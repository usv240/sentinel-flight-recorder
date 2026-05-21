from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..db.schemas import DecisionLogRequest
from ..db import mongodb
from ..services.context_builder import build_metrics_snapshot
from ..services.output_writer import write_decision

router = APIRouter()

_VALID_SCENARIOS = {"acmesaas", "qwikster", ""}


def _validate_scenario(s: str):
    if s and s not in _VALID_SCENARIOS:
        raise HTTPException(400, f"Invalid demo_scenario '{s}'. Must be: acmesaas, qwikster")


class PrecheckRequest(BaseModel):
    decision_text: str
    decision_type: str = "strategy"
    demo_scenario: Optional[str] = None


@router.post("/precheck")
async def precheck_decision(req: PrecheckRequest):
    """
    Pre-decision risk analysis. Call this BEFORE logging a decision.
    Returns risk score, blocking conditions, historical patterns, and alternatives.
    This is SENTINEL's preventive mode — not just recording, but preventing.
    """
    if req.decision_type not in ("pricing", "hiring", "product", "strategy", "operational"):
        raise HTTPException(400, "decision_type must be: pricing, hiring, product, strategy, operational")

    from ..services.precheck_engine import run_precheck
    snapshot = await build_metrics_snapshot(req.demo_scenario or None)
    result = await run_precheck(req.decision_text, req.decision_type, snapshot)
    return result


@router.get("/snapshot")
async def get_current_snapshot(demo_scenario: str = ""):
    """Return current Fivetran metrics snapshot — called by the Log Decision modal."""
    _validate_scenario(demo_scenario)
    snapshot = await build_metrics_snapshot(demo_scenario or None)
    clean = {k: v for k, v in snapshot.items() if not k.startswith("_") and k not in ("raw",)}
    return {"snapshot": clean, "flags": snapshot.get("_flags", []), "sources": snapshot.get("sources", {})}


@router.post("/log")
async def log_decision(req: DecisionLogRequest, demo_scenario: str = ""):
    _validate_scenario(demo_scenario)
    snapshot = await build_metrics_snapshot(demo_scenario or None)

    doc = {
        "decision_text": req.decision_text,
        "decision_type": req.decision_type.value,
        "rationale": req.rationale,
        "alternatives_considered": req.alternatives_considered,
        "participants": req.participants,
        "auto_detected": False,
        "metrics_snapshot": snapshot,
        "outcome": None,
        "warning_fired": False,
    }

    # Try MongoDB — gracefully degrade if unavailable
    import uuid as _uuid_mod
    decision_id = f"DEC-LOCAL-{_uuid_mod.uuid4().hex[:8].upper()}"
    try:
        decision_id = await mongodb.insert_decision(doc)
        doc["decision_id"] = decision_id
        output_file = write_decision(doc, snapshot)
        await mongodb.get_db().decisions.update_one(
            {"decision_id": decision_id},
            {"$set": {"output_file": output_file}},
        )
    except Exception:
        doc["decision_id"] = decision_id
        output_file = write_decision(doc, snapshot)

    # If a precheck_risk was passed and is high, notify Slack
    # (frontend sets X-Sentinel-Risk header when user proceeds despite warning)
    precheck_risk = getattr(req, "precheck_risk_level", None)
    precheck_score = getattr(req, "precheck_risk_score", None)
    if precheck_risk == "high" and precheck_score:
        try:
            from ..services.slack_client import send_precheck_alert
            import asyncio
            asyncio.create_task(send_precheck_alert(
                decision_text=req.decision_text,
                risk_level=precheck_risk,
                risk_score=float(precheck_score),
                blocking_conditions=[],
                alternatives=[],
                snapshot=snapshot,
            ))
        except Exception:
            pass

    return {
        "decision_id": decision_id,
        "message": "Decision recorded with full metrics context",
        "metrics_captured": [k for k in snapshot if k not in ("captured_at", "sources", "_flags", "raw")],
        "flags": snapshot.get("_flags", []),
        "output_file": output_file,
    }


@router.get("/list")
async def list_decisions(limit: int = 20, decision_type: str = "", demo_scenario: str = ""):
    if demo_scenario:
        from ..services.causal_tracer import _build_demo_trace
        trace = _build_demo_trace(demo_scenario)
        return {"decisions": _demo_decision_list(demo_scenario), "total": 3}

    decisions = await mongodb.get_decisions(
        decision_type=decision_type or None, limit=limit
    )
    for d in decisions:
        d.pop("_id", None)
    return {"decisions": decisions, "total": len(decisions)}


@router.get("/{decision_id}")
async def get_decision(decision_id: str):
    doc = await mongodb.get_decision_by_id(decision_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Decision not found")
    doc.pop("_id", None)
    return doc


def _demo_decision_list(scenario: str):
    if scenario == "acmesaas":
        return [
            {
                "decision_id": "DEC-20260603-PRICE",
                "decision_text": "Increase all pricing tiers by 20%",
                "decision_type": "pricing",
                "logged_at": "2026-06-03T09:15:00",
                "outcome": "churn_spike",
                "warning_fired": True,
                "days_of_warning": 34,
                "causal_correlation": 0.87,
            },
            {
                "decision_id": "DEC-20260515-HIRE",
                "decision_text": "Hire 3 senior engineers to accelerate product roadmap",
                "decision_type": "hiring",
                "logged_at": "2026-05-15T14:00:00",
                "outcome": "positive",
                "warning_fired": False,
            },
            {
                "decision_id": "DEC-20260428-PIVOT",
                "decision_text": "Pivot focus to enterprise segment, pause SMB outbound",
                "decision_type": "strategy",
                "logged_at": "2026-04-28T10:30:00",
                "outcome": "monitoring",
                "warning_fired": False,
            },
        ]
    if scenario == "qwikster":
        return [
            {
                "decision_id": "DEC-20110712-QWIK",
                "decision_text": "Announce 60% price increase + Qwikster DVD spinoff",
                "decision_type": "pricing",
                "logged_at": "2011-07-12T00:00:00",
                "outcome": "catastrophic",
                "warning_fired": True,
                "days_of_warning": 0,
                "causal_correlation": 0.91,
            },
        ]
    return []
