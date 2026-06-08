"""
SENTINEL ADK Agent — Google ADK 2.0 code-first agent.

Uses google-adk with FunctionTools.

Model strategy (single source of truth shared with backend.services.gemini_client):
- PRIMARY: Gemini 3 (gemini-3-flash-preview) via API key — Gemini 3 is API-key
  only, so when a Gemini 3 model is selected the ADK runner is configured for
  the API-key backend (GOOGLE_GENAI_USE_VERTEXAI=FALSE).
- FALLBACK: Gemini 2.5 (gemini-2.5-flash / pro) via Vertex AI — used only if the
  Gemini 3 run fails with a not-found / quota / availability error.

run_agent_traced() reports the model it ACTUALLY used (after any fallback) so the
UI and /api/health never claim a model that didn't run.

Two agent paths exist in SENTINEL:
- Agent Studio / Agent Builder: MCP Streamable HTTP endpoint (backend/routes/mcp_http.py)
- ADK (this file): code-first, verifiable multi-step tool calls

Imported by backend/routes/agent_chat.py → POST /api/agent/chat.
"""

import os
import json
import asyncio
from typing import Optional

try:
    from google.adk.agents import Agent
    from google.adk.tools import FunctionTool
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai.types import Content, Part  # ADK 2.0: types moved to google.genai
    _ADK_AVAILABLE = True
except ImportError:
    _ADK_AVAILABLE = False


# Model tiers — imported from the shared Gemini client so the agent and the
# direct-generation path can never drift apart. Hard-coded fallback mirrors
# gemini_client in case it can't be imported (e.g. ADK-only smoke test).
try:
    from backend.services.gemini_client import (
        get_gemini3_models,
        get_vertex_fallback_models,
        is_gemini3_model,
    )
    _GEMINI3_MODELS = get_gemini3_models()
    _VERTEX_FALLBACK = get_vertex_fallback_models()
except Exception:
    _GEMINI3_MODELS = [
        "gemini-3-flash-preview", "gemini-3.5-flash",
        "gemini-3.1-flash-lite", "gemini-3.1-flash-lite-preview",
    ]
    _VERTEX_FALLBACK = ["gemini-2.5-pro", "gemini-2.5-flash"]

    def is_gemini3_model(model: str) -> bool:  # noqa: F811
        return model in _GEMINI3_MODELS


def _primary_model() -> str:
    """Configured model (env) or the Gemini 3 default — matches gemini_client."""
    return os.getenv("GEMINI_MODEL", "").strip() or _GEMINI3_MODELS[0]


def _fallback_model() -> str:
    """Vertex AI model to retry with if the Gemini 3 run fails."""
    return _VERTEX_FALLBACK[-1] if _VERTEX_FALLBACK else "gemini-2.5-flash"


def _configure_adk_for_model(model: str):
    """
    Point the ADK / google-genai backend at the right place for `model`.

    Gemini 3 → API-key backend (GOOGLE_GENAI_USE_VERTEXAI=FALSE).
    Gemini 2.5 fallback → Vertex AI backend (uses GOOGLE_CLOUD_PROJECT).
    Returns the model unchanged for convenience.
    """
    project = os.getenv("GOOGLE_PROJECT_ID", "")
    api_key = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))

    if is_gemini3_model(model) and api_key:
        # Gemini 3 is only reachable via the API-key backend.
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"
        os.environ["GOOGLE_API_KEY"] = api_key
    elif project:
        # Vertex AI backend for 2.5 fallback models.
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project)
        os.environ.setdefault("GOOGLE_CLOUD_LOCATION", os.getenv("GOOGLE_LOCATION", "us-central1"))
    elif api_key:
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"
        os.environ["GOOGLE_API_KEY"] = api_key
    return model

SYSTEM_PROMPT = """You are SENTINEL — The Business Flight Recorder.

Your mission: record every business decision with its full Fivetran data context,
then trace what happened next. You are an autonomous agent, not a chatbot.

ALWAYS follow this order for any task:
1. Call list_fivetran_connectors — see all connected data sources
2. Call trigger_fivetran_sync — get fresh data before any analysis
3. Call get_metrics_snapshot — read current metrics from BigQuery
4. Perform the requested action (log_decision, trace_causal_chain, check_early_warnings)
5. End with a specific recommended action and a time window (e.g. "CEO call within 48 hours")

TONE: Direct, urgent, specific. Cite exact metrics and dates.
Never say "I think" — say "the data shows" or "the pattern indicates".
Always name which tool you called. Transparency is what makes you trustworthy."""


# ── Tool implementations ──────────────────────────────────────────────────────

