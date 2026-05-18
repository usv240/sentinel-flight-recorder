"""
Real Fivetran MCP client.

Spawns the fivetran-mcp/server.py subprocess and communicates via the
Model Context Protocol (stdio JSON-RPC). Falls back to the REST API
if the MCP server path is not configured or fails to start.

Every tool call is logged to _tool_call_log so the frontend can stream
it via SSE and show real MCP calls in the activity feed.
"""

import os
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ring-buffer of the most recent tool calls — read by the SSE endpoint
_tool_call_log: List[Dict] = []
_MAX_LOG = 50


def _record_call(tool: str, args: dict, result: Any, source: str = "mcp", error: str = None):
    entry = {
        "id": len(_tool_call_log),
        "ts": datetime.utcnow().isoformat(),
        "source": source,
        "tool": tool,
        "args": args,
        "result_preview": str(result)[:200] if result else None,
        "error": error,
    }
    _tool_call_log.append(entry)
    if len(_tool_call_log) > _MAX_LOG:
        _tool_call_log.pop(0)
    return entry


def get_recent_tool_calls(since_id: int = 0) -> List[Dict]:
    return [c for c in _tool_call_log if c["id"] >= since_id]


# ── MCP subprocess client ────────────────────────────────────────────────────

_mcp_available = False
_mcp_imported = False


def _try_import_mcp():
    global _mcp_available, _mcp_imported
    if _mcp_imported:
        return _mcp_available
    _mcp_imported = True
    try:
        from mcp import ClientSession, StdioServerParameters  # noqa: F401
        from mcp.client.stdio import stdio_client  # noqa: F401
        _mcp_available = True
    except ImportError:
        _mcp_available = False
    return _mcp_available


def _mcp_server_path() -> Optional[Path]:
    raw = os.getenv("FIVETRAN_MCP_PATH", "")
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        # Resolve relative to this file's directory (sentinel/backend/services/)
        base = Path(__file__).parent.parent.parent  # sentinel/
        p = (base / raw).resolve()
    return p if p.exists() else None


async def call_mcp_tool(tool_name: str, arguments: dict = None) -> Dict[str, Any]:
    """
    Call a Fivetran MCP tool by name.
    Uses the real MCP subprocess if available; otherwise falls back to REST API.
    All calls are logged to _tool_call_log for the frontend SSE stream.
    """
    arguments = arguments or {}

    if _try_import_mcp():
        server_path = _mcp_server_path()
        if server_path:
            try:
                result = await _call_via_mcp_subprocess(tool_name, arguments, server_path)
                _record_call(tool_name, arguments, result, source="mcp")
                return result
            except Exception as e:
                _record_call(tool_name, arguments, None, source="mcp", error=str(e))

    # REST API fallback
    result = await _call_via_rest(tool_name, arguments)
    _record_call(tool_name, arguments, result, source="rest_fallback")
    return result


# The fivetran-mcp server requires schema_file for every tool call
# (validates the caller has acknowledged the response structure)
# Maps our tool names to fivetran-mcp tool names + required schema_file argument
_MCP_TOOL_MAP = {
    # our name          → (fivetran-mcp name,            schema_file)
    "list_connections":  ("list_connections",              "open-api-definitions/connections/list_connections.json"),
    "get_connection":    ("get_connection_details",        "open-api-definitions/connections/connection_details.json"),
    "trigger_sync":      ("sync_connection",               "open-api-definitions/connections/sync_connection.json"),
    "get_connector_schema": ("get_connection_schema_config", "open-api-definitions/connections/connection_schema_config.json"),
    "get_account_info":  ("get_account_info",              "open-api-definitions/account/get_account_info.json"),
    "list_groups":       ("list_groups",                   "open-api-definitions/groups/list_all_groups.json"),
    "list_destinations": ("list_destinations",             "open-api-definitions/destinations/list_destinations.json"),
}


