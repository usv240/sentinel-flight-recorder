"""
SSE endpoint — streams real Fivetran MCP tool calls to the frontend.
Frontend polls /api/tool-calls/stream?since=N and receives new calls as JSON.
"""
import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from ..services.mcp_client import get_recent_tool_calls

router = APIRouter()


@router.get("/stream")
async def stream_tool_calls(since: int = 0):
    """Server-sent events: streams tool call log entries since a given ID."""

    async def event_generator():
        last_id = since
        for _ in range(60):  # stream for up to 60 seconds
            calls = get_recent_tool_calls(since_id=last_id)
            if calls:
                for call in calls:
                    yield f"data: {json.dumps(call)}\n\n"
                    last_id = call["id"] + 1
            await asyncio.sleep(0.5)
        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/recent")
async def recent_tool_calls(since: int = 0, limit: int = 20):
    """Polling endpoint — returns recent tool calls since a given ID."""
    calls = get_recent_tool_calls(since_id=since)
    return {"calls": calls[-limit:], "total": len(calls)}
