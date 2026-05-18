"""
SENTINEL Autonomous Monitoring Loop

This is what makes SENTINEL an agent, not just a dashboard.

Every 30 minutes, without any user action:
  1. Calls Fivetran MCP list_connections() + trigger_sync()
  2. Queries BigQuery for fresh metrics
  3. Runs warning pattern engine
  4. If new warnings detected: saves to MongoDB, writes to output files
  5. Logs the full reasoning trace

The scheduler starts on app startup (registered in main.py).
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger("sentinel.monitor")

# APScheduler — gracefully optional so app still starts without it
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    _APScheduler = AsyncIOScheduler
    _APSCHEDULER_AVAILABLE = True
except ImportError:
    _APScheduler = None
    _APSCHEDULER_AVAILABLE = False

_scheduler: Optional[object] = None

# Track last cycle result for the API endpoint
_last_cycle: dict = {
    "ran_at": None,
    "connectors_checked": 0,
    "warnings_detected": 0,
    "warnings_new": 0,
    "snapshot": {},
    "status": "never_run",
    "error": None,
}


async def run_monitoring_cycle():
    """
    Full autonomous agent cycle.
    Calls Fivetran MCP → BigQuery → Gemini warning engine.
    No user interaction required.
    """
    global _last_cycle
    started = datetime.now(timezone.utc)
    log.info("SENTINEL monitor cycle starting...")

    try:
        from .mcp_client import call_mcp_tool, list_connectors, trigger_sync
        from .context_builder import build_metrics_snapshot
        from .warning_engine import check_warnings
        from ..db import mongodb
        from .output_writer import write_warning, _log_session

        # ── Step 1: Fivetran MCP — list all connected sources ──────────────
        log.info("MCP: list_connections()")
        connectors = await list_connectors()
        _log_session("MONITOR [1/4]", f"MCP list_connections → {len(connectors)} connectors")

        # ── Step 2: Fivetran MCP — trigger sync on active connectors ───────
        synced = 0
        for conn in connectors[:2]:  # limit to 2 to avoid rate limits
            cid = conn.get("id", "")
            if cid and not cid.startswith("mock_") and cid != "":
                log.info(f"MCP: trigger_sync({cid})")
                await trigger_sync(cid)
                synced += 1
                await asyncio.sleep(0.5)

        _log_session("MONITOR [2/4]", f"MCP trigger_sync → {synced} syncs triggered")

        # ── Step 3: BigQuery — pull fresh metrics ───────────────────────────
        log.info("BigQuery: building metrics snapshot...")
        snapshot = await build_metrics_snapshot()
        metric_count = len([v for v in snapshot.values() if v is not None and not str(v).startswith("_")])
        _log_session("MONITOR [3/4]", f"BigQuery snapshot → {metric_count} metrics captured")

        # ── Step 4: Gemini warning engine — check patterns ──────────────────
        log.info("Gemini: checking warning patterns...")
        warnings = await check_warnings(snapshot)

        # Only save genuinely new warnings (not demo ones, not duplicates)
        new_count = 0
        for w in warnings:
            if w.get("demo_scenario"):
                continue  # skip demo warnings
            try:
                wid = await mongodb.insert_warning(w)
                write_warning(w)
                new_count += 1
                log.warning(f"NEW WARNING: {w.get('message', '')[:100]}")
            except Exception as e:
                log.error(f"Failed to save warning: {e}")

        _log_session(
            "MONITOR [4/4] COMPLETE",
            f"Pattern check → {len(warnings)} matches | {new_count} new warnings saved\n\n"
            f"Metrics: MRR={snapshot.get('mrr')}, NPS={snapshot.get('nps')}, "
            f"Churn={snapshot.get('churn_rate')}\n"
            f"Flags: {snapshot.get('_flags', [])}"
        )

        _last_cycle = {
            "ran_at": started.isoformat(),
            "connectors_checked": len(connectors),
            "syncs_triggered": synced,
            "warnings_detected": len(warnings),
            "warnings_new": new_count,
            "snapshot_metrics": metric_count,
            "status": "ok",
            "error": None,
            "duration_s": (datetime.now(timezone.utc) - started).total_seconds(),
        }
        log.info(f"Monitor cycle complete in {_last_cycle['duration_s']:.1f}s")

    except Exception as e:
        log.error(f"Monitor cycle failed: {e}", exc_info=True)
        _last_cycle = {
            "ran_at": started.isoformat(),
            "status": "error",
            "error": str(e),
        }


def get_last_cycle_status() -> dict:
    return _last_cycle


def start_scheduler(interval_minutes: int = 30):
    """Start the APScheduler background loop."""
    global _scheduler

    if not _APSCHEDULER_AVAILABLE:
        log.warning("APScheduler not installed — autonomous monitoring disabled. Install apscheduler>=3.10.4")
        return None

    if _scheduler is not None:
        return _scheduler

    _scheduler = _APScheduler(
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 60}
    )
    _scheduler.add_job(
        run_monitoring_cycle,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="sentinel_monitor",
        name="SENTINEL Autonomous Monitor",
        replace_existing=True,
    )
    _scheduler.start()
    log.info(f"SENTINEL monitor started — running every {interval_minutes} minutes")
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("SENTINEL monitor stopped")
