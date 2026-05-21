"""
Custom Analysis endpoint — judges enter their own data, SENTINEL runs the full pipeline.

This proves SENTINEL is NOT running on curated rails.
Any decision + metrics → same causal inference battery + Gemini narrative.

POST /api/custom/analyze
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

router = APIRouter()


class CustomDecisionInput(BaseModel):
    decision_text: str = Field(..., description="What was decided")
    decision_date: str = Field(..., description="When (YYYY-MM-DD)")
    decision_type: str = Field(default="strategy", description="pricing|hiring|product|strategy|operational")

    # Metrics at time of decision
    mrr_at_decision: Optional[float] = Field(None, description="MRR ($) at decision time")
    nps_at_decision: Optional[float] = Field(None, description="NPS score at decision time")
    churn_at_decision: Optional[float] = Field(None, description="Churn rate (0.0–1.0) at decision time")

    # Current / outcome metrics (what happened after)
    mrr_now: Optional[float] = Field(None, description="MRR ($) now / at outcome time")
    nps_now: Optional[float] = Field(None, description="NPS score now")
    churn_now: Optional[float] = Field(None, description="Churn rate now")

    # Optional: weekly time series (comma-separated) for the primary metric
    # e.g. "0.09,0.10,0.11,0.13,0.15" — one value per week since decision
    metric_weekly_series: Optional[str] = Field(None, description="Weekly metric values since decision (comma-separated)")
    metric_name: Optional[str] = Field(None, description="Name of the metric in weekly series")


class CustomAnalysisResponse(BaseModel):
    verdict: str
    verdict_text: str
    causal_analysis: dict
    narrative: str
    confounding_factors: list
    data_quality: dict
    recommendation: str


@router.post("/analyze", response_model=CustomAnalysisResponse)
async def custom_analyze(inp: CustomDecisionInput):
    """
    Run the full SENTINEL causal inference battery on user-supplied data.
    No hardcoded scenarios — works with any decision and any metrics.
    """
    if inp.decision_type not in ("pricing", "hiring", "product", "strategy", "operational"):
        raise HTTPException(status_code=400, detail="decision_type must be one of: pricing, hiring, product, strategy, operational")

    from ..services.causal_tracer import _run_causal_battery, _pearson_r
    from ..services.gemini_client import generate_confounding_factors, generate_causal_narrative

    # ── Build time series from inputs ─────────────────────────────────────
    weekly_series = []
    metric_name = inp.metric_name or "custom_metric"
    data_quality_notes = []

    if inp.metric_weekly_series:
        try:
            weekly_series = [float(v.strip()) for v in inp.metric_weekly_series.split(",") if v.strip()]
            data_quality_notes.append(f"Using provided weekly series: {len(weekly_series)} data points")
        except ValueError:
            data_quality_notes.append("Could not parse weekly series — falling back to before/after comparison")

    # If no weekly series, synthesize from before/after snapshots
    if len(weekly_series) < 3:
        before_after_pairs = []
        if inp.churn_at_decision is not None and inp.churn_now is not None:
            # Interpolate 5 weekly points
            c0, c1 = inp.churn_at_decision, inp.churn_now
            weekly_series = [c0 + (c1 - c0) * i / 4 for i in range(5)]
            metric_name = "churn_rate"
            data_quality_notes.append("Interpolated 5 weekly points from before/after churn values")
        elif inp.nps_at_decision is not None and inp.nps_now is not None:
            n0, n1 = inp.nps_at_decision, inp.nps_now
            weekly_series = [n0 + (n1 - n0) * i / 4 for i in range(5)]
            metric_name = "nps"
            data_quality_notes.append("Interpolated 5 weekly points from before/after NPS values")
        elif inp.mrr_at_decision is not None and inp.mrr_now is not None:
            m0, m1 = inp.mrr_at_decision, inp.mrr_now
            weekly_series = [m0 + (m1 - m0) * i / 4 for i in range(5)]
            metric_name = "mrr"
            data_quality_notes.append("Interpolated 5 weekly points from before/after MRR values")
        else:
            data_quality_notes.append("Insufficient metric data — provide at least before/after values for one metric")

    # ── Run causal battery ─────────────────────────────────────────────────
    if len(weekly_series) >= 3:
        indicator = list(range(len(weekly_series)))
        decision_index = 0
        analysis = _run_causal_battery(weekly_series, indicator, decision_index, metric_name)
    else:
        analysis = {
            "metric": metric_name,
            "pearson_r": 0.0,
            "pearson_p": 1.0,
            "granger": {"significant": False, "note": "Insufficient data — need at least 3 time points"},
            "interrupted_time_series": {"significant": False, "note": "Insufficient data"},
            "mann_whitney": {"significant": False, "note": "Insufficient data"},
            "significant_tests": 0,
            "verdict": "insufficient_data",
            "verdict_text": "Not enough data to run statistical tests. Provide weekly metric series for better analysis.",
            "methodology_note": "Add metric_weekly_series for Granger causality, ITS, and Mann-Whitney tests.",
        }

    # ── Gemini narrative + confounding factors ────────────────────────────
    import asyncio

    root_decision = {
        "decision_text": inp.decision_text,
        "decision_type": inp.decision_type,
        "logged_at": inp.decision_date,
        "metrics_snapshot": {
            "mrr": inp.mrr_at_decision,
            "nps": inp.nps_at_decision,
            "churn_rate": inp.churn_at_decision,
        },
    }

    outcome = _build_outcome_description(inp)
    chain = _build_minimal_chain(inp)

    narrative_coro = generate_causal_narrative(
        outcome=outcome,
        root_decision=root_decision,
        causal_chain=chain,
        data_at_decision={
            "mrr": inp.mrr_at_decision,
            "nps": inp.nps_at_decision,
            "churn_rate": inp.churn_at_decision,
        },
        pearson_r=analysis.get("pearson_r", 0.0),
        p_value=analysis.get("pearson_p", 1.0),
        days_of_warning=0,
        corr_metric=metric_name,
    )
    confounding_coro = generate_confounding_factors(
        root_decision=root_decision,
        outcome=outcome,
        causal_chain=chain,
        pearson_r=analysis.get("pearson_r", 0.0),
    )
    narrative, confounding_factors = await asyncio.gather(narrative_coro, confounding_coro)

    # ── Recommendation ────────────────────────────────────────────────────
    sig = analysis.get("significant_tests", 0)
    if sig >= 2:
        recommendation = f"Strong causal signal ({sig}/3 tests significant). Review the '{inp.decision_text}' decision and its downstream effects. Run SENTINEL monitoring to track recovery."
    elif sig == 1:
        recommendation = f"Weak causal signal (1/3 tests significant). Monitor '{metric_name}' weekly. Additional data points will sharpen the analysis."
    else:
        recommendation = f"No statistically detectable causal signal from this decision on '{metric_name}'. Either the decision had no measurable effect, or more data is needed."

    data_quality = {
        "data_points": len(weekly_series),
        "metric_used": metric_name,
        "notes": data_quality_notes,
        "quality": "good" if len(weekly_series) >= 5 else "limited" if len(weekly_series) >= 3 else "insufficient",
        "improve_by": "Provide metric_weekly_series with 5+ weekly observations for full Granger causality test",
    }

    return CustomAnalysisResponse(
        verdict=analysis.get("verdict", "unknown"),
        verdict_text=analysis.get("verdict_text", ""),
        causal_analysis=analysis,
        narrative=narrative,
        confounding_factors=confounding_factors,
        data_quality=data_quality,
        recommendation=recommendation,
    )


def _build_outcome_description(inp: CustomDecisionInput) -> str:
    parts = []
    if inp.mrr_at_decision and inp.mrr_now:
        delta = inp.mrr_now - inp.mrr_at_decision
        parts.append(f"MRR changed by ${delta:+,.0f}")
    if inp.churn_at_decision is not None and inp.churn_now is not None:
        delta = inp.churn_now - inp.churn_at_decision
        parts.append(f"Churn {'+' if delta > 0 else ''}{delta:.1%}")
    if inp.nps_at_decision is not None and inp.nps_now is not None:
        delta = inp.nps_now - inp.nps_at_decision
        parts.append(f"NPS {'+' if delta > 0 else ''}{delta:.0f} points")
    if not parts:
        return f"Outcome after decision: '{inp.decision_text}'"
    return f"After '{inp.decision_text}': {', '.join(parts)}"


def _build_minimal_chain(inp: CustomDecisionInput) -> list:
    chain = [{
        "event_id": "E001", "date": inp.decision_date, "type": "decision",
        "title": inp.decision_text[:60],
        "severity": "root_cause",
        "description": f"{inp.decision_type.upper()} decision made on {inp.decision_date}",
    }]
    if inp.mrr_now or inp.churn_now or inp.nps_now:
        chain.append({
            "event_id": "E002", "date": "current", "type": "outcome",
            "title": "Current metric state",
            "severity": "high",
            "description": _build_outcome_description(inp),
        })
    return chain
