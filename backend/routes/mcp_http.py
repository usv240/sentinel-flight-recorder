"""
MCP Streamable HTTP Transport endpoint.

Implements the MCP 2025-03-26 spec so Google Cloud Agent Studio can connect
to SENTINEL's Fivetran MCP proxy via HTTP — no local process needed.

Endpoint: POST /api/mcp
Agent Studio connects to: https://sentinel-38381883054.us-central1.run.app/api/mcp
"""

import json
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from ..services.mcp_client import call_mcp_tool

router = APIRouter()

# Active sessions (in-memory; single instance Cloud Run is fine for demo)
_sessions: dict = {}

# Tools exposed to Agent Studio — wraps Fivetran MCP + SENTINEL API
_TOOLS = [
    {
        "name": "list_fivetran_connectors",
        "description": "List all Fivetran-connected data sources. Always call this first to show which data sources are available.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "trigger_fivetran_sync",
        "description": "Trigger a live Fivetran sync on a connector to get fresh data before snapshotting metrics.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "connection_id": {
                    "type": "string",
                    "description": "The Fivetran connector ID to sync (e.g. 'humble_currently')",
                }
            },
            "required": ["connection_id"],
        },
    },
    {
        "name": "get_fivetran_schema",
        "description": "Get the schema of a Fivetran connector to understand what metrics are available.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "connection_id": {
                    "type": "string",
                    "description": "The Fivetran connector ID",
                }
            },
            "required": ["connection_id"],
        },
    },
    {
        "name": "get_metrics_snapshot",
        "description": "Get the current business metrics snapshot from Fivetran-connected BigQuery sources.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "demo_scenario": {
                    "type": "string",
                    "enum": ["acmesaas", "qwikster"],
                    "description": "Optional demo scenario name",
                }
            },
            "required": [],
        },
    },
    {
        "name": "check_early_warnings",
        "description": "Check current metrics against historical bad-outcome patterns. Returns active early warnings.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "demo_scenario": {
                    "type": "string",
                    "enum": ["acmesaas", "qwikster"],
                }
            },
            "required": [],
        },
    },
    {
        "name": "log_decision",
        "description": "Record a business decision with a full Fivetran metrics snapshot at this exact moment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "decision_text": {"type": "string", "description": "What was decided"},
                "decision_type": {
                    "type": "string",
                    "enum": ["pricing", "hiring", "product", "strategy", "operational"],
                },
                "rationale": {"type": "string", "description": "Why this decision was made"},
            },
            "required": ["decision_text", "decision_type"],
        },
    },
    {
        "name": "trace_causal_chain",
        "description": "Trace the causal chain between a past decision and a bad outcome. Returns Pearson r correlation and days of warning missed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scenario": {
                    "type": "string",
                    "enum": ["acmesaas", "qwikster"],
                    "description": "Demo scenario to trace",
                }
            },
            "required": ["scenario"],
        },
    },
    {
        "name": "ask_sentinel",
        "description": "Ask SENTINEL a question about the decision history using Gemini 3 causal AI.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "demo_scenario": {"type": "string", "enum": ["acmesaas", "qwikster"]},
            },
            "required": ["question"],
        },
    },
    {
        "name": "run_monitoring_cycle",
        "description": "Trigger the autonomous monitoring cycle: Fivetran MCP sync → BigQuery snapshot → Gemini warning analysis.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


async def _call_tool(name: str, arguments: dict) -> str:
    """Route tool calls to the appropriate backend service (in-process)."""
    try:
        if name == "list_fivetran_connectors":
            result = await call_mcp_tool("list_connections", {})
            items = result.get("data", {}).get("items", result.get("connectors", []))
            return json.dumps({"connectors": items, "count": len(items)}, default=str)

        if name == "trigger_fivetran_sync":
            cid = arguments.get("connection_id", "")
            result = await call_mcp_tool("trigger_sync", {"connection_id": cid})
            return json.dumps({"triggered": True, "connection_id": cid, "result": result}, default=str)

        if name == "get_fivetran_schema":
            cid = arguments.get("connection_id", "")
            result = await call_mcp_tool("get_connector_schema", {"connector_id": cid})
            return json.dumps(result, default=str)

        if name == "get_metrics_snapshot":
            from ..services.context_builder import build_metrics_snapshot
            scenario = arguments.get("demo_scenario")
            snap = await build_metrics_snapshot(scenario or None)
            clean = {k: v for k, v in snap.items() if not k.startswith("_") and k != "raw"}
            return json.dumps({"snapshot": clean, "flags": snap.get("_flags", [])}, default=str)

        if name == "check_early_warnings":
            from ..services.context_builder import build_metrics_snapshot
            from ..services.warning_engine import check_warnings
            scenario = arguments.get("demo_scenario")
            snap = await build_metrics_snapshot(scenario or None)
            warnings = await check_warnings(snap, demo_scenario=scenario)
            return json.dumps({"warnings": warnings, "count": len(warnings)}, default=str)

        if name == "log_decision":
            from ..services.context_builder import build_metrics_snapshot
            from ..db import mongodb
            from ..services.output_writer import write_decision
            snap = await build_metrics_snapshot()
            doc = {
                "decision_text": arguments.get("decision_text", ""),
                "decision_type": arguments.get("decision_type", "strategy"),
                "rationale": arguments.get("rationale", ""),
                "auto_detected": False,
                "metrics_snapshot": snap,
            }
            did = await mongodb.insert_decision(doc)
            write_decision(doc, snap)
            return json.dumps({"decision_id": did, "flags": snap.get("_flags", [])}, default=str)

        if name == "trace_causal_chain":
            from ..services.causal_tracer import _build_demo_trace
            scenario = arguments.get("scenario", "acmesaas")
            trace = await _build_demo_trace(scenario)
            return json.dumps({
                "outcome": trace.get("outcome_description"),
                "pearson_r": trace.get("pearson_r"),
                "days_of_warning": trace.get("days_of_warning"),
                "narrative": trace.get("narrative"),
            }, default=str)

        if name == "ask_sentinel":
            from ..routes.ask import _SCENARIO_CONTEXT
            from ..services.gemini_client import answer_with_scenario_context, answer_why_question
            from ..db import mongodb
            question = arguments.get("question", "")
            scenario = arguments.get("demo_scenario")
            if scenario and scenario in _SCENARIO_CONTEXT:
                result = await answer_with_scenario_context(question, _SCENARIO_CONTEXT[scenario])
            else:
                decisions = await mongodb.get_decisions(limit=20)
                result = await answer_why_question(question, decisions)
            return json.dumps(result, default=str)

        if name == "run_monitoring_cycle":
            from ..services.monitor import run_monitoring_cycle
            import asyncio
            asyncio.create_task(run_monitoring_cycle())
            return json.dumps({"triggered": True, "message": "Monitoring cycle started"})

        return json.dumps({"error": f"Unknown tool: {name}"})

    except Exception as e:
        return json.dumps({"error": str(e)})


@router.get("")
async def mcp_discovery():
    """
    MCP discovery / health probe.

    The MCP Streamable HTTP transport is POST-driven (JSON-RPC), but Google Cloud
    Agent Builder / Agent Studio and other MCP hosts often issue a GET to the
    endpoint first to discover the server before connecting. Returning a clean
    200 with server metadata + the tool catalogue makes that probe succeed and
    documents the endpoint for anyone who opens it in a browser.
    """
    return JSONResponse(content={
        "server": {
            "name": "SENTINEL-Fivetran-MCP",
            "version": "2.0.0",
            "description": "SENTINEL Business Flight Recorder — Fivetran MCP proxy for Google Cloud Agent Builder",
        },
        "protocolVersion": "2025-03-26",
        "transport": "streamable-http",
        "capabilities": {"tools": {"listChanged": False}},
        "tools": [{"name": t["name"], "description": t["description"]} for t in _TOOLS],
        "usage": {
            "connect": "POST JSON-RPC 2.0 to this same URL",
            "methods": ["initialize", "tools/list", "tools/call"],
            "agent_builder": "Add as an MCP server in Agent Studio using this URL",
        },
    })


@router.post("")
async def mcp_endpoint(request: Request):
    """MCP Streamable HTTP transport — single endpoint for all JSON-RPC messages."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    method = body.get("method", "")
    params = body.get("params", {})
    req_id = body.get("id")  # None for notifications

    # ── Notifications (no response required) ─────────────────────────────────
    if method == "notifications/initialized":
        return JSONResponse(status_code=202, content={})

    # ── Initialize ────────────────────────────────────────────────────────────
    if method == "initialize":
        session_id = str(uuid.uuid4())
        _sessions[session_id] = {"initialized": True}
        response = JSONResponse(content={
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": "SENTINEL-Fivetran-MCP",
                    "version": "2.0.0",
                    "description": "SENTINEL Business Flight Recorder — Fivetran MCP proxy",
                },
            },
        })
        response.headers["Mcp-Session-Id"] = session_id
        return response

    # ── Tools list ────────────────────────────────────────────────────────────
    if method == "tools/list":
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": _TOOLS},
        })

    # ── Tool call ─────────────────────────────────────────────────────────────
    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result_text = await _call_tool(tool_name, arguments)
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": result_text}],
                "isError": False,
            },
        })

    # ── Unknown method ────────────────────────────────────────────────────────
    return JSONResponse(content={
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    })
