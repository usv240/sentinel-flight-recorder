import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from .routes import decisions, warnings, trace, connectors, demo, ask, transcript, toolcalls

app = FastAPI(
    title="SENTINEL — The Business Flight Recorder",
    description="The first flight recorder for human business decisions.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(decisions.router, prefix="/api/decisions", tags=["decisions"])
app.include_router(warnings.router, prefix="/api/warnings", tags=["warnings"])
app.include_router(trace.router, prefix="/api/trace", tags=["trace"])
app.include_router(connectors.router, prefix="/api/connectors", tags=["connectors"])
app.include_router(demo.router, prefix="/api/demo", tags=["demo"])
app.include_router(ask.router, prefix="/api/ask", tags=["ask"])
app.include_router(transcript.router, prefix="/api/transcript", tags=["transcript"])
app.include_router(toolcalls.router, prefix="/api/tool-calls", tags=["tool-calls"])

# Health must be registered before the SPA catch-all
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "SENTINEL",
        "version": "1.0.0",
        "demo_mode": os.getenv("DEMO_MODE", "true").lower() == "true",
    }

# Serve frontend — catch-all must come last
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(frontend_path / "index.html"))

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="API route not found")
        file_path = frontend_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_path / "index.html"))
