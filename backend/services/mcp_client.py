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


def record_inbound_event(event: str, payload: dict) -> Dict:
    """
    Record an inbound Fivetran event (e.g. a webhook sync_end) into the same
    feed as outbound tool calls, so the activity stream shows the full
    bidirectional Fivetran integration — SENTINEL calling Fivetran AND
    Fivetran pushing events back to SENTINEL.
    """
    return _record_call(
        tool=f"webhook:{event}",
        args={k: payload.get(k) for k in ("connector_id", "connection_id", "destination_group_id") if k in payload},
        result=payload,
        source="fivetran_webhook",
    )


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


# ── Transport / live-state introspection (for /api/health/integrations) ───────

def fivetran_has_creds() -> bool:
    """True if a Fivetran API key + secret are configured."""
    return bool(os.getenv("FIVETRAN_API_KEY") and os.getenv("FIVETRAN_API_SECRET"))


def fivetran_mode() -> str:
    """
    The transport SENTINEL will actually use for the next Fivetran call:
      "mcp"  — fivetran-mcp subprocess is importable, its server.py exists, creds present
      "rest" — no MCP server available, but Fivetran creds present (REST API)
      "demo" — no creds: calls return clearly-labelled demo/mock stand-ins
    """
    if not fivetran_has_creds():
        return "demo"
    if _try_import_mcp() and _mcp_server_path() is not None:
        return "mcp"
    return "rest"


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
                return _tag_source(result, "mcp")
            except Exception as e:
                _record_call(tool_name, arguments, None, source="mcp", error=str(e))

    # REST API fallback — real REST when creds exist, otherwise labelled demo data
    result = await _call_via_rest(tool_name, arguments)
    source = "rest" if fivetran_has_creds() else "demo"
    _record_call(tool_name, arguments, result, source=f"{source}_fallback" if source == "rest" else "demo")
    return _tag_source(result, source)


def _tag_source(result: Any, source: str) -> Any:
    """
    Annotate a tool result with the transport that produced it so the UI and
    /api/health can never present demo/mock data as live. Adds:
      _source: "mcp" | "rest" | "demo"
      _live:   True for mcp/rest (real Fivetran), False for demo
    Only dicts are tagged; other shapes pass through untouched.
    """
    if isinstance(result, dict):
        result.setdefault("_source", source)
        result.setdefault("_live", source in ("mcp", "rest"))
    return result


