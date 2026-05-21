from fastapi import APIRouter
from ..db import mongodb
from ..services.context_builder import build_metrics_snapshot
from ..services.warning_engine import check_warnings
from ..services.output_writer import write_warning

router = APIRouter()


@router.get("/actions")
async def get_autonomous_actions():
    """Return recent autonomous actions taken by SENTINEL."""
    actions = await mongodb.get_recent_actions(limit=10)
    for a in actions:
        a.pop("_id", None)
    return {"actions": actions, "count": len(actions)}


@router.get("/active")
async def get_active_warnings(demo_scenario: str = ""):
    if demo_scenario:
        from ..services.warning_engine import _demo_warnings
        warnings = _demo_warnings(demo_scenario)
        for w in warnings:
            write_warning(w)
        from ..services.output_writer import _log_session
        _log_session(f"WARNINGS [{demo_scenario.upper()}]",
            f"{len(warnings)} warning(s) loaded. "
            f"Severities: {', '.join(w['severity'] for w in warnings)}")
        return {"warnings": warnings}

    snapshot = await build_metrics_snapshot()
    triggered = await check_warnings(snapshot)

    results = []
    for w in triggered:
        warning_id = await mongodb.insert_warning({
            "severity": w["severity"],
            "trigger_metric": w["trigger_metric"],
            "trigger_value": w["trigger_value"],
            "causal_confidence": w["historical_churn_rate"],
            "message": w["description"],
            "recommended_action": "Review decision log and contact Customer Success",
            "acknowledged": False,
        })
        w["warning_id"] = warning_id
        write_warning(w)
        results.append(w)

    from ..services.output_writer import _log_session
    _log_session("WARNING CHECK", f"Checked patterns. {len(results)} warning(s) triggered.")

    return {"warnings": results}


@router.post("/{warning_id}/acknowledge")
async def acknowledge(warning_id: str):
    success = await mongodb.acknowledge_warning(warning_id)
    return {"acknowledged": success, "warning_id": warning_id}
