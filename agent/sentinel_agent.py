"""
SENTINEL ADK Agent — code-first Google Cloud Agent Builder.

Uses google-adk with FunctionTools, same pattern as the ADK SDK.
Model: gemini-3-flash-preview (Gemini 3) via Vertex AI.

This runs alongside the Agent Studio agent:
- Agent Studio: visual reasoning trace for judges to see in the UI
- ADK (this file): Gemini 3 throughout, code-verifiable, stronger tech score

Imported by backend/routes/agent_chat.py and exposed at POST /api/agent/chat.
"""

import os
import json
import asyncio
from typing import Optional

# ADK imports — graceful fallback if not installed
try:
    from google.adk.agents import Agent
    from google.adk.tools import FunctionTool
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    _ADK_AVAILABLE = True
except ImportError:
    _ADK_AVAILABLE = False

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
Always name which Fivetran MCP tool you called. Transparency is what makes you trustworthy."""


# ── Tool implementations ──────────────────────────────────────────────────────

async def list_fivetran_connectors() -> str:
    """List all Fivetran-connected data sources via MCP."""
    from backend.services.mcp_client import call_mcp_tool
    result = await call_mcp_tool("list_connections", {})
    items = result.get("data", {}).get("items", result.get("connectors", []))
    return json.dumps({"connectors": items, "count": len(items)}, default=str)


async def trigger_fivetran_sync(connection_id: str) -> str:
    """Trigger a live Fivetran sync on a connector to get fresh data."""
    from backend.services.mcp_client import call_mcp_tool
    result = await call_mcp_tool("trigger_sync", {"connection_id": connection_id})
    return json.dumps({"triggered": True, "connection_id": connection_id}, default=str)


async def get_metrics_snapshot(demo_scenario: Optional[str] = None) -> str:
    """Get the current business metrics from Fivetran-connected BigQuery sources."""
    from backend.services.context_builder import build_metrics_snapshot
    snap = await build_metrics_snapshot(demo_scenario or None)
    clean = {k: v for k, v in snap.items() if not k.startswith("_") and k != "raw"}
    return json.dumps({"snapshot": clean, "flags": snap.get("_flags", [])}, default=str)


async def check_early_warnings(demo_scenario: Optional[str] = None) -> str:
    """Check current metrics against historical bad-outcome patterns."""
    from backend.services.context_builder import build_metrics_snapshot
    from backend.services.warning_engine import check_warnings
    snap = await build_metrics_snapshot(demo_scenario or None)
    warnings = await check_warnings(snap, demo_scenario=demo_scenario)
    return json.dumps({"warnings": warnings, "count": len(warnings)}, default=str)


async def log_decision(decision_text: str, decision_type: str, rationale: str = "") -> str:
    """Record a business decision with a full Fivetran metrics snapshot."""
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


async def trace_causal_chain(scenario: str = "acmesaas") -> str:
    """Trace the causal chain for a scenario. Returns Pearson r and days of warning."""
    from backend.services.causal_tracer import _build_demo_trace
    trace = await _build_demo_trace(scenario)
    return json.dumps({
        "outcome": trace.get("outcome_description"),
        "pearson_r": trace.get("pearson_r"),
        "p_value": trace.get("p_value"),
        "days_of_warning": trace.get("days_of_warning"),
        "narrative": trace.get("narrative"),
        "causal_chain": trace.get("causal_chain", []),
    }, default=str)


async def ask_about_decision_history(question: str, demo_scenario: Optional[str] = None) -> str:
    """Ask a question about the decision log using Gemini 3 causal AI."""
    from backend.routes.ask import _SCENARIO_CONTEXT
    from backend.services.gemini_client import answer_with_scenario_context, answer_why_question
    from backend.db import mongodb
    if demo_scenario and demo_scenario in _SCENARIO_CONTEXT:
        result = await answer_with_scenario_context(question, _SCENARIO_CONTEXT[demo_scenario])
    else:
        decisions = await mongodb.get_decisions(limit=20)
        result = await answer_why_question(question, decisions)
    return json.dumps(result, default=str)


# ── Agent factory ─────────────────────────────────────────────────────────────

def create_sentinel_agent():
    """Create the SENTINEL ADK agent with Gemini 3 and all Fivetran MCP tools."""
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

    agent = Agent(
        name="SENTINEL",
        model=os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"),
        description="Business Flight Recorder — records decisions with Fivetran data context and traces causal chains",
        instruction=SYSTEM_PROMPT,
        tools=tools,
    )

    return agent


# Singleton agent instance
_agent = None
_runner = None
_session_service = None


def get_runner():
    """Return the singleton ADK runner — initialised once."""
    global _agent, _runner, _session_service
    if _runner is not None:
        return _runner, _session_service

    _agent = create_sentinel_agent()
    if _agent is None:
        return None, None

    _session_service = InMemorySessionService()
    _runner = Runner(
        agent=_agent,
        app_name="sentinel",
        session_service=_session_service,
    )
    return _runner, _session_service


async def run_agent(message: str, session_id: str = "default") -> str:
    """Run the ADK agent with a message. Returns the final text response."""
    from google.adk.types import Content, Part

    runner, session_service = get_runner()
    if runner is None:
        return "ADK not available. Install google-adk."

    # Ensure session exists
    try:
        session_service.get_session(app_name="sentinel", user_id="user", session_id=session_id)
    except Exception:
        session_service.create_session(app_name="sentinel", user_id="user", session_id=session_id)

    content = Content(role="user", parts=[Part(text=message)])
    final_text = ""

    async for event in runner.run_async(
        user_id="user",
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text"):
                    final_text += part.text

    return final_text or "No response generated."
