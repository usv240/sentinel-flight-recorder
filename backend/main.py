import os
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from .routes import decisions, warnings, trace, connectors, demo, ask, transcript, toolcalls, mcp_http, agent_chat
from .services.monitor import start_scheduler, stop_scheduler, get_last_cycle_status, run_monitoring_cycle

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("sentinel")

# ── Rate limiting ─────────────────────────────────────────────────────────────
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    _limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
    _RATE_LIMIT = True
except ImportError:
    _limiter = None
    _RATE_LIMIT = False

# ── CORS — only allow the actual deployment origins ───────────────────────────
_ALLOWED_ORIGINS = [
    "https://sentinel-38381883054.us-central1.run.app",
    "https://console.cloud.google.com",
    "https://agent-platform.cloud.google.com",
    "http://localhost:8100",
    "http://localhost:8080",
    "http://127.0.0.1:8100",
]
# Allow all in development (APP_ENV=development)
if os.getenv("APP_ENV") == "development":
    _ALLOWED_ORIGINS.append("*")


async def _safe_startup_cycle():
    """Run the first monitoring cycle on startup — errors are logged, not raised."""
    try:
        await run_monitoring_cycle()
    except Exception as e:
        log.error(f"Startup monitoring cycle failed (non-fatal): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler(interval_minutes=30)
    asyncio.create_task(_safe_startup_cycle())
    yield
    stop_scheduler()


app = FastAPI(
    # expose Swagger only in dev
    openapi_url="/api/openapi.json" if os.getenv("APP_ENV") == "development" else None,
    title="SENTINEL — The Business Flight Recorder",
    description="The first flight recorder for human business decisions. Powered by Gemini 3, Fivetran MCP, and Google Cloud Agent Builder.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
)

if _RATE_LIMIT:
    app.state.limiter = _limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Global exception handler — never expose stack traces to clients ───────────
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    log.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


app.include_router(decisions.router,   prefix="/api/decisions",   tags=["decisions"])
app.include_router(warnings.router,    prefix="/api/warnings",    tags=["warnings"])
app.include_router(trace.router,       prefix="/api/trace",       tags=["trace"])
app.include_router(connectors.router,  prefix="/api/connectors",  tags=["connectors"])
app.include_router(demo.router,        prefix="/api/demo",        tags=["demo"])
app.include_router(ask.router,         prefix="/api/ask",         tags=["ask"])
app.include_router(transcript.router,  prefix="/api/transcript",  tags=["transcript"])
app.include_router(toolcalls.router,   prefix="/api/tool-calls",  tags=["tool-calls"])
app.include_router(mcp_http.router,    prefix="/api/mcp",         tags=["mcp"])
app.include_router(agent_chat.router,  prefix="/api/agent",       tags=["agent"])


@app.get("/api/health")
async def health():
    from .services.mcp_client import get_recent_tool_calls
    from .db.mongodb import get_db
    cycle = get_last_cycle_status()

    # Check MongoDB connectivity
    mongo_ok = False
    try:
        await get_db().command("ping", serverSelectionTimeoutMS=2000)
        mongo_ok = True
    except Exception:
        pass

    return {
        "status": "ok",
        "service": "SENTINEL",
        "version": "2.0.0",
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"),
        "demo_mode": os.getenv("DEMO_MODE", "true").lower() == "true",
        "mongodb": "connected" if mongo_ok else "unreachable",
        "monitor": {
            "last_run": cycle.get("ran_at"),
            "status": cycle.get("status", "pending"),
            "warnings_detected": cycle.get("warnings_detected", 0),
            "syncs_triggered": cycle.get("syncs_triggered", 0),
        },
        "mcp_calls_logged": len(get_recent_tool_calls()),
    }


@app.get("/api/monitor/status")
async def monitor_status():
    return get_last_cycle_status()


@app.post("/api/monitor/run")
async def trigger_monitor():
    asyncio.create_task(_safe_startup_cycle())
    return {"triggered": True, "message": "Monitoring cycle started. Check /api/monitor/status for results."}


# ── Frontend SPA — catch-all must come last ───────────────────────────────────
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
