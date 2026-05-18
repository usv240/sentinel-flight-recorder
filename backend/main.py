import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from .routes import decisions, warnings, trace, connectors, demo, ask, transcript, toolcalls
from .services.monitor import start_scheduler, stop_scheduler, get_last_cycle_status, run_monitoring_cycle

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: launch autonomous monitoring loop
    start_scheduler(interval_minutes=30)
    # Run one immediate cycle so the app has fresh data on boot
    import asyncio
    asyncio.create_task(run_monitoring_cycle())
    yield
    # Shutdown: stop scheduler cleanly
    stop_scheduler()


app = FastAPI(
    title="SENTINEL — The Business Flight Recorder",
    description="The first flight recorder for human business decisions. Powered by Gemini 3 + Fivetran MCP.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(decisions.router,   prefix="/api/decisions",   tags=["decisions"])
app.include_router(warnings.router,    prefix="/api/warnings",    tags=["warnings"])
app.include_router(trace.router,       prefix="/api/trace",       tags=["trace"])
app.include_router(connectors.router,  prefix="/api/connectors",  tags=["connectors"])
app.include_router(demo.router,        prefix="/api/demo",        tags=["demo"])
app.include_router(ask.router,         prefix="/api/ask",         tags=["ask"])
app.include_router(transcript.router,  prefix="/api/transcript",  tags=["transcript"])
app.include_router(toolcalls.router,   prefix="/api/tool-calls",  tags=["tool-calls"])


@app.get("/api/health")
async def health():
    from .services.mcp_client import get_recent_tool_calls
    cycle = get_last_cycle_status()
    return {
        "status": "ok",
        "service": "SENTINEL",
        "version": "2.0.0",
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"),
        "demo_mode": os.getenv("DEMO_MODE", "true").lower() == "true",
        "monitor": {
            "last_run": cycle.get("ran_at"),
            "status": cycle.get("status", "pending"),
            "warnings_detected": cycle.get("warnings_detected", 0),
        },
        "mcp_calls_logged": len(get_recent_tool_calls()),
    }


@app.get("/api/monitor/status")
async def monitor_status():
    """Real-time autonomous agent loop status."""
    return get_last_cycle_status()


@app.post("/api/monitor/run")
async def trigger_monitor():
    """Manually trigger a monitoring cycle — useful for demos."""
    import asyncio
    asyncio.create_task(run_monitoring_cycle())
    return {"triggered": True, "message": "Monitoring cycle started. Check /api/monitor/status for results."}


# Frontend SPA — catch-all must come last
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(frontend_path / "index.html"))

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        file_path = frontend_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_path / "index.html"))
