"""
SENTINEL Fivetran Webhook Receiver — event-driven sync.

Fivetran can POST a webhook whenever a connector finishes a sync, fails, or
changes state. SENTINEL registers this endpoint as a Fivetran webhook so it
becomes EVENT-DRIVEN, not just a 30-minute poller: the moment fresh data lands
in BigQuery, Fivetran notifies SENTINEL and an analysis cycle fires immediately.

Security: if FIVETRAN_WEBHOOK_SECRET is set, every payload's HMAC-SHA256
signature (X-Fivetran-Signature-256 header) is verified before processing.

Docs: https://fivetran.com/docs/rest-api/webhooks

Endpoints:
  POST /api/fivetran/webhook        receive a Fivetran event
  GET  /api/fivetran/webhook/recent recent events SENTINEL has received
"""

import os
import hmac
import hashlib
import asyncio
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..services.mcp_client import record_inbound_event

log = logging.getLogger("sentinel.webhook")
router = APIRouter()

# Ring buffer of received webhook events (for the UI feed)
_events: list = []
_MAX_EVENTS = 50

# Events that mean "fresh data is available → re-analyse now"
_SYNC_COMPLETE_EVENTS = {"sync_end", "resync_end", "sync_succeeded"}
_FAILURE_EVENTS = {"connection_failure", "sync_failure", "sync_failed"}


def _verify_signature(raw_body: bytes, signature_header: str) -> bool:
    """Verify Fivetran's HMAC-SHA256 webhook signature. No-op if no secret set."""
    secret = os.getenv("FIVETRAN_WEBHOOK_SECRET", "")
    if not secret:
        return True  # verification disabled — accept (dev / demo)
    if not signature_header:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    # Fivetran sends "v1=<hex>" or a bare hex digest depending on config
    provided = signature_header.split("=", 1)[-1].strip()
    return hmac.compare_digest(expected, provided)


@router.post("/webhook")
async def receive_webhook(request: Request):
    """Receive a Fivetran webhook event and react to it."""
    raw = await request.body()
    sig = request.headers.get("x-fivetran-signature-256", "") or request.headers.get("x-fivetran-signature", "")

    if not _verify_signature(raw, sig):
        log.warning("Fivetran webhook rejected — bad signature")
        return JSONResponse(status_code=401, content={"ok": False, "error": "invalid signature"})

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid JSON"})

    event = (payload.get("event") or payload.get("type") or "unknown").lower()
    connector_id = payload.get("connector_id") or payload.get("connection_id") or "?"

    record = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "connector_id": connector_id,
        "destination_group_id": payload.get("destination_group_id"),
        "connector_type": payload.get("connector_type"),
    }
    _events.append(record)
    if len(_events) > _MAX_EVENTS:
        _events.pop(0)

    # Mirror into the live tool-call feed (bidirectional Fivetran integration)
    record_inbound_event(event, payload)
    log.info(f"Fivetran webhook: {event} ← connector={connector_id}")

    # ── React: a completed sync means fresh BigQuery data → analyse now ──────
    reacted = None
    if event in _SYNC_COMPLETE_EVENTS:
        from ..services.monitor import run_monitoring_cycle
        asyncio.create_task(run_monitoring_cycle())
        reacted = "monitoring_cycle_triggered"
        log.info("Webhook triggered an immediate SENTINEL monitoring cycle")
    elif event in _FAILURE_EVENTS:
        try:
            from ..services.output_writer import _log_session
            _log_session(
                "FIVETRAN WEBHOOK: CONNECTION FAILURE",
                f"Connector `{connector_id}` reported `{event}`. SENTINEL flagged the data source as stale."
            )
        except Exception:
            pass
        reacted = "failure_logged"

    return {"ok": True, "event": event, "connector_id": connector_id, "reacted": reacted}


@router.get("/webhook/recent")
async def recent_webhook_events(limit: int = 20):
    """Recent Fivetran events SENTINEL has received (most recent first)."""
    return {"events": list(reversed(_events))[:limit], "count": len(_events)}
