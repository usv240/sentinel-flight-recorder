"""
SENTINEL ADK Agent — Google ADK 2.0 code-first agent.

Uses google-adk with FunctionTools.
Model: gemini-2.5-flash (Gemini 3 Flash when available) via Vertex AI.

Two agent paths exist in SENTINEL:
- Agent Studio: visual reasoning trace (MCP HTTP endpoint)
- ADK (this file): code-first, Gemini model, verifiable tool calls

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

def _configure_adk():
    """Configure ADK to use the right Gemini backend (Vertex AI or direct API key)."""
    import os
    project = os.getenv("GOOGLE_PROJECT_ID", "")
    api_key = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))

    if project:
        # Vertex AI mode — set env vars ADK looks for
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project)
        os.environ.setdefault("GOOGLE_CLOUD_LOCATION", os.getenv("GOOGLE_LOCATION", "us-central1"))
    elif api_key:
        # Direct API key mode (local dev)
        os.environ.setdefault("GOOGLE_API_KEY", api_key)

_configure_adk()

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

def create_sentinel_agent() -> Optional[object]:
    """Create the SENTINEL ADK agent with all tools."""
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

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    return Agent(
        name="SENTINEL",
        model=model,
        description="Business Flight Recorder — records decisions with Fivetran data context and traces causal chains",
        instruction=SYSTEM_PROMPT,
        tools=tools,
    )


# Singleton runner — initialised once per process
_runner: Optional[Runner] = None
_session_service: Optional[InMemorySessionService] = None


def get_runner():
    """Return singleton ADK runner. Initialised on first call."""
    global _runner, _session_service
    if _runner is not None:
        return _runner, _session_service

    agent = create_sentinel_agent()
    if agent is None:
        return None, None

    _session_service = InMemorySessionService()
    _runner = Runner(
        agent=agent,
        app_name="sentinel",
        session_service=_session_service,
    )
    return _runner, _session_service


async def run_agent(message: str, session_id: str = "default") -> str:
    """
    Run the SENTINEL ADK agent. Returns the final text response.
    ADK 2.0: session methods are async; Content/Part from google.genai.types.
    """
    if not _ADK_AVAILABLE:
        return "ADK not available — install google-adk."

    runner, session_service = get_runner()
    if runner is None:
        return "ADK agent could not be initialised."

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

    async for event in runner.run_async(
        user_id="user",
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    final_text += part.text

    return final_text or "No response generated."
