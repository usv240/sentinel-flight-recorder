from fastapi import APIRouter
from ..services.fivetran_client import list_connectors, trigger_sync, get_sync_history
from ..services.bigquery_pipeline import get_connector_registry

router = APIRouter()


@router.get("/list")
async def get_connectors(demo_mode: bool = True):
    connectors = await list_connectors()
    registry = get_connector_registry()
    enriched = []
    for c in connectors:
        enriched.append({
            "id": c.get("id"),
            "service": c.get("service"),
            "schema": c.get("schema"),
            "status": c.get("status", {}).get("sync_state", "unknown"),
            "last_sync": c.get("succeeded_at"),
            "demo": demo_mode,
        })
    return {
        "connectors": enriched,
        "count": len(enriched),
        "bigquery_registry": registry,
        "data_sources": list(registry.keys()),
    }


@router.post("/{connector_id}/sync")
async def force_sync(connector_id: str):
    success = await trigger_sync(connector_id)
    return {"triggered": success, "connector_id": connector_id}


@router.get("/{connector_id}/history")
async def sync_history(connector_id: str):
    history = await get_sync_history(connector_id)
    return {"history": history, "connector_id": connector_id}
