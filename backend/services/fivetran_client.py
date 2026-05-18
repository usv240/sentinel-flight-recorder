import os
import httpx
from typing import List, Dict, Any, Optional
from base64 import b64encode

FIVETRAN_BASE = "https://api.fivetran.com/v1"


def _auth_header() -> Dict[str, str]:
    key = os.getenv("FIVETRAN_API_KEY", "")
    secret = os.getenv("FIVETRAN_API_SECRET", "")
    token = b64encode(f"{key}:{secret}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


async def list_connectors() -> List[Dict[str, Any]]:
    group_id = os.getenv("FIVETRAN_GROUP_ID", "")
    if not group_id:
        return _mock_connectors()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FIVETRAN_BASE}/groups/{group_id}/connectors",
            headers=_auth_header(),
            timeout=15,
        )
        if resp.status_code != 200:
            return _mock_connectors()
        data = resp.json()
        return data.get("data", {}).get("items", [])


async def get_connector(connector_id: str) -> Optional[Dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FIVETRAN_BASE}/connectors/{connector_id}",
            headers=_auth_header(),
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        return resp.json().get("data")


async def trigger_sync(connector_id: str) -> bool:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{FIVETRAN_BASE}/connectors/{connector_id}/sync",
            headers=_auth_header(),
            timeout=15,
        )
        return resp.status_code == 200


async def get_sync_history(connector_id: str, limit: int = 10) -> List[Dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FIVETRAN_BASE}/connectors/{connector_id}/history/sync",
            headers=_auth_header(),
            params={"limit": limit},
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        return resp.json().get("data", {}).get("items", [])


async def list_connector_schemas(connector_id: str) -> Dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FIVETRAN_BASE}/connectors/{connector_id}/schemas",
            headers=_auth_header(),
            timeout=15,
        )
        if resp.status_code != 200:
            return {}
        return resp.json().get("data", {})


def _mock_connectors() -> List[Dict]:
    """Returns mock connectors for demo mode when Fivetran not configured."""
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
