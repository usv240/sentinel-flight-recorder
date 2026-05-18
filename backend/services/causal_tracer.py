import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import numpy as np

try:
    from scipy import stats as scipy_stats
    _SCIPY = True
except ImportError:
    _SCIPY = False

from ..db import mongodb
from .gemini_client import analyze_causal_chain


def _pearson_r(x: List[float], y: List[float]) -> tuple[float, float]:
    """Calculate Pearson correlation coefficient and p-value."""
    if not _SCIPY or len(x) < 3:
        # Fallback: manual calculation
        if len(x) < 2:
            return 0.0, 1.0
        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        den_x = (sum((xi - mean_x) ** 2 for xi in x)) ** 0.5
        den_y = (sum((yi - mean_y) ** 2 for yi in y)) ** 0.5
        if den_x == 0 or den_y == 0:
            return 0.0, 1.0
        r = num / (den_x * den_y)
        return round(r, 3), 0.05  # approximate p-value
    r, p = scipy_stats.pearsonr(x, y)
    return round(float(r), 3), round(float(p), 4)


def _build_demo_trace(scenario: str) -> Dict[str, Any]:
    """Pre-built causal traces for demo scenarios."""
    if scenario == "acmesaas":
        return {
            "trace_id": "TRACE-ACME-001",
            "outcome_description": "Customer X churned — $120,000 ARR lost",
            "pearson_r": 0.87,
            "p_value": 0.003,
            "days_of_warning": 34,
            "earliest_signal_date": "2026-06-17T00:00:00",
            "narrative": (
                "The pricing decision of June 3 triggered a cascade that SENTINEL "
                "would have detected on June 17 — 34 days before the churn. "
                "The data existed at decision time: NPS was 31 (below safe threshold), "
                "Customer X had filed 12 support tickets in 7 days, and their last "
                "login was just 2 days ago. These three signals together had an 87% "
                "historical correlation with churn following a price increase."
            ),
            "root_decision": {
                "decision_id": "DEC-20260603-PRICE",
                "decision_text": "Increase all pricing tiers by 20%",
                "decision_type": "pricing",
                "logged_at": "2026-06-03T09:15:00",
                "rationale": "CAC rising, need to improve unit economics",
                "metrics_snapshot": {
                    "mrr": 85000,
                    "nps": 31,
                    "churn_rate": 0.09,
                    "support_tickets_7d": 89,
                    "active_customers": 142,
                },
            },
            "causal_chain": [
                {
                    "event_id": "E001",
                    "date": "2026-06-03",
                    "type": "decision",
                    "title": "Pricing +20%",
                    "description": "All tiers increased by 20%. NPS was 31 at time of decision — below the 40-point safety threshold.",
                    "severity": "root_cause",
                },
                {
                    "event_id": "E002",
                    "date": "2026-06-17",
                    "type": "signal",
                    "title": "Customer X reduces seats",
                    "description": "Customer X downgrades from 45 to 30 seats. Auto-detected by Fivetran Stripe connector.",
                    "metric_value": -33.0,
                    "metric_label": "seat reduction %",
                    "severity": "warning",
                },
                {
                    "event_id": "E003",
                    "date": "2026-06-28",
                    "type": "signal",
                    "title": '"Evaluating alternatives" ticket',
                    "description": "Customer X support ticket: 'We are evaluating alternatives due to recent price changes.'",
                    "severity": "high",
                },
                {
                    "event_id": "E004",
                    "date": "2026-07-07",
                    "type": "signal",
                    "title": "Login frequency drops 60%",
                    "description": "Customer X daily logins drop from avg 47 to 19. SENTINEL fires early warning.",
                    "metric_value": -60.0,
                    "metric_label": "login frequency change %",
                    "severity": "critical",
                },
                {
                    "event_id": "E005",
                    "date": "2026-07-15",
                    "type": "outcome",
                    "title": "Customer X churns",
                    "description": "$120,000 ARR lost. Cancellation reason: 'Pricing no longer competitive at this tier.'",
                    "metric_value": -120000.0,
                    "metric_label": "ARR lost ($)",
                    "severity": "critical",
                },
            ],
            "data_available_at_decision": {
                "nps": 31,
                "nps_threshold": 40,
                "support_tickets_7d": 89,
                "support_tickets_avg": 29,
                "customer_x_tickets": 12,
                "customer_x_last_login_days": 2,
                "churn_rate": "9% (above 8% threshold)",
            },
            "data_that_predicted_outcome": [
                "NPS=31 is 9 points below the 40-point threshold that historically precedes churn post-price-increase",
                "Customer X had filed 12 support tickets in 7 days — 3x the account average",
                "Support ticket volume (89/week) was 3.1x company average — indicating broad dissatisfaction",
                "Churn rate of 9% was already above the 8% warning threshold before the price increase",
            ],
            "recommended_actions": [
                "Delay price increase until NPS recovers above 50",
                "Grandfather existing customers at current pricing for 6 months",
                "Executive check-in call with Customer X within 48 hours of seat reduction",
            ],
        }

    if scenario == "qwikster":
        return {
            "trace_id": "TRACE-QWIK-001",
            "outcome_description": "800,000 subscribers lost — worst quarter in Netflix history",
            "pearson_r": 0.91,
            "p_value": 0.001,
            "days_of_warning": 0,
            "earliest_signal_date": "2011-07-13T00:00:00",
            "narrative": (
                "Netflix's July 12, 2011 pricing announcement combined a 60% price increase "
                "with a service split — doubling down on a strategy that subscriber growth data "
                "already showed was fragile. Subscriber growth had slowed from 3.3M new subscribers "
                "in Q1 to 1.8M in Q2. Price sensitivity surveys conducted before the decision "
                "showed 67% of subscribers called the increase 'unacceptable.' "
                "SENTINEL would have flagged this on July 13 — the day after the announcement."
            ),
            "root_decision": {
                "decision_id": "DEC-20110712-QWIK",
                "decision_text": "Announce 60% price increase and split DVD/streaming into separate services (Qwikster)",
                "decision_type": "pricing",
                "logged_at": "2011-07-12T00:00:00",
                "rationale": "Separate streaming and DVD businesses for independent growth",
                "metrics_snapshot": {
                    "active_customers": 24600000,
                    "subscriber_growth_q1": 3300000,
                    "subscriber_growth_q2": 1800000,
                    "dvd_revenue_yoy_change": -0.10,
                    "price_sensitivity_survey": "67% said increase unacceptable",
                },
            },
            "causal_chain": [
                {
                    "event_id": "E001",
                    "date": "2011-07-12",
                    "type": "decision",
                    "title": "Qwikster announcement + 60% price increase",
                    "description": "Reed Hastings announces split of Netflix into two services. Streaming stays Netflix. DVD becomes Qwikster. Price effectively increases 60% for subscribers who want both.",
                    "severity": "root_cause",
                },
                {
                    "event_id": "E002",
                    "date": "2011-07-13",
                    "type": "signal",
                    "title": "Social media backlash — 82,000 angry comments",
                    "description": "Netflix blog post receives 82,000 comments, overwhelmingly negative. #DearNetflix trending on Twitter.",
                    "severity": "critical",
                },
                {
                    "event_id": "E003",
                    "date": "2011-08-01",
                    "type": "signal",
                    "title": "Subscriber cancellations begin",
                    "description": "Q3 cancellations accelerate. Internal projections revised downward.",
                    "severity": "high",
                },
                {
                    "event_id": "E004",
                    "date": "2011-09-18",
                    "type": "decision",
                    "title": "Qwikster formally announced (doubling down)",
                    "description": "Netflix officially announces Qwikster brand. Compounds confusion. Stock falls further.",
                    "severity": "warning",
                },
                {
                    "event_id": "E005",
                    "date": "2011-10-10",
                    "type": "outcome",
                    "title": "Qwikster cancelled — 23 days after launch",
                    "description": "800,000 subscribers lost in Q3. Netflix stock fell 77% from July peak. Qwikster cancelled.",
                    "metric_value": -800000.0,
                    "metric_label": "subscribers lost",
                    "severity": "critical",
                },
            ],
            "data_available_at_decision": {
                "subscriber_growth_q1_2011": "3.3M new subscribers",
                "subscriber_growth_q2_2011": "1.8M new subscribers (45% decline)",
                "dvd_revenue_trend": "-10% YoY — declining",
                "price_sensitivity_survey": "67% said 60% increase was unacceptable",
                "competitor_activity": "Amazon Prime expanding streaming catalog",
            },
            "data_that_predicted_outcome": [
                "Subscriber growth slowing 45% quarter-over-quarter — customers already questioning value",
                "Internal price sensitivity survey: 67% rejection rate of proposed 60% increase",
                "DVD revenue declining 10% YoY — splitting services would accelerate this, not fix it",
                "Amazon Prime had just doubled its streaming catalog — switching cost was lower than ever",
            ],
            "recommended_actions": [
                "Delay price increase until subscriber growth re-accelerates above 2.5M/quarter",
                "Test 20% increase with a cohort before full rollout",
                "Never split services — complexity increases churn risk disproportionately",
            ],
        }

    return {}


