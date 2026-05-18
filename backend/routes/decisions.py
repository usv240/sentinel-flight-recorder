from fastapi import APIRouter, HTTPException
from datetime import datetime
from ..db.schemas import DecisionLogRequest
from ..db import mongodb
from ..services.context_builder import build_metrics_snapshot
from ..services.output_writer import write_decision

router = APIRouter()


@router.post("/log")
async def log_decision(req: DecisionLogRequest, demo_scenario: str = ""):
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
    decision_id = f"DEC-LOCAL-{__import__('uuid').uuid4().hex[:8].upper()}"
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