async def list_fivetran_connectors() -> str:
    """List all Fivetran-connected data sources via MCP."""
    from backend.services.mcp_client import call_mcp_tool
    result = await call_mcp_tool("list_connections", {})
    items = result.get("data", {}).get("items", result.get("connectors", []))
    return json.dumps({"connectors": items, "count": len(items)}, default=str)


async def trigger_fivetran_sync(connection_id: str) -> str:
    """Trigger a live Fivetran sync on a connector to get fresh data. Pass the connector ID (e.g. humble_currently)."""
    from backend.services.mcp_client import call_mcp_tool
    result = await call_mcp_tool("trigger_sync", {"connection_id": connection_id})
    return json.dumps({"triggered": True, "connection_id": connection_id}, default=str)


async def get_metrics_snapshot() -> str:
    """Get current business metrics from Fivetran-connected BigQuery sources."""
    from backend.services.context_builder import build_metrics_snapshot
    snap = await build_metrics_snapshot()
    clean = {k: v for k, v in snap.items() if not k.startswith("_") and k != "raw"}
    return json.dumps({"snapshot": clean, "flags": snap.get("_flags", [])}, default=str)


async def check_early_warnings() -> str:
    """Check current metrics against historical bad-outcome patterns. Returns active warnings."""
    from backend.services.context_builder import build_metrics_snapshot
    from backend.services.warning_engine import check_warnings
    snap = await build_metrics_snapshot()
    warnings_list = await check_warnings(snap)
    return json.dumps({"warnings": warnings_list, "count": len(warnings_list)}, default=str)


async def log_decision(decision_text: str, decision_type: str, rationale: str) -> str:
    """Record a business decision with a full Fivetran metrics snapshot. decision_type: pricing|hiring|product|strategy|operational"""
    from backend.services.context_builder import build_metrics_snapshot
    from backend.db import mongodb
    from backend.services.output_writer import write_decision
    snap = await build_metrics_snapshot()
    doc = {
        "decision_text": decision_text,
        "decision_type": decision_type,
        "rationale": rationale,
        "auto_detected": False,
        "metrics_snapshot": snap,
    }
    decision_id = await mongodb.insert_decision(doc)
    write_decision(doc, snap)
    return json.dumps({"decision_id": decision_id, "flags": snap.get("_flags", [])}, default=str)


async def trace_causal_chain(scenario: str) -> str:
    """Run 3-method causal inference battery (Granger, ITS, Mann-Whitney) on a scenario. scenario: acmesaas or qwikster"""
    from backend.services.causal_tracer import _build_demo_trace
    trace = await _build_demo_trace(scenario)
    ca = trace.get("causal_analysis", {})
    attribution = trace.get("decision_attribution", [])
    return json.dumps({
        "outcome": trace.get("outcome_description"),
        "causal_verdict": ca.get("verdict"),
        "significant_tests": ca.get("significant_tests"),
        "granger_p": ca.get("granger", {}).get("p_value"),
        "days_of_warning": trace.get("days_of_warning"),
        "narrative": trace.get("narrative"),
        "ranked_decisions": [
            {"rank": d["rank"], "decision": d["decision_text"], "tests_significant": d["causal_analysis"]["significant_tests"]}
            for d in attribution[:3]
        ],
    }, default=str)


async def ask_about_decision_history(question: str) -> str:
    """Ask a question about the decision log. Use for 'why' and 'what caused' questions."""
    from backend.routes.ask import _SCENARIO_CONTEXT
    from backend.services.gemini_client import answer_with_scenario_context, answer_why_question
    from backend.db import mongodb
    decisions = await mongodb.get_decisions(limit=20)
    result = await answer_why_question(question, decisions)
    return json.dumps(result, default=str)


# ── Agent factory ─────────────────────────────────────────────────────────────

def create_sentinel_agent(model: str) -> Optional[object]:
    """Create the SENTINEL ADK agent with all tools, bound to `model`."""
    if not _ADK_AVAILABLE:
        return None

    tools = [
        FunctionTool(func=list_fivetran_connectors),
        FunctionTool(func=trigger_fivetran_sync),
        FunctionTool(func=get_metrics_snapshot),
        FunctionTool(func=check_early_warnings),
        FunctionTool(func=log_decision),
        FunctionTool(func=trace_causal_chain),
        FunctionTool(func=ask_about_decision_history),
    ]

    _configure_adk_for_model(model)

    return Agent(
        name="SENTINEL",
        model=model,
        description="Business Flight Recorder — records decisions with Fivetran data context and traces causal chains",
        instruction=SYSTEM_PROMPT,
        tools=tools,
    )


