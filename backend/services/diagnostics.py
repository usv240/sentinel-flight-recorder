"""
SENTINEL integration diagnostics.

A single, honest source of truth for "what is actually live right now".
Every integration reports one of:
  - "live"        : configured AND a real call/connection succeeded
  - "configured"  : credentials present but not (yet) verified this request
  - "demo"        : no credentials — SENTINEL returns clearly-labelled demo data
  - "unavailable" : the SDK/library isn't installed
  - "error"       : configured but a real call failed (detail explains why)

Surfaced at GET /api/health/integrations. This is what lets you see at a
glance whether SENTINEL is actually live or running on demo data — and
exactly what to fix to go fully live. Nothing here ever raises; each probe
is wrapped and time-boxed.
"""

import os
from typing import Dict, Any


def _bool_env(*names: str) -> bool:
    return any(bool(os.getenv(n)) for n in names)


# ── Gemini ────────────────────────────────────────────────────────────────────

def _gemini_status() -> Dict[str, Any]:
    try:
        from .gemini_client import (
            _GENAI_AVAILABLE, get_configured_model, get_active_model,
            gemini3_quota_exhausted, get_gemini3_models, get_vertex_fallback_models,
        )
    except Exception as e:
        return {"status": "unavailable", "detail": f"gemini_client import failed: {e}"}

    if not _GENAI_AVAILABLE:
        return {"status": "unavailable", "detail": "google-genai SDK not installed"}

    api_key = bool(os.getenv("GEMINI_API_KEY"))
    project = bool(os.getenv("GOOGLE_PROJECT_ID"))
    active = os.getenv("GEMINI_MODEL_ACTIVE")  # set only after a real call

    if active:
        status = "live"
        detail = f"last successful call used {active}"
    elif api_key or project:
        status = "configured"
        detail = "credentials present; no call made yet this process"
    else:
        status = "demo"
        detail = "no GEMINI_API_KEY or GOOGLE_PROJECT_ID — generation unavailable"

    return {
        "status": status,
        "detail": detail,
        "configured_model": get_configured_model(),
        "active_model": get_active_model(),
        "gemini3_models": get_gemini3_models(),
        "vertex_fallback_models": get_vertex_fallback_models(),
        "gemini3_quota_exhausted": gemini3_quota_exhausted(),
        "api_key_present": api_key,
        "vertex_project_present": project,
    }


# ── Fivetran ────────────────────────────────────────────────────────────────

async def _fivetran_status() -> Dict[str, Any]:
    try:
        from .mcp_client import (
            fivetran_mode, fivetran_has_creds, _try_import_mcp, _mcp_server_path,
            get_recent_tool_calls, list_connectors,
        )
    except Exception as e:
        return {"status": "unavailable", "detail": f"mcp_client import failed: {e}"}

    mode = fivetran_mode()
    mcp_importable = _try_import_mcp()
    server_path = _mcp_server_path()

    base = {
        "mode": mode,
        "creds_present": fivetran_has_creds(),
        "group_id_present": bool(os.getenv("FIVETRAN_GROUP_ID")),
        "mcp_sdk_importable": mcp_importable,
        "mcp_server_path": str(server_path) if server_path else None,
        "webhook_secret_present": bool(os.getenv("FIVETRAN_WEBHOOK_SECRET")),
    }

    if mode == "demo":
        base.update(status="demo",
                    detail="no FIVETRAN_API_KEY/SECRET — returning labelled demo connectors")
        return base

    # Creds are present — but that's NOT proof the API works (expired trial / tier
    # without API access returns 402 and we fall back to mock). Make a real probe
    # call and detect whether we actually got live data or a mock fallback.
    try:
        conns = await list_connectors()
    except Exception as e:
        base.update(status="error", detail=f"Fivetran probe call failed: {str(e)[:140]}")
        return base

    is_mock = (not conns) or all(
        str(c.get("id", "")).startswith("mock_") for c in conns if isinstance(c, dict)
    )
    real_count = sum(
        1 for c in conns if isinstance(c, dict) and not str(c.get("id", "")).startswith("mock_")
    )

    if is_mock:
        base.update(
            status="error",
            detail=("creds present but Fivetran API returned no live connectors "
                    "(expired trial or tier without API access → 402). Serving demo "
                    "connectors. Restore a plan with REST/MCP API access to go live."),
            live_connectors=0,
        )
        return base

    base.update(
        status="live",
        detail=f"{mode.upper()} transport returned {real_count} live connector(s)",
        live_connectors=real_count,
    )
    return base


# ── BigQuery ──────────────────────────────────────────────────────────────────