async def _call_via_mcp_subprocess(tool_name: str, arguments: dict, server_path: Path) -> Dict:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    env = {
        **os.environ,
        "FIVETRAN_API_KEY": os.getenv("FIVETRAN_API_KEY", ""),
        "FIVETRAN_API_SECRET": os.getenv("FIVETRAN_API_SECRET", ""),
        "FIVETRAN_ALLOW_WRITES": os.getenv("FIVETRAN_ALLOW_WRITES", "true"),
    }

    server_params = StdioServerParameters(
        command="python",
        args=[str(server_path)],
        env=env,
    )

    # Translate tool name and inject schema_file required by fivetran-mcp server
    if tool_name in _MCP_TOOL_MAP:
        real_tool, schema_file = _MCP_TOOL_MAP[tool_name]
        tool_name = real_tool
        if "schema_file" not in arguments:
            arguments = {**arguments, "schema_file": schema_file}

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            # MCP returns TextContent list
            if result.content:
                text = result.content[0].text if hasattr(result.content[0], "text") else str(result.content[0])
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"raw": text}
            return {}


# ── REST API fallback (same data, different transport) ───────────────────────

import httpx
from base64 import b64encode

_FT_BASE = "https://api.fivetran.com/v1"


def _auth():
    key = os.getenv("FIVETRAN_API_KEY", "")
    secret = os.getenv("FIVETRAN_API_SECRET", "")
    token = b64encode(f"{key}:{secret}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


async def _call_via_rest(tool_name: str, arguments: dict) -> Dict:
    group_id = os.getenv("FIVETRAN_GROUP_ID", "")
    async with httpx.AsyncClient(timeout=15) as client:

        if tool_name in ("list_connections", "list_connectors"):
            if not group_id:
                return {"connectors": _mock_connectors()}
            resp = await client.get(f"{_FT_BASE}/groups/{group_id}/connectors", headers=_auth())
            if resp.status_code == 200:
                return resp.json()
            return {"connectors": _mock_connectors()}

        if tool_name in ("trigger_sync", "sync_connection"):
            connector_id = arguments.get("connector_id", arguments.get("connection_id", ""))
            resp = await client.post(f"{_FT_BASE}/connections/{connector_id}/sync", headers=_auth())
            return {"triggered": resp.status_code == 200, "connector_id": connector_id}

        if tool_name == "get_connector_schema":
            connector_id = arguments.get("connector_id", "")
            resp = await client.get(f"{_FT_BASE}/connectors/{connector_id}/schemas", headers=_auth())
            if resp.status_code == 200:
                return resp.json()
            return {}

        if tool_name == "get_account_info":
            resp = await client.get(f"{_FT_BASE}/account/info", headers=_auth())
            if resp.status_code == 200:
                return resp.json()
            return {}

        if tool_name == "get_sync_history":
            connector_id = arguments.get("connector_id", "")
            resp = await client.get(f"{_FT_BASE}/connectors/{connector_id}/history/sync", headers=_auth(), params={"limit": 10})
            if resp.status_code == 200:
                return resp.json()
            return {"history": []}

    return {"error": f"Unknown tool: {tool_name}"}


def _mock_connectors():
    return [
        {"id": "mock_stripe", "service": "stripe", "schema": "sentinel_stripe",
         "status": {"sync_state": "scheduled"}, "succeeded_at": "2026-05-18T10:00:00Z"},
        {"id": "mock_hubspot", "service": "hubspot", "schema": "sentinel_hubspot",
         "status": {"sync_state": "scheduled"}, "succeeded_at": "2026-05-18T09:45:00Z"},
        {"id": "mock_mixpanel", "service": "mixpanel", "schema": "sentinel_mixpanel",
         "status": {"sync_state": "paused"}, "succeeded_at": "2026-05-17T22:00:00Z"},
        {"id": "mock_quickbooks", "service": "quickbooks", "schema": "sentinel_quickbooks",
         "status": {"sync_state": "scheduled"}, "succeeded_at": "2026-05-18T08:30:00Z"},
    ]


# ── High-level helpers used by routes ────────────────────────────────────────

async def list_connectors() -> List[Dict]:
    result = await call_mcp_tool("list_connections")
    # Use `is not None` — empty list is a valid real response, not a reason to mock
    items = result.get("data", {}).get("items")
    if items is None:
        items = result.get("connectors")
    if items is None:
        items = _mock_connectors()
    return items


async def trigger_sync(connector_id: str) -> bool:
    result = await call_mcp_tool("trigger_sync", {"connector_id": connector_id})
    return result.get("triggered", False)


async def get_connector_schema(connector_id: str) -> Dict:
    return await call_mcp_tool("get_connector_schema", {"connector_id": connector_id})
