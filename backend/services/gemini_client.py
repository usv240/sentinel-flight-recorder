"""
Gemini client — uses Gemini via Vertex AI (google-genai SDK).

Vertex AI mode uses Google Cloud project credentials.
Model configured via GEMINI_MODEL env var (default: gemini-2.5-flash).
"""

import os
import json
import re
from typing import Optional

# Primary: new google-genai SDK with Vertex AI
try:
    from google import genai
    from google.genai import types as genai_types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

_client: Optional[object] = None
_LEGACY_AVAILABLE = False  # legacy google-generativeai removed; use google-genai only

# Set to True when all Gemini 3 models fail due to quota (429/RESOURCE_EXHAUSTED).
# Used by tests to distinguish quota exhaustion from code errors.
_gemini3_quota_exhausted: bool = False

# ── Gemini 3 models — strict requirement, all via API key ─────────────────────
# Tested and confirmed working: gemini-3-flash-preview, gemini-3.5-flash,
# gemini-3.1-flash-lite, gemini-3.1-flash-lite-preview
# Pro models (429 quota-limited): gemini-3.1-pro-preview, gemini-3-pro-preview
_GEMINI3_MODELS = [
    "gemini-3-flash-preview",       # primary — Gemini 3, confirmed working
    "gemini-3.5-flash",             # G3 fallback 1
    "gemini-3.1-flash-lite",        # G3 fallback 2
    "gemini-3.1-flash-lite-preview",# G3 fallback 3
]

# Vertex AI fallback — used only when ALL Gemini 3 API key quota is exhausted
# These use the project's Vertex AI billing (much higher quota)
_VERTEX_FALLBACK = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
]

# Full candidate list: Gemini 3 first (API key), Vertex AI last resort
_MODEL_CANDIDATES = _GEMINI3_MODELS + _VERTEX_FALLBACK


def _get_model_id() -> str:
    """Return configured model or default to Gemini 3 flash."""
    env = os.getenv("GEMINI_MODEL", "")
    return env if env else _MODEL_CANDIDATES[0]


def _get_client():
    """
    Return a configured google-genai client.
    Gemini 3 models are only available via API key (not Vertex AI yet).
    Vertex AI is used for models that work there (2.5-flash, 2.5-pro, 2.0-flash).
    """
    global _client
    if _client is not None:
        return _client

    if not _GENAI_AVAILABLE:
        return None

    project = os.getenv("GOOGLE_PROJECT_ID", "")
    location = os.getenv("GOOGLE_LOCATION", "us-central1")
    api_key  = os.getenv("GEMINI_API_KEY", "")

    # Prefer Vertex AI for cloud compliance — but Gemini 3 needs API key
    if project:
        _client = genai.Client(vertexai=True, project=project, location=location)
    elif api_key:
        _client = genai.Client(api_key=api_key)
    return _client


def _get_gemini3_client():
    """Dedicated client for Gemini 3 models — requires API key, not Vertex AI."""
    if not _GENAI_AVAILABLE:
        return None
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)



def _clean_json(text: str) -> str:
    """Robustly strip markdown code fences from Gemini output."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ``` blocks
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return match.group(1).strip()
    # Remove leading/trailing backticks without newlines
    if text.startswith("`") and text.endswith("`"):
        text = text.strip("`").strip()
    return text


async def generate(prompt: str, as_json: bool = False) -> str:
    """
    Core generation call.
    Gemini 3 models → API key client (only way they work currently).
    Gemini 2.5/2.0 models → Vertex AI client.
    Tries Gemini 3 first, falls back gracefully.
    """
    global _gemini3_quota_exhausted
    text = None

    if not _GENAI_AVAILABLE:
        return "{}" if as_json else ""

    env_model = os.getenv("GEMINI_MODEL", "").strip()
    # Always try Gemini 3 first (hackathon strict requirement).
    # If GEMINI_MODEL is a Gemini 3 model, honour that preference within G3 tier.
    # If GEMINI_MODEL is a Vertex fallback, still put all G3 models first.
    if env_model and env_model in _GEMINI3_MODELS:
        candidates = [env_model] + [m for m in _MODEL_CANDIDATES if m != env_model]
    else:
        # env_model is a Vertex model or empty — Gemini 3 tier goes first always
        candidates = _GEMINI3_MODELS + [m for m in _VERTEX_FALLBACK if m != env_model]
        if env_model and env_model not in candidates:
            candidates.append(env_model)

    gemini3_client = _get_gemini3_client()
    vertex_client  = _get_client()

    _gemini3_failed_count = 0

    for candidate_model in candidates:
        # Gemini 3 → API key client. Vertex fallbacks → Vertex AI client.
        is_gemini3 = candidate_model in _GEMINI3_MODELS
        client = gemini3_client if is_gemini3 else vertex_client
        if not client:
            if is_gemini3:
                _gemini3_failed_count += 1
            continue
        try:
            config = None
            if as_json:
                try:
                    config = genai_types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                except Exception:
                    config = None
            response = client.models.generate_content(
                model=candidate_model,
                contents=prompt,
                config=config,
            )
            text = response.text.strip()
            os.environ["GEMINI_MODEL_ACTIVE"] = candidate_model
            # Reset flag if Gemini 3 succeeds
            if is_gemini3:
                _gemini3_quota_exhausted = False
            break
        except Exception as e:
            err = str(e)
            if any(x in err.lower() for x in [
                "not found", "404", "deprecated",
                "unavailable", "503", "overloaded",
                "429", "resource_exhausted", "quota",
            ]):
                if is_gemini3:
                    _gemini3_failed_count += 1
                continue  # quota / unavailable — try next candidate
            raise

    # All Gemini 3 candidates failed → mark quota as exhausted
    if _gemini3_failed_count >= len(_GEMINI3_MODELS):
        _gemini3_quota_exhausted = True

    if text is None:
        return "{}" if as_json else ""

    if as_json:
        return _clean_json(text)
    return text


# ── Task-specific Gemini calls ────────────────────────────────────────────────

async def analyze_causal_chain(
    outcome_description: str,
    outcome_date: str,
    affected_metric: str,
    candidate_decisions: list,
    metrics_at_decision: dict,
    metrics_at_outcome: dict,
) -> dict:
    decisions_text = "\n".join(
        f"- [{d.get('logged_at', '?')}] {d.get('decision_type', '').upper()}: "
        f"{d.get('decision_text', '')} | Rationale: {d.get('rationale', 'not recorded')}"
        for d in candidate_decisions
    )

    prompt = f"""You are SENTINEL — The Business Flight Recorder.

