"""
SENTINEL Fivetran connector + platform routes.

Exposes the FULL Fivetran platform surface SENTINEL drives via MCP:
  account · groups · connections · destinations · webhooks · sync history · schema

Every route logs its MCP/REST call to the tool-call feed, so you can watch
SENTINEL exercise the real Fivetran integration live.
"""
from fastapi import APIRouter
from ..services.fivetran_client import (
    list_connectors, trigger_sync, get_sync_history, list_connector_schemas,
    get_account_info, list_groups, get_group_details, list_connections_in_group,
    list_destinations, get_destination_details, list_webhooks,
)
from ..services.bigquery_pipeline import get_connector_registry

router = APIRouter()


def _norm(c: dict) -> dict:
    """Normalise a Fivetran connector object into SENTINEL's flat shape."""
    cid = c.get("id", "")
    status = c.get("status", {})
    sync_state = status.get("sync_state") if isinstance(status, dict) else status
    return {
        "id": cid,
        "service": c.get("service"),
        "schema": c.get("schema"),
        "status": sync_state or "unknown",
        "setup_state": status.get("setup_state") if isinstance(status, dict) else None,
        "last_sync": c.get("succeeded_at"),
        "failed_at": c.get("failed_at"),
        "sync_frequency": c.get("sync_frequency"),
        "live": not cid.startswith("mock_"),  # real connector = live
    }


@router.get("/list")
async def get_connectors():
    connectors = await list_connectors()
    registry = get_connector_registry()
    enriched = [_norm(c) for c in connectors]
    return {
        "connectors": enriched,
        "count": len(enriched),
        "live_count": sum(1 for c in enriched if c["live"]),
        "bigquery_registry": registry,
        "data_sources": list(registry.keys()),
    }


@router.get("/platform")
async def platform_overview():
    """
    One-shot Fivetran platform overview — account, groups, connectors,
    destinations and webhooks in a single response. Powers the Fivetran
    control panel in the UI and proves end-to-end breadth of integration.
    """
    account = await get_account_info()
    groups = await list_groups()
    connectors = await list_connectors()
    destinations = await list_destinations()
    webhooks = await list_webhooks()
    registry = get_connector_registry()

    enriched = [_norm(c) for c in connectors]
    return {
        "account": account,
        "groups": groups,
        "connectors": enriched,
        "destinations": destinations,
        "webhooks": webhooks,
        "bigquery_registry": registry,
        "summary": {
            "groups": len(groups),
            "connectors": len(enriched),
            "live_connectors": sum(1 for c in enriched if c["live"]),
            "destinations": len(destinations),
            "webhooks": len(webhooks),
            "registered_tables": len(registry),
        },
        "transport": "fivetran-mcp (stdio JSON-RPC) → REST fallback",
    }


@router.get("/account")
async def account_info():
    return {"account": await get_account_info()}


@router.get("/groups")
async def groups():
    items = await list_groups()
    return {"groups": items, "count": len(items)}


@router.get("/groups/{group_id}")
async def group_details(group_id: str):
    details = await get_group_details(group_id)
    conns = await list_connections_in_group(group_id)
    return {"group": details, "connections": [_norm(c) for c in conns], "count": len(conns)}


@router.get("/destinations")
async def destinations():
    items = await list_destinations()
    return {"destinations": items, "count": len(items)}


@router.get("/destinations/{destination_id}")
async def destination_details(destination_id: str):
    return {"destination": await get_destination_details(destination_id)}


@router.get("/webhooks")
async def webhooks():
    items = await list_webhooks()
    return {"webhooks": items, "count": len(items)}


@router.post("/{connector_id}/sync")
async def force_sync(connector_id: str):
    success = await trigger_sync(connector_id)
    return {"triggered": success, "connector_id": connector_id}


@router.get("/{connector_id}/history")
async def sync_history(connector_id: str):
    history = await get_sync_history(connector_id)
    return {"history": history, "connector_id": connector_id, "count": len(history)}


@router.get("/{connector_id}/schema")
async def connector_schema(connector_id: str):
    schema = await list_connector_schemas(connector_id)
    return {"schema": schema, "connector_id": connector_id}
