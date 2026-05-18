"""
Gemini client — uses Gemini 3 via Vertex AI (google-genai SDK).

Vertex AI mode is required for hackathon compliance
("Google Cloud artificial intelligence tools").

Model: gemini-3-flash-preview  (Gemini 3 generation)
Fallback: gemini-2.5-flash     (if Gemini 3 not yet available in region)
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

# Fallback: legacy google-generativeai SDK
try:
    import google.generativeai as _genai_legacy
    _LEGACY_AVAILABLE = True
except ImportError:
    _LEGACY_AVAILABLE = False

_client: Optional[object] = None
_legacy_model: Optional[object] = None

# Gemini 3 model IDs in priority order
_MODEL_CANDIDATES = [
    "gemini-3-flash-preview",   # Gemini 3 — hackathon requirement
    "gemini-2.5-flash",         # fallback
    "gemini-2.0-flash",         # last resort
]


def _get_model_id() -> str:
    """Return configured model or default to Gemini 3 flash."""
    env = os.getenv("GEMINI_MODEL", "")
    return env if env else _MODEL_CANDIDATES[0]


def _get_client():
    """Return a configured google-genai client (Vertex AI mode preferred)."""
    global _client
    if _client is not None:
        return _client

    if not _GENAI_AVAILABLE:
        return None

    project = os.getenv("GOOGLE_PROJECT_ID", "")
    location = os.getenv("GOOGLE_LOCATION", "us-central1")
    api_key = os.getenv("GEMINI_API_KEY", "")

    if project:
        # Vertex AI mode — required for Google Cloud tools compliance
        _client = genai.Client(vertexai=True, project=project, location=location)
    elif api_key:
        # Direct API fallback (dev only)
        _client = genai.Client(api_key=api_key)
    return _client


def _get_legacy_model():
    global _legacy_model
    if _legacy_model is None and _LEGACY_AVAILABLE:
        api_key = os.getenv("GEMINI_API_KEY", "")
        _genai_legacy.configure(api_key=api_key)
        model_id = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        _legacy_model = _genai_legacy.GenerativeModel(model_id)
    return _legacy_model


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
    """Core generation call — tries Gemini 3 via Vertex AI first."""
    model_id = _get_model_id()
    text = None

    # Try: new SDK (Vertex AI mode)
    if _GENAI_AVAILABLE:
        client = _get_client()
        if client:
            for candidate_model in _MODEL_CANDIDATES:
                if os.getenv("GEMINI_MODEL"):
                    candidate_model = os.getenv("GEMINI_MODEL")
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
                    break
                except Exception as e:
                    err = str(e)
                    if "not found" in err.lower() or "404" in err or "deprecated" in err.lower():
                        # Try next model
                        continue
                    raise

    # Fallback: legacy SDK
    if text is None and _LEGACY_AVAILABLE:
        model = _get_legacy_model()
        if model:
            response = model.generate_content(prompt)
            text = response.text.strip()

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

COMPUTED STATISTICS:
- Pearson r = {pearson_r:.3f} (computed from {corr_metric} time series)
- p-value = {p_value:.4f}
- {days_of_warning} days of warning were available and missed

Write EXACTLY 3 sentences:
1. What the decision was and what data was being ignored (cite specific numbers)
2. What Pearson r = {pearson_r:.3f} means for this outcome specifically
3. How many days of warning existed and what the first signal was

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