def _bigquery_status() -> Dict[str, Any]:
    try:
        from google.cloud import bigquery  # noqa: F401
        bq_available = True
    except Exception:
        bq_available = False

    project = os.getenv("GOOGLE_PROJECT_ID", "")
    table = os.getenv("SENTINEL_BQ_ACMESAAS_TABLE", "google_sheets.acmesaas_metrics")

    if not bq_available:
        return {"status": "unavailable", "detail": "google-cloud-bigquery not installed",
                "project": project or None, "primary_table": table}
    if not project:
        return {"status": "demo", "detail": "no GOOGLE_PROJECT_ID — metrics come from demo snapshots",
                "primary_table": table}

    # Probe the primary Fivetran-synced table with a tiny, time-boxed query.
    detail = "project configured; primary table not probed"
    status = "configured"
    row_count = None
    try:
        client = bigquery.Client(project=project)
        fq = table if "." in table and table.count(".") >= 1 else f"{project}.{table}"
        if fq.count(".") == 1:  # dataset.table → prepend project
            fq = f"{project}.{fq}"
        job = client.query(f"SELECT COUNT(*) AS n FROM `{fq}`")
        rows = list(job.result(timeout=8))
        row_count = int(rows[0]["n"]) if rows else 0
        status = "live" if row_count and row_count > 0 else "configured"
        detail = (f"queried {fq}: {row_count} rows"
                  if row_count else f"{fq} reachable but empty — populate via a Fivetran sync")
    except Exception as e:
        status = "error"
        detail = f"query failed: {str(e)[:160]}"

    return {"status": status, "detail": detail, "project": project,
            "primary_table": table, "row_count": row_count}


# ── MongoDB ───────────────────────────────────────────────────────────────────

async def _mongodb_status() -> Dict[str, Any]:
    uri = os.getenv("MONGODB_URI", "")
    if not uri:
        return {"status": "demo", "detail": "no MONGODB_URI — decisions kept in-memory only"}
    try:
        from ..db.mongodb import get_db
        await get_db().command("ping", serverSelectionTimeoutMS=2500)
        return {"status": "live", "detail": "ping ok",
                "database": os.getenv("MONGODB_DATABASE", "sentinel_db")}
    except Exception as e:
        return {"status": "error", "detail": f"ping failed: {str(e)[:160]}"}


# ── ADK + Slack ───────────────────────────────────────────────────────────────

def _adk_status() -> Dict[str, Any]:
    try:
        import google.adk  # noqa: F401
        adk = True
    except Exception:
        adk = False
    if not adk:
        return {"status": "unavailable", "detail": "google-adk not installed — /api/agent/chat uses direct Gemini fallback"}
    return {"status": "live", "detail": "google-adk available — multi-step agent active"}


def _slack_status() -> Dict[str, Any]:
    if _bool_env("SLACK_BOT_TOKEN"):
        return {"status": "configured", "detail": "bot token present — Decision Council + alerts enabled",
                "channel_present": bool(os.getenv("SLACK_CHANNEL_ID"))}
    return {"status": "demo", "detail": "no SLACK_BOT_TOKEN — Slack features disabled (optional)"}


# ── Aggregate ─────────────────────────────────────────────────────────────────

async def gather_integration_status() -> Dict[str, Any]:
    """Probe every integration and return a single honest status document."""
    integrations = {
        "gemini": _gemini_status(),
        "fivetran": await _fivetran_status(),
        "bigquery": _bigquery_status(),
        "mongodb": await _mongodb_status(),
        "adk": _adk_status(),
        "slack": _slack_status(),
    }

    # Overall posture: how "live" is this deployment right now?
    live = sum(1 for v in integrations.values() if v.get("status") == "live")
    demo = sum(1 for v in integrations.values() if v.get("status") == "demo")
    errors = [k for k, v in integrations.items() if v.get("status") == "error"]

    # The two integrations that define the Fivetran-track story.
    ft = integrations["fivetran"]["status"]
    bq = integrations["bigquery"]["status"]
    if ft == "live" and bq == "live":
        posture = "fully_live"
    elif ft in ("live",) or bq in ("live", "configured"):
        posture = "partially_live"
    else:
        posture = "demo"

    return {
        "posture": posture,
        "live_count": live,
        "demo_count": demo,
        "errors": errors,
        "integrations": integrations,
        "note": (
            "posture=demo means no live credentials are wired — SENTINEL returns "
            "clearly-labelled demo data and never presents it as live. Wire "
            "FIVETRAN_API_KEY/SECRET + GOOGLE_PROJECT_ID + a Fivetran→BigQuery "
            "sync to reach fully_live."
        ),
    }