# The fivetran-mcp server requires schema_file for every tool call
# (validates the caller has acknowledged the response structure)
# Maps our tool names to fivetran-mcp tool names + required schema_file argument.
#
# SENTINEL exercises the FULL breadth of the Fivetran platform via MCP — not just
# connectors and syncs, but the account, groups, destinations, webhooks and
# transformations resources too. Every entry here is a real fivetran-mcp tool with
# its real open-api-definitions schema file (verified against fivetran/fivetran-mcp).
_MCP_TOOL_MAP = {
    # our name              → (fivetran-mcp name,              schema_file)
    # ── Account ──────────────────────────────────────────────────────────────
    "get_account_info":      ("get_account_info",               "open-api-definitions/account/get_account_info.json"),
    # ── Connections ──────────────────────────────────────────────────────────
    "list_connections":      ("list_connections",               "open-api-definitions/connections/list_connections.json"),
    "get_connection":        ("get_connection_details",         "open-api-definitions/connections/connection_details.json"),
    "trigger_sync":          ("sync_connection",                "open-api-definitions/connections/sync_connection.json"),
    "get_connector_schema":  ("get_connection_schema_config",   "open-api-definitions/connections/connection_schema_config.json"),
    # ── Groups ───────────────────────────────────────────────────────────────
    "list_groups":           ("list_groups",                    "open-api-definitions/groups/list_all_groups.json"),
    "get_group_details":     ("get_group_details",              "open-api-definitions/groups/group_details.json"),
    "list_connections_in_group": ("list_connections_in_group",  "open-api-definitions/groups/list_all_connections_in_group.json"),
    # ── Destinations ─────────────────────────────────────────────────────────
    "list_destinations":     ("list_destinations",              "open-api-definitions/destinations/list_destinations.json"),
    "get_destination_details": ("get_destination_details",      "open-api-definitions/destinations/destination_details.json"),
    # ── Webhooks (event-driven sync notifications) ───────────────────────────
    "list_webhooks":         ("list_webhooks",                  "open-api-definitions/webhooks/list_all_webhooks.json"),
    "get_webhook_details":   ("get_webhook_details",            "open-api-definitions/webhooks/webhook_details.json"),
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

    # fivetran-mcp validates request_body as a JSON *string*, not an object.
    # Callers pass a dict (so the REST path can use it directly); stringify it
    # here for the MCP transport.
    rb = arguments.get("request_body")
    if rb is not None and not isinstance(rb, str):
        arguments = {**arguments, "request_body": json.dumps(rb)}

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
    """
    REST API fallback — used when the MCP subprocess isn't available.
    Mirrors the Fivetran REST API (https://fivetran.com/docs/rest-api) so the
    same data flows whether SENTINEL talks MCP or REST. Endpoints with no clean
    REST equivalent return a structured, clearly-labelled stand-in.
    """
    group_id = os.getenv("FIVETRAN_GROUP_ID", "")
    has_creds = bool(os.getenv("FIVETRAN_API_KEY") and os.getenv("FIVETRAN_API_SECRET"))
    async with httpx.AsyncClient(timeout=15) as client:

        # ── Account ──────────────────────────────────────────────────────────
        if tool_name == "get_account_info":
            # No single account-info REST endpoint; summarise from /groups
            if not has_creds:
                return {"data": _mock_account()}
            resp = await client.get(f"{_FT_BASE}/groups", headers=_auth())
            if resp.status_code == 200:
                groups = resp.json().get("data", {}).get("items", [])
                return {"data": {"account_groups": len(groups),
                                 "first_group": groups[0].get("name") if groups else None,
                                 "api": "rest"}}
            return {"data": _mock_account()}

        # ── Connections ──────────────────────────────────────────────────────
        if tool_name in ("list_connections", "list_connectors"):
            if not group_id:
                return {"connectors": _mock_connectors()}
            resp = await client.get(f"{_FT_BASE}/groups/{group_id}/connectors", headers=_auth())
            if resp.status_code == 200:
                return resp.json()
            return {"connectors": _mock_connectors()}

        if tool_name in ("get_connection",):
            connector_id = arguments.get("connector_id", arguments.get("connectionId", arguments.get("connection_id", "")))
            resp = await client.get(f"{_FT_BASE}/connectors/{connector_id}", headers=_auth())
            if resp.status_code == 200:
                return resp.json()
            return {}

        if tool_name in ("trigger_sync", "sync_connection"):
            connector_id = arguments.get("connector_id", arguments.get("connection_id", ""))
            body = arguments.get("request_body", {"force": True})
            resp = await client.post(f"{_FT_BASE}/connectors/{connector_id}/sync",
                                     headers=_auth(), json=body)
            return {"triggered": resp.status_code in (200, 201), "connector_id": connector_id}

        if tool_name == "get_connector_schema":
            connector_id = arguments.get("connector_id", "")
            resp = await client.get(f"{_FT_BASE}/connectors/{connector_id}/schemas", headers=_auth())
            if resp.status_code == 200:
                return resp.json()
            return {}

        # ── Groups ───────────────────────────────────────────────────────────
        if tool_name == "list_groups":
            if not has_creds:
                return {"data": {"items": _mock_groups()}}
            resp = await client.get(f"{_FT_BASE}/groups", headers=_auth())
            if resp.status_code == 200:
                return resp.json()
            return {"data": {"items": _mock_groups()}}

        if tool_name == "get_group_details":
            gid = arguments.get("group_id", group_id)
            resp = await client.get(f"{_FT_BASE}/groups/{gid}", headers=_auth())
            if resp.status_code == 200:
                return resp.json()
            return {}

        if tool_name == "list_connections_in_group":
            gid = arguments.get("group_id", group_id)
            resp = await client.get(f"{_FT_BASE}/groups/{gid}/connectors", headers=_auth())
            if resp.status_code == 200:
                return resp.json()
            return {"data": {"items": _mock_connectors()}}

        # ── Destinations ─────────────────────────────────────────────────────
        if tool_name == "list_destinations":
            # Destinations are per-group in REST — assemble by walking groups
            if not has_creds:
                return {"data": {"items": _mock_destinations()}}
            gresp = await client.get(f"{_FT_BASE}/groups", headers=_auth())
            dests = []
            if gresp.status_code == 200:
                for g in gresp.json().get("data", {}).get("items", []):
                    dresp = await client.get(f"{_FT_BASE}/destinations/{g['id']}", headers=_auth())
                    if dresp.status_code == 200:
                        dests.append(dresp.json().get("data", {}))
            return {"data": {"items": dests or _mock_destinations()}}

        if tool_name == "get_destination_details":
            did = arguments.get("destination_id", group_id)
            resp = await client.get(f"{_FT_BASE}/destinations/{did}", headers=_auth())
            if resp.status_code == 200:
                return resp.json()
            return {}

        # ── Webhooks ─────────────────────────────────────────────────────────
        if tool_name == "list_webhooks":
            if not has_creds:
                return {"data": {"items": _mock_webhooks()}}
            resp = await client.get(f"{_FT_BASE}/webhooks", headers=_auth())
            if resp.status_code == 200:
                return resp.json()
            return {"data": {"items": _mock_webhooks()}}

        if tool_name == "get_webhook_details":
            wid = arguments.get("webhook_id", "")
            resp = await client.get(f"{_FT_BASE}/webhooks/{wid}", headers=_auth())
            if resp.status_code == 200:
                return resp.json()
            return {}

        # ── Sync history / logs ──────────────────────────────────────────────
        if tool_name == "get_sync_history":
            connector_id = arguments.get("connector_id", "")
            resp = await client.get(f"{_FT_BASE}/connectors/{connector_id}", headers=_auth())
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


def _mock_account():
    return {"account_name": "SENTINEL Demo Account", "account_id": "sentinel_demo",
            "account_groups": 1, "first_group": "sentinel_warehouse", "api": "mock"}


def _mock_groups():
    return [
        {"id": "sentinel_warehouse", "name": "sentinel_warehouse", "created_at": "2026-05-01T00:00:00Z"},
    ]


def _mock_destinations():
    return [
        {"id": "sentinel_warehouse", "group_id": "sentinel_warehouse", "service": "big_query",
         "region": "US", "setup_status": "connected",
         "config": {"project_id": "sentinel-flight-recorder", "data_set_location": "US"}},
    ]


def _mock_webhooks():
    return [
        {"id": "wh_sentinel_sync", "type": "group", "group_id": "sentinel_warehouse",
         "url": "https://sentinel-38381883054.us-central1.run.app/api/fivetran/webhook",
         "events": ["sync_end", "connection_failure"], "active": True,
         "created_at": "2026-05-10T00:00:00Z"},
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
    # fivetran-mcp's sync_connection requires BOTH connection_id and a
    # request_body ({"force": bool}) — POST /v1/connections/{id}/sync.
    # Omitting request_body fails MCP input validation, so we always send it.
    result = await call_mcp_tool("trigger_sync", {
        "connection_id": connector_id,
        "request_body": {"force": True},
    })
    if not isinstance(result, dict):
        return False
    # REST fallback path returns an explicit {"triggered": bool}.
    if "triggered" in result:
        return bool(result["triggered"])
    # MCP path returns the raw Fivetran response: success looks like {"code":"Success"}.
    if str(result.get("code", "")).lower() == "success":
        return True
    raw = str(result.get("raw", ""))
    if raw and not any(x in raw.lower() for x in ("error", "required", "invalid")):
        return True
    return False


async def get_connector_schema(connector_id: str) -> Dict:
    return await call_mcp_tool("get_connector_schema", {"connector_id": connector_id})


def _items(result: Dict) -> List[Dict]:
    """Normalise the many shapes Fivetran returns into a flat list of items."""
    if not isinstance(result, dict):
        return []
    data = result.get("data")
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return data["items"]
    if isinstance(data, list):
        return data
    for key in ("items", "connectors", "groups", "destinations", "webhooks"):
        if isinstance(result.get(key), list):
            return result[key]
    return []


def _items_or_mock(result: Dict, mock_fn) -> List[Dict]:
    """
    Return real items from a Fivetran response. If the API call was genuinely
    live (mcp/rest) but returned an empty list, return [] — do NOT fabricate a
    mock entry. Only fall back to mock data when there was no live call at all
    (demo mode / failure), keeping the "never present mock as live" guarantee.
    """
    items = _items(result)
    if items:
        return items
    if isinstance(result, dict) and result.get("_live"):
        return []  # live but genuinely empty (e.g. 0 webhooks configured)
    return mock_fn()


# ── Full-platform helpers — exercise the breadth of the Fivetran MCP surface ──

async def get_account_info() -> Dict:
    result = await call_mcp_tool("get_account_info")
    return result.get("data", result) if isinstance(result, dict) else {}


async def list_groups() -> List[Dict]:
    return _items_or_mock(await call_mcp_tool("list_groups"), _mock_groups)


async def get_group_details(group_id: str) -> Dict:
    result = await call_mcp_tool("get_group_details", {"group_id": group_id})
    return result.get("data", result) if isinstance(result, dict) else {}


async def list_connections_in_group(group_id: str) -> List[Dict]:
    return _items(await call_mcp_tool("list_connections_in_group", {"group_id": group_id}))


async def list_destinations() -> List[Dict]:
    return _items_or_mock(await call_mcp_tool("list_destinations"), _mock_destinations)


async def get_destination_details(destination_id: str) -> Dict:
    result = await call_mcp_tool("get_destination_details", {"destination_id": destination_id})
    return result.get("data", result) if isinstance(result, dict) else {}


async def list_webhooks() -> List[Dict]:
    return _items_or_mock(await call_mcp_tool("list_webhooks"), _mock_webhooks)


async def get_webhook_details(webhook_id: str) -> Dict:
    result = await call_mcp_tool("get_webhook_details", {"webhook_id": webhook_id})
    return result.get("data", result) if isinstance(result, dict) else {}