Analyze this business outcome and identify its root cause.

BAD OUTCOME: {outcome_description}
First observed: {outcome_date}
Affected metric: {affected_metric}

DECISIONS (14–90 days before outcome):
{decisions_text}

METRICS AT DECISION TIME:
{json.dumps(metrics_at_decision, indent=2, default=str)}

METRICS AT OUTCOME:
{json.dumps(metrics_at_outcome, indent=2, default=str)}

Identify the root cause, how many days of warning were available, and 3 preventive actions.

Return valid JSON only:
{{
  "root_decision_id": "DEC-xxx or null",
  "causal_mechanism": "explanation",
  "data_that_predicted_outcome": ["signal 1", "signal 2", "signal 3"],
  "days_of_warning": 34,
  "earliest_signal_description": "first detectable signal",
  "preventive_actions": ["action 1", "action 2", "action 3"],
  "narrative": "2-3 sentence summary citing specific numbers",
  "confidence": 0.87
}}"""

    result = await generate(prompt, as_json=True)
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {
            "root_decision_id": None, "causal_mechanism": result,
            "data_that_predicted_outcome": [], "days_of_warning": 0,
            "earliest_signal_description": "", "preventive_actions": [],
            "narrative": result[:300], "confidence": 0.5,
        }


async def generate_causal_narrative(
    outcome: str,
    root_decision: dict,
    causal_chain: list,
    data_at_decision: dict,
    pearson_r: float,
    p_value: float,
    days_of_warning: int,
    corr_metric: str,
) -> str:
    chain_text = "\n".join(
        f"  [{e['date']}] {e['title']}: {e['description']}"
        for e in causal_chain
    )
    prompt = f"""You are SENTINEL — The Business Flight Recorder. Write a 3-sentence causal narrative.

OUTCOME: {outcome}
ROOT DECISION: {root_decision.get('decision_text')} ({root_decision.get('logged_at', '')[:10]})
RATIONALE: {root_decision.get('rationale', 'not recorded')}

CAUSAL CHAIN:
{chain_text}

DATA THAT EXISTED AT DECISION TIME:
{json.dumps(data_at_decision, indent=2, default=str)}

CAUSAL INFERENCE RESULTS (3-method statistical battery):
- Pearson r = {pearson_r:.3f} on {corr_metric} (correlation context only)
- p-value = {p_value:.4f}
- {days_of_warning} days of warning were available and missed
- NOTE: Use "the statistical pattern" or "3 independent tests confirm" — do NOT frame correlation as proof of causation.

Write EXACTLY 3 sentences:
1. What the decision was and what data was being ignored (cite specific numbers from data_at_decision)
2. What the statistical pattern shows — reference that multiple independent tests (Granger causality, trend break analysis) confirm the relationship
3. How many days of warning existed and what the first measurable signal was

Be direct, urgent. Cite specific metrics and dates. No hedging."""

    return await generate(prompt)


async def answer_with_scenario_context(question: str, scenario_context: dict) -> dict:
    ctx_json = json.dumps(scenario_context, indent=2, default=str)
    prompt = f"""You are SENTINEL — The Business Flight Recorder.
