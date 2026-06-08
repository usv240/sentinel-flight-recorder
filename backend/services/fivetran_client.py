"""
Fivetran client — thin shim that delegates to mcp_client.
All real calls go through mcp_client which handles MCP subprocess / REST fallback
and logs every call to the tool_call_log for the SSE stream.

This shim exposes the FULL Fivetran platform surface SENTINEL uses:
account, connections, groups, destinations, webhooks and sync history.
"""
from typing import List, Dict, Any, Optional
from .mcp_client import (
    list_connectors as _list_connectors,
    trigger_sync as _trigger_sync,
    get_connector_schema as _get_connector_schema,
    get_account_info as _get_account_info,
    list_groups as _list_groups,
    get_group_details as _get_group_details,
    list_connections_in_group as _list_connections_in_group,
    list_destinations as _list_destinations,
    get_destination_details as _get_destination_details,
    list_webhooks as _list_webhooks,
    get_webhook_details as _get_webhook_details,
    call_mcp_tool,
)


# ── Connections ───────────────────────────────────────────────────────────────
async def list_connectors() -> List[Dict[str, Any]]:
    return await _list_connectors()


async def get_connector(connector_id: str) -> Optional[Dict]:
    result = await call_mcp_tool("get_connection", {"connectionId": connector_id})
    return result.get("data") if result else None


async def trigger_sync(connector_id: str) -> bool:
    return await _trigger_sync(connector_id)


async def get_sync_history(connector_id: str, limit: int = 10) -> List[Dict]:
    result = await call_mcp_tool("get_sync_history", {"connector_id": connector_id, "limit": limit})
    data = result.get("data", {}) if isinstance(result, dict) else {}
    # Some Fivetran responses nest the connector object; surface sync timestamps
    if isinstance(data, dict) and "items" in data:
        return data["items"]
    return data if isinstance(data, list) else ([data] if data else [])


async def list_connector_schemas(connector_id: str) -> Dict:
    return await _get_connector_schema(connector_id)


# ── Account ───────────────────────────────────────────────────────────────────
async def get_account_info() -> Dict:
    return await _get_account_info()


# ── Groups ────────────────────────────────────────────────────────────────────
async def list_groups() -> List[Dict]:
    return await _list_groups()


async def get_group_details(group_id: str) -> Dict:
    return await _get_group_details(group_id)


async def list_connections_in_group(group_id: str) -> List[Dict]:
    return await _list_connections_in_group(group_id)


# ── Destinations ──────────────────────────────────────────────────────────────
async def list_destinations() -> List[Dict]:
    return await _list_destinations()


async def get_destination_details(destination_id: str) -> Dict:
    return await _get_destination_details(destination_id)


# ── Webhooks ──────────────────────────────────────────────────────────────────
async def list_webhooks() -> List[Dict]:
    return await _list_webhooks()


async def get_webhook_details(webhook_id: str) -> Dict:
    return await _get_webhook_details(webhook_id)