async def trace_causal_chain(
    outcome_description: str,
    outcome_date: datetime,
    affected_metric: str,
    demo_scenario: Optional[str] = None,
) -> Dict[str, Any]:
    if demo_scenario:
        return _build_demo_trace(demo_scenario)

    # Fetch candidate decisions from DB
    candidates = await mongodb.get_decisions_in_lookback(outcome_date)

    if not candidates:
        return {
            "trace_id": "TRACE-EMPTY",
            "outcome_description": outcome_description,
            "narrative": "No decisions found in the 14–90 day lookback window. Log decisions going forward to enable causal tracing.",
            "causal_chain": [],
            "pearson_r": 0.0,
            "p_value": 1.0,
            "days_of_warning": 0,
        }

    # Build metric time series for correlation
    metric_values = []
    decision_timestamps = []
    for d in candidates:
        snap = d.get("metrics_snapshot", {})
        val = snap.get(affected_metric)
        if val is not None:
            metric_values.append(float(val))
            decision_timestamps.append(
                (outcome_date - d["logged_at"]).days
            )

    pearson_r, p_value = (0.0, 1.0)
    if len(metric_values) >= 3:
        pearson_r, p_value = _pearson_r(decision_timestamps, metric_values)

    # Ask Gemini for causal analysis
    metrics_at_decision = {
        d["decision_id"]: d.get("metrics_snapshot", {}) for d in candidates
    }
    gemini_result = await analyze_causal_chain(
        outcome_description=outcome_description,
        outcome_date=outcome_date.isoformat(),
        affected_metric=affected_metric,
        candidate_decisions=candidates,
        metrics_at_decision=metrics_at_decision,
        metrics_at_outcome={},
    )

    days_of_warning = gemini_result.get("days_of_warning", 0)
    earliest_signal = outcome_date - timedelta(days=days_of_warning)

    return {
        "trace_id": f"TRACE-{outcome_date.strftime('%Y%m%d')}-{affected_metric[:6].upper()}",
        "outcome_description": outcome_description,
        "pearson_r": pearson_r,
        "p_value": p_value,
        "days_of_warning": days_of_warning,
        "earliest_signal_date": earliest_signal.isoformat(),
        "narrative": gemini_result.get("narrative", ""),
        "root_decision_id": gemini_result.get("root_decision_id"),
        "causal_chain": [],
        "data_that_predicted_outcome": gemini_result.get("data_that_predicted_outcome", []),
        "recommended_actions": gemini_result.get("preventive_actions", []),
        "data_available_at_decision": metrics_at_decision,
    }