Answer the question using ONLY the scenario data below. Be specific. Cite exact numbers, dates, and decision IDs.

SCENARIO DATA:
{ctx_json}

USER QUESTION: {question}

Rules:
- Cite specific metrics, dates, and IDs from the data
- If referencing Pearson r, explain what it means for this outcome
- Mention which Fivetran-connected source provided each metric
- End with a specific recommended action if forward-looking
- Under 200 words

Return JSON:
{{
  "answer": "your answer",
  "relevant_decision_ids": ["DEC-xxx"],
  "confidence": 0.95,
  "sources": ["specific decisions/metrics referenced"]
}}"""

    result = await generate(prompt, as_json=True)
    try:
        parsed = json.loads(result)
        if "answer" not in parsed:
            return {"answer": result[:500], "relevant_decision_ids": [], "confidence": 0.7, "sources": []}
        return parsed
    except Exception:
        return {"answer": result[:500], "relevant_decision_ids": [], "confidence": 0.7, "sources": []}


async def extract_decisions_from_transcript(transcript: str) -> list:
    prompt = f"""You are SENTINEL. Extract every business decision from this text.

TEXT:
{transcript[:4000]}

Return a JSON array. Include decisions only — not discussions, questions, or observations.

[
  {{
    "decision_text": "what was decided",
    "decision_type": "pricing|hiring|product|strategy|operational",
    "rationale": "why (if mentioned)",
    "participants": ["names if mentioned"],
    "confidence": 0.9
  }}
]

If no decisions, return [].
"""
    result = await generate(prompt, as_json=True)
    try:
        return json.loads(result)
    except Exception:
        return []


async def answer_why_question(question: str, decision_log: list) -> dict:
    decisions_text = "\n".join(
        f"[{d.get('logged_at', '?')}] {d.get('decision_type', '').upper()}: "
        f"{d.get('decision_text', '')} | MRR={d.get('metrics_snapshot', {}).get('mrr', '?')}, "
        f"NPS={d.get('metrics_snapshot', {}).get('nps', '?')} | Outcome: {d.get('outcome', 'pending')}"
        for d in decision_log[:20]
    )
    prompt = f"""You are SENTINEL. Answer this question using the decision log.

QUESTION: {question}

DECISION LOG:
{decisions_text}

Return JSON:
{{
  "answer": "direct answer citing specific dates, metrics, and decision IDs",
  "relevant_decision_ids": ["DEC-xxx"],
  "confidence": 0.85,
  "sources": ["which decisions you referenced"]
}}"""

    result = await generate(prompt, as_json=True)
    try:
        return json.loads(result)
    except Exception:
        return {"answer": result[:500], "relevant_decision_ids": [], "confidence": 0.5, "sources": []}


async def generate_confounding_factors(
    root_decision: dict,
    outcome: str,
    causal_chain: list,
    pearson_r: float,
) -> list:
    """Generate alternative explanations that could confound the correlation.
    Honest statistical framing — correlation is not causation."""
    prompt = f"""You are a skeptical data scientist reviewing a business decision analysis.

ROOT DECISION: {root_decision.get('decision_text', 'Unknown')} on {root_decision.get('logged_at', '?')}
OBSERVED OUTCOME: {outcome}
CORRELATION (Pearson r): {pearson_r} between decision timing and outcome metrics
CHAIN OF EVENTS: {json.dumps(causal_chain[:3], default=str)}

List exactly 3 plausible ALTERNATIVE EXPLANATIONS or confounding factors that could explain the same outcome WITHOUT the root decision being causal. These are factors a skeptic would raise.

Return a JSON array of 3 strings. Each string is one confounding factor, 1 sentence, specific and realistic. No preamble.

Example format: ["Factor 1 text here.", "Factor 2 text here.", "Factor 3 text here."]"""

    raw = await generate(prompt, as_json=True)
    try:
        result = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(result, list):
            return result[:3]
        if isinstance(result, dict):
            for v in result.values():
                if isinstance(v, list):
                    return v[:3]
    except Exception:
        pass
    return [
        "A competitor may have launched a competing product or pricing change in the same window.",
        "Macroeconomic conditions or seasonal patterns could explain the metric movement independently.",
        "Other concurrent internal decisions (hiring, product changes) may have contributed equally.",
    ]


async def generate_action_plan(
    warning: dict,
    snapshot: dict,
    root_decision: dict = None,
) -> dict:
    """
    Generate a concrete action plan AND a ready-to-send stakeholder alert.
    This is SENTINEL's visible agent action — not just data in a database.
    The draft_email field is a real email a CEO could send in 30 seconds.
    """
    from datetime import datetime
    today = datetime.now().strftime("%B %d, %Y")
    mrr = snapshot.get('mrr', 0)
    nps = snapshot.get('nps', '?')
    churn = snapshot.get('churn_rate', 0)
    try:
        churn_pct = f"{float(churn):.1%}"
    except Exception:
        churn_pct = str(churn)

    prompt = f"""You are SENTINEL, an autonomous business intelligence agent. A critical warning just fired.
