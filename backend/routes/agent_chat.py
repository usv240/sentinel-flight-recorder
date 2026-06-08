"""
ADK agent chat endpoint.

POST /api/agent/chat — runs the SENTINEL ADK agent (Gemini 3 via google-adk)
and returns the final text response. Session ID is optional; defaults to "default".

The ADK agent (sentinel/agent/sentinel_agent.py) uses FunctionTools that call
the same backend services as the MCP HTTP endpoint — so both paths stay in sync.
"""

import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()


class AgentChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    demo_scenario: Optional[str] = None


class ToolCall(BaseModel):
    tool: str
    args: dict = {}
    ok: bool = True


class AgentChatResponse(BaseModel):
    response: str
    session_id: str
    agent: str = "SENTINEL-ADK"
    model: str = "gemini-3-flash-preview"
    model_fallback: bool = False  # True if Gemini 3 failed and Vertex 2.5 answered
    tool_trace: List[ToolCall] = []
    steps: int = 0


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(req: AgentChatRequest):
    """Run the SENTINEL ADK agent with a user message, returning its tool trace."""
    # Validate demo_scenario if provided
    if req.demo_scenario and req.demo_scenario not in ("acmesaas", "qwikster"):
        raise HTTPException(status_code=400, detail="demo_scenario must be 'acmesaas' or 'qwikster'")

    session_id = req.session_id or str(uuid.uuid4())

    # Enrich message with demo context if provided
    message = req.message
    if req.demo_scenario:
        message = f"[demo_scenario={req.demo_scenario}] {message}"

    tool_trace: list = []
    # Report the configured model up front; run_agent_traced overrides this with
    # the model that ACTUALLY answered (after any Gemini 3 → 2.5 fallback).
    import os
    model = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
    model_fallback = False
    try:
        # Ensure the API-key backend has a key available for Gemini 3.
        if not os.environ.get("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")
        from agent.sentinel_agent import run_agent_traced
        result = await run_agent_traced(message, session_id=session_id)
        response_text = result["response"]
        tool_trace = result.get("tool_trace", [])
        model = result.get("model", model)
        model_fallback = result.get("model_fallback", False)
    except ImportError:
        # ADK not installed — fall back to direct Gemini call
        response_text = await _fallback_gemini(message)
        model_fallback = True
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    return AgentChatResponse(
        response=response_text,
        session_id=session_id,
        model=model,
        model_fallback=model_fallback,
        tool_trace=[ToolCall(**t) for t in tool_trace],
        steps=len(tool_trace),
    )


async def _fallback_gemini(message: str) -> str:
    """Direct Gemini call if ADK is not available."""
    try:
        from ..services.gemini_client import generate
        return await generate(message)
    except Exception as e:
        return f"ADK unavailable and fallback failed: {e}"
