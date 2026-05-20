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
from typing import Optional

router = APIRouter()


class AgentChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    demo_scenario: Optional[str] = None


class AgentChatResponse(BaseModel):
    response: str
    session_id: str
    agent: str = "SENTINEL-ADK"
    model: str = "gemini-3-flash-preview"


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(req: AgentChatRequest):
    """Run the SENTINEL ADK agent with a user message."""
    # Validate demo_scenario if provided
    if req.demo_scenario and req.demo_scenario not in ("acmesaas", "qwikster"):
        raise HTTPException(status_code=400, detail="demo_scenario must be 'acmesaas' or 'qwikster'")

    session_id = req.session_id or str(uuid.uuid4())

    # Enrich message with demo context if provided
    message = req.message
    if req.demo_scenario:
        message = f"[demo_scenario={req.demo_scenario}] {message}"

    try:
        from agent.sentinel_agent import run_agent
        response_text = await run_agent(message, session_id=session_id)
    except ImportError:
        # ADK not installed — fall back to direct Gemini call
        response_text = await _fallback_gemini(message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    return AgentChatResponse(
        response=response_text,
        session_id=session_id,
    )


async def _fallback_gemini(message: str) -> str:
    """Direct Gemini call if ADK is not available."""
    try:
        from ..services.gemini_client import generate
        return await generate(message)
    except Exception as e:
        return f"ADK unavailable and fallback failed: {e}"
