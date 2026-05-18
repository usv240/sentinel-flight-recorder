"""
Fivetran client — thin shim that delegates to mcp_client.
All real calls go through mcp_client which handles MCP subprocess / REST fallback
and logs every call to the tool_call_log for the SSE stream.
"""
from typing import List, Dict, Any, Optional
from .mcp_client import (
    list_connectors as _list_connectors,
    trigger_sync as _trigger_sync,
    get_connector_schema as _get_connector_schema,
    call_mcp_tool,
)


async def list_connectors() -> List[Dict[str, Any]]:
    return await _list_connectors()


async def get_connector(connector_id: str) -> Optional[Dict]:
    result = await call_mcp_tool("get_connection", {"connectionId": connector_id})
    return result.get("data") if result else None


async def trigger_sync(connector_id: str) -> bool:
    return await _trigger_sync(connector_id)


async def get_sync_history(connector_id: str, limit: int = 10) -> List[Dict]:
    result = await call_mcp_tool("get_sync_history", {"connector_id": connector_id, "limit": limit})
    return result.get("data", {}).get("items", [])


async def list_connector_schemas(connector_id: str) -> Dict:
    return await _get_connector_schema(connector_id)