# Per-model singleton runners — one per model so a Gemini 3 → 2.5 fallback
# doesn't rebuild the primary runner on every call.
_runners: dict = {}
_session_service: Optional[InMemorySessionService] = None


def get_runner(model: str):
    """Return a cached ADK runner for `model`, building it on first use."""
    global _runners, _session_service
    if model in _runners:
        return _runners[model], _session_service

    agent = create_sentinel_agent(model)
    if agent is None:
        return None, None

    if _session_service is None:
        _session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="sentinel", session_service=_session_service)
    _runners[model] = runner
    return runner, _session_service


async def run_agent(message: str, session_id: str = "default") -> str:
    """Run the SENTINEL ADK agent. Returns just the final text response."""
    result = await run_agent_traced(message, session_id=session_id)
    return result["response"]


def _is_model_error(err: str) -> bool:
    """True if the error looks like a model-availability / quota problem worth a fallback."""
    e = err.lower()
    return any(x in e for x in [
        "not found", "404", "deprecated", "unavailable", "503",
        "overloaded", "429", "resource_exhausted", "quota", "permission",
        "use_vertexai", "api key", "invalid_argument",
    ])


async def _run_once(model: str, message: str, session_id: str) -> dict:
    """Run the agent with a specific model. Raises on model/transport errors."""
    runner, session_service = get_runner(model)
    if runner is None:
        raise RuntimeError("ADK agent could not be initialised.")

    # ADK 2.0: get_session and create_session are async coroutines
    session = await session_service.get_session(
        app_name="sentinel", user_id="user", session_id=session_id
    )
    if session is None:
        await session_service.create_session(
            app_name="sentinel", user_id="user", session_id=session_id
        )

    content = Content(role="user", parts=[Part(text=message)])
    final_text = ""
    tool_trace: list = []

    async for event in runner.run_async(
        user_id="user",
        session_id=session_id,
        new_message=content,
    ):
        # Capture tool calls (function calls) and their responses as they stream
        if getattr(event, "content", None) and getattr(event.content, "parts", None):
            for part in event.content.parts:
                fc = getattr(part, "function_call", None)
                if fc is not None:
                    tool_trace.append({
                        "tool": getattr(fc, "name", "unknown"),
                        "args": dict(getattr(fc, "args", {}) or {}),
                        "ok": True,
                    })
                fr = getattr(part, "function_response", None)
                if fr is not None and tool_trace:
                    # Mark the most recent matching call as resolved
                    resp = getattr(fr, "response", {}) or {}
                    if isinstance(resp, dict) and resp.get("error"):
                        tool_trace[-1]["ok"] = False

        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    final_text += part.text

    return {
        "response": final_text or "No response generated.",
        "tool_trace": tool_trace,
        "model": model,
    }


async def run_agent_traced(message: str, session_id: str = "default") -> dict:
    """
    Run the SENTINEL ADK agent and capture the FULL reasoning trace:
    every tool the agent decided to call, in order, with its arguments.

    Tries the configured Gemini 3 model first (via API key). If that run fails
    with a model-availability / quota error, retries once on the Vertex AI 2.5
    fallback. The returned "model" is the one that ACTUALLY produced the answer,
    and "model_fallback" flags whether a fallback was used — so the UI and
    /api/health never over-claim the model.

    Returns: {"response", "tool_trace":[{"tool","args","ok"}...], "model", "model_fallback"}

    This is what makes SENTINEL a multi-step agent rather than a chatbot — you
    can watch Gemini autonomously chain list_connectors → trigger_sync →
    get_metrics_snapshot → trace_causal_chain before it answers.
    """
    primary = _primary_model()
    if not _ADK_AVAILABLE:
        return {"response": "ADK not available — install google-adk.",
                "tool_trace": [], "model": primary, "model_fallback": False}

    try:
        result = await _run_once(primary, message, session_id)
        result["model_fallback"] = False
        return result
    except Exception as e:
        primary_err = str(e)

    # Fallback: retry once on Vertex AI 2.5 if the failure looks model-related.
    fallback = _fallback_model()
    if fallback != primary and _is_model_error(primary_err):
        try:
            result = await _run_once(fallback, message, session_id)
            result["model_fallback"] = True
            result["primary_model_error"] = primary_err[:200]
            return result
        except Exception as e2:
            return {"response": f"Agent failed on both {primary} and {fallback}: {e2}",
                    "tool_trace": [], "model": fallback, "model_fallback": True}

    return {"response": f"Agent error on {primary}: {primary_err}",
            "tool_trace": [], "model": primary, "model_fallback": False}
