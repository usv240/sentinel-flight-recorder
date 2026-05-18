from fastapi import APIRouter
from ..services.causal_tracer import _build_demo_trace
from ..services.warning_engine import _demo_warnings
from ..services.context_builder import _demo_snapshot
from ..routes.decisions import _demo_decision_list

router = APIRouter()

SCENARIOS = {
    "acmesaas": {
        "id": "acmesaas",
        "name": "AcmeSaaS — Pricing Disaster",
        "tagline": "A 20% price increase that cost $120,000 in ARR",
        "period": "June–July 2026",
        "outcome": "$120K ARR lost",
        "days_of_warning": 34,
        "company": "AcmeSaaS (fictional)",
        "industry": "B2B SaaS",
        "description": (
            "AcmeSaaS raised prices 20% to improve unit economics. "
            "Their NPS was 31 at decision time — 9 points below the warning threshold. "
            "Customer X showed 12 support tickets and a login gap of 2 days. "
            "34 days of warning were available. None were acted on."
        ),
    },
    "qwikster": {
        "id": "qwikster",
        "name": "Netflix Qwikster — The $3B Mistake",
        "tagline": "800,000 subscribers lost in one quarter",
        "period": "July–October 2011",
        "outcome": "Stock -77%, 800K subscribers lost, Qwikster cancelled in 23 days",
        "days_of_warning": 0,
        "company": "Netflix (public)",
        "industry": "Streaming / Entertainment",
        "description": (
            "Netflix announced a 60% price increase combined with a DVD/streaming split. "
            "Subscriber growth had already decelerated 45% QoQ. Internal surveys showed "
            "67% of subscribers called the increase 'unacceptable'. "
            "SENTINEL would have flagged this on July 13, the day after the announcement."
        ),
    },
}


@router.get("/scenarios")
async def list_scenarios():
    return {"scenarios": list(SCENARIOS.values())}


@router.get("/{scenario}/full")
async def get_full_scenario(scenario: str):
    if scenario not in SCENARIOS:
        return {"error": f"Unknown scenario: {scenario}"}

    meta = SCENARIOS[scenario]
    snapshot_key = "acmesaas_baseline" if scenario == "acmesaas" else "qwikster_baseline"

    data = {
        "meta": meta,
        "decisions": _demo_decision_list(scenario),
        "warnings": _demo_warnings(scenario),
        "trace": _build_demo_trace(scenario),
        "snapshot": _demo_snapshot(snapshot_key),
    }

    from ..services.output_writer import write_demo_load
    write_demo_load(scenario, data)

    return data
