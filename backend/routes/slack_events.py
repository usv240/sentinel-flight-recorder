"""
Slack Events API endpoint for SENTINEL.

Slack POSTs here whenever a message is sent in a monitored channel.
We respond within 3 seconds (Slack hard requirement) by returning 200 immediately
and processing the message as a FastAPI BackgroundTask.

Setup in Slack app dashboard:
  Event Subscriptions → Request URL:
    https://sentinel-38381883054.us-central1.run.app/api/slack/events
  Subscribe to bot events:
    - message.channels   (public channels)
    - message.groups     (private channels)
"""

import logging
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse

router = APIRouter()
log = logging.getLogger("sentinel.slack_events")


@router.post("/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    """
    Receives all Slack events.
    Handles URL verification instantly; processes messages in the background.
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "invalid json"})

    event_type = body.get("type", "")

    # ── 1. URL verification — Slack sends this once when you set up the endpoint ──
    if event_type == "url_verification":
        challenge = body.get("challenge", "")
        log.info("Slack URL verification challenge received and answered")
        return {"challenge": challenge}

    # ── 2. Event callback ──────────────────────────────────────────────────────────
    if event_type == "event_callback":
        event = body.get("event", {})
        msg_type = event.get("type", "")

        is_user_message = (
            msg_type == "message"
            and not event.get("bot_id")        # ignore bot messages (including ours)
            and not event.get("subtype")        # ignore edits, joins, leaves
            and event.get("text", "").strip()   # must have text
        )

        if is_user_message:
            from ..services.slack_interceptor import process_message_event
            background_tasks.add_task(process_message_event, event)
            log.info(f"Queued message from {event.get('user')} for interception check")

    # Always return 200 immediately — Slack will retry if we take > 3s
    return {"ok": True}


@router.get("/events")
async def slack_events_verify(request: Request):
    """Health check — confirms the Slack endpoint is reachable."""
    return {"status": "ok", "endpoint": "SENTINEL Slack Events", "ready": True}
