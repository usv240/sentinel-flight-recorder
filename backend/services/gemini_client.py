import os
import json
from typing import Optional

try:
    from google import genai
    from google.genai import types as genai_types
    _USE_NEW_SDK = True
except ImportError:
    import google.generativeai as genai_legacy
    _USE_NEW_SDK = False

_client = None
_model_legacy = None


def _get_client():
    global _client
    if _USE_NEW_SDK and _client is None:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
    return _client


def _get_legacy_model():
    global _model_legacy
    if _model_legacy is None:
        import google.generativeai as genai_leg
        genai_leg.configure(api_key=os.getenv("GEMINI_API_KEY", ""))
        _model_legacy = genai_leg.GenerativeModel("gemini-2.0-flash-exp")
    return _model_legacy


async def generate(prompt: str, as_json: bool = False) -> str:
    if _USE_NEW_SDK:
        client = _get_client()
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        response = client.models.generate_content(model=model, contents=prompt)
        text = response.text.strip()
    else:
        model = _get_legacy_model()
        response = model.generate_content(prompt)
        text = response.text.strip()

    if as_json:
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return text.strip()
    return text


async def analyze_causal_chain(
    outcome_description: str,
    outcome_date: str,
    affected_metric: str,
    candidate_decisions: list,
    metrics_at_decision: dict,
    metrics_at_outcome: dict,
) -> dict:
    decisions_text = "\n".join(
        f"- [{d.get('logged_at', 'unknown date')}] {d.get('decision_type', '').upper()}: "
        f"{d.get('decision_text', '')} | Rationale: {d.get('rationale', 'not recorded')}"
        for d in candidate_decisions
    )

    prompt = f"""You are SENTINEL — The Business Flight Recorder.

Analyze this business outcome and identify its root cause from the decision log.

BAD OUTCOME: {outcome_description}
First observed: {outcome_date}
Affected metric: {affected_metric}

METRICS AT OUTCOME TIME:
{json.dumps(metrics_at_outcome, indent=2)}

DECISIONS MADE IN THE 14-90 DAYS BEFORE THIS OUTCOME:
{decisions_text}

METRICS AT THE TIME OF EACH DECISION:
{json.dumps(metrics_at_decision, indent=2)}

Your task:
1. Identify the root cause decision(s)
2. Explain the causal mechanism
3. List data signals AVAILABLE at decision time that should have raised flags
4. State how many days of warning were available
5. Suggest 2-3 preventive actions

Respond as valid JSON:
{{
  "root_decision_id": "DEC-xxx or null",
  "causal_mechanism": "explanation",
  "data_that_predicted_outcome": ["signal 1", "signal 2", "signal 3"],
  "days_of_warning": 34,
  "earliest_signal_description": "first detectable signal",
  "preventive_actions": ["action 1", "action 2", "action 3"],
  "narrative": "2-3 sentence summary",
  "confidence": 0.87
}}"""

    result = await generate(prompt, as_json=True)
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {
            "root_decision_id": None,
            "causal_mechanism": result,
            "data_that_predicted_outcome": [],
            "days_of_warning": 0,
            "earliest_signal_description": "",
            "preventive_actions": [],
            "narrative": result[:300],
            "confidence": 0.5,
        }


async def extract_decisions_from_transcript(transcript: str) -> list:
    prompt = f"""Extract all business decisions mentioned in this meeting transcript.

TRANSCRIPT:
{transcript}

Return a JSON array:
[
  {{
    "decision_text": "what was decided",
    "decision_type": "pricing|hiring|product|strategy|operational",
    "rationale": "why (if mentioned)",
    "participants": ["names"],
    "confidence": 0.9
  }}
]

Only include actual decisions, not discussions."""

    result = await generate(prompt, as_json=True)
    try:
        return json.loads(result)
    except Exception:
        return []


async def answer_why_question(question: str, decision_log: list) -> dict:
    decisions_text = "\n".join(
        f"[{d.get('logged_at', '?')}] {d.get('decision_type', '').upper()}: "
        f"{d.get('decision_text', '')} | MRR={d.get('metrics_snapshot', {}).get('mrr', '?')}, "
        f"NPS={d.get('metrics_snapshot', {}).get('nps', '?')} | "
        f"Outcome: {d.get('outcome', 'pending')}"
        for d in decision_log[:20]
    )

    prompt = f"""You are SENTINEL. Answer this question using the decision log.

QUESTION: {question}

DECISION LOG:
{decisions_text}

Respond as JSON:
{{
  "answer": "direct answer",
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

Sentence 1: what is happening right now.
Sentence 2: what decision caused this pattern.
Be specific, factual, urgent. A CEO must understand immediately."""

    return await generate(prompt)
