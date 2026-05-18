import asyncio
from fastapi import APIRouter
from ..services.causal_tracer import _build_demo_trace
from ..services.warning_engine import _build_demo_warnings
from ..services.context_builder import build_metrics_snapshot, _demo_snapshot
from ..services.mcp_client import call_mcp_tool
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

    # Run all three expensive async operations in parallel:
    # MCP tool call + Gemini causal trace + Gemini warnings
    snapshot_key = "acmesaas_baseline" if scenario == "acmesaas" else "qwikster_baseline"

    trace, warnings, live_snapshot = await asyncio.gather(
        _build_demo_trace(scenario),
        _build_demo_warnings(scenario),
        _try_live_snapshot(scenario),
    )

    # Merge live BigQuery data into the baseline snapshot when available
    baseline = _demo_snapshot(snapshot_key)
    snapshot = _merge_snapshot(baseline, live_snapshot)

    # Backfill causal_confidence from computed Pearson r
    pearson_r = trace.get("pearson_r", 0.87)
    for w in warnings:
        if w.get("causal_confidence") is None or w.get("causal_confidence") == 0.87:
            w["causal_confidence"] = pearson_r

    data = {
        "meta": meta,
        "decisions": _demo_decision_list(scenario),
        "warnings": warnings,
        "trace": trace,
        "snapshot": snapshot,
        "data_source": snapshot.get("_data_source", "demo"),
    }

    from ..services.output_writer import write_demo_load
    write_demo_load(scenario, data)

    return data


async def _try_live_snapshot(scenario: str) -> dict:
    """Query BigQuery for live Fivetran data. Returns {} on failure."""
    if scenario != "acmesaas":
        return {}
    try:
        # First: call Fivetran MCP to trigger a sync (logs the tool call)
        await call_mcp_tool("list_connections", {})
        # Then try to get live metrics
        snapshot = await build_metrics_snapshot(demo_scenario=None)
        if snapshot.get("mrr"):
            snapshot["_data_source"] = "bigquery_live"
            return snapshot
    except Exception:
        pass
    return {}


def _merge_snapshot(baseline: dict, live: dict) -> dict:
    """Merge live BigQuery data into the baseline, prefer live values."""
    if not live or not live.get("mrr"):
        baseline["_data_source"] = "demo_baseline"
        return baseline
    merged = {**baseline}
    live_keys = {"mrr", "arr", "churn_rate", "nps", "active_customers",
                 "cac", "ltv", "support_tickets_7d", "runway_months"}
    for k in live_keys:
        if live.get(k) is not None:
            merged[k] = live[k]
    merged["_data_source"] = "bigquery_live"
    merged["captured_at"] = live.get("captured_at", baseline.get("captured_at"))
    if live.get("_flags"):
        merged["_flags"] = live["_flags"]
    return merged