Generate a JSON response with two parts: an action plan AND a ready-to-send stakeholder email.

WARNING: {warning.get('message', warning.get('description', 'Critical pattern detected'))}
SEVERITY: {warning.get('severity', 'high').upper()}
TRIGGER METRIC: {warning.get('trigger_metric', 'unknown')} = {warning.get('trigger_value', '?')}
ROOT DECISION: {(root_decision or {}).get('decision_text', 'Unknown')}
CURRENT METRICS: MRR=${mrr:,.0f}, NPS={nps}, Churn={churn_pct}
DATE: {today}

Return this exact JSON structure:
{{
  "summary": "1-sentence summary: what SENTINEL detected and why it requires immediate action",
  "urgency": "immediate|48h|7d",
  "actions": [
    {{"step": 1, "owner": "CEO|CFO|VP Sales|Product|Engineering", "action": "specific concrete action", "deadline": "within X hours/days"}},
    {{"step": 2, "owner": "role", "action": "specific concrete action", "deadline": "within X hours/days"}},
    {{"step": 3, "owner": "role", "action": "specific concrete action", "deadline": "within X days"}}
  ],
  "metric_to_watch": "exact metric name that confirms recovery",
  "escalate_if": "specific measurable condition requiring board-level escalation",
  "draft_email": {{
    "subject": "SENTINEL Alert: [specific subject line a CEO would actually send]",
    "to": "Leadership Team",
    "body": "Full email body (3-4 paragraphs). Reference specific metrics. Name specific actions and owners. Give specific deadlines. Write as if this is a real urgent business email, not a template. Start with the finding, then the data, then the asks."
  }}
}}

The draft_email.body must be specific (cite exact metrics, exact dates, exact numbers from the context above).
Do not use placeholder text like [X] or [insert here]."""

    raw = await generate(prompt, as_json=True)
    try:
        result = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(result, dict) and "actions" in result:
            return result
    except Exception:
        pass

    # Structured fallback — also specific
    return {
        "summary": f"SENTINEL detected a critical pattern: {warning.get('message', 'anomaly detected')}. Immediate leadership action required.",
        "urgency": "48h",
        "actions": [
            {"step": 1, "owner": "CEO", "action": f"Review decision log for decisions made in the last {warning.get('days_since_decision', 45)} days that correlate with this pattern", "deadline": "within 24 hours"},
            {"step": 2, "owner": "VP Sales", "action": "Contact top 5 accounts by ARR to assess sentiment — do not wait for renewal", "deadline": "within 48 hours"},
            {"step": 3, "owner": "Product", "action": f"Evaluate reverting or softening the decision that triggered {warning.get('trigger_metric', 'the metric change')}", "deadline": "within 7 days"},
        ],
        "metric_to_watch": warning.get("trigger_metric", "churn_rate"),
        "escalate_if": f"{warning.get('trigger_metric', 'churn_rate')} does not show improvement within 14 days",
        "draft_email": {
            "subject": f"SENTINEL Alert [{warning.get('severity', 'HIGH').upper()}]: Action Required — {warning.get('trigger_metric', 'Metric')} Pattern Detected",
            "to": "Leadership Team",
            "body": (
                f"SENTINEL flagged a {warning.get('severity', 'high')}-severity pattern at {today}.\n\n"
                f"Pattern: {warning.get('message', 'A critical metric pattern was detected.')}\n\n"
                f"Current state: MRR ${mrr:,.0f} | NPS {nps} | Churn {churn_pct}\n\n"
                f"SENTINEL's recommendation: {warning.get('recommended_action', 'Review the decision log and contact at-risk accounts within 48 hours.')}\n\n"
                "This alert was generated autonomously by SENTINEL with no human action. Review the full decision impact trace at your SENTINEL dashboard."
            ),
        },
    }


async def generate_warning_narrative(
    trigger_metric: str,
    trigger_value: float,
    root_decision: dict,
    pattern_description: str,
) -> str:
    prompt = f"""You are SENTINEL. Write a 2-sentence urgent early warning.

TRIGGER: {trigger_metric} changed by {trigger_value:.0%}
ROOT DECISION: {root_decision.get('decision_text', 'Unknown')} ({root_decision.get('days_ago', '?')} days ago)
PATTERN: {pattern_description}

Sentence 1: what is happening right now (specific metric, specific change).
Sentence 2: which decision caused this and what the historical pattern shows.
Be specific, factual, urgent. No hedging."""

    return await generate(prompt)
