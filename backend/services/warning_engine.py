from datetime import datetime
from typing import List, Dict, Any, Optional
from ..db import mongodb
from .gemini_client import generate_warning_narrative


PATTERNS = [
    {
        "id": "P001",
        "name": "Churn spike post-price-increase",
        "description": "Price increase when NPS < 40 → churn spike within 30 days",
        "trigger_metric": "nps",
        "trigger_condition": "lt",
        "trigger_threshold": 40.0,
        "related_decision_type": "pricing",
        "lookback_days": 30,
        "historical_churn_rate": 0.82,
        "severity": "critical",
    },
    {
        "id": "P002",
        "name": "Key account churn signal",
        "description": "Support tickets 3x average + login frequency drop → churn within 21 days",
        "trigger_metric": "support_tickets_7d",
        "trigger_condition": "gt_multiple",
        "trigger_threshold": 2.5,
        "related_decision_type": "any",
        "lookback_days": 21,
        "historical_churn_rate": 0.71,
        "severity": "high",
    },
    {
        "id": "P003",
        "name": "CAC exceeds LTV / 3",
        "description": "CAC rising above LTV/3 → unsustainable unit economics within 60 days",
        "trigger_metric": "cac",
        "trigger_condition": "gt_ratio",
        "trigger_threshold": 0.33,
        "related_metric": "ltv",
        "related_decision_type": "hiring",
        "lookback_days": 60,
        "historical_churn_rate": 0.65,
        "severity": "high",
    },
    {
        "id": "P004",
        "name": "Runway below 6 months",
        "description": "Runway dropping below 6 months with no fundraise decision logged",
        "trigger_metric": "runway_months",
        "trigger_condition": "lt",
        "trigger_threshold": 6.0,
        "related_decision_type": "strategy",
        "lookback_days": 90,
        "historical_churn_rate": 0.78,
        "severity": "critical",
    },
]


def _check_pattern(pattern: Dict, snapshot: Dict) -> Optional[Dict]:
    metric = snapshot.get(pattern["trigger_metric"])
    if metric is None:
        return None

    triggered = False
    condition = pattern["trigger_condition"]

    if condition == "lt" and float(metric) < pattern["trigger_threshold"]:
        triggered = True
    elif condition == "gt" and float(metric) > pattern["trigger_threshold"]:
        triggered = True
    elif condition == "gt_multiple":
        avg = snapshot.get(f"{pattern['trigger_metric']}_avg", float(metric) / 3)
        if avg and float(metric) > avg * pattern["trigger_threshold"]:
            triggered = True
    elif condition == "gt_ratio":
        related = snapshot.get(pattern.get("related_metric", "ltv"))
        if related and float(metric) > float(related) * pattern["trigger_threshold"]:
            triggered = True

    if not triggered:
        return None

    return {
        "pattern_id": pattern["id"],
        "pattern_name": pattern["name"],
        "trigger_metric": pattern["trigger_metric"],
        "trigger_value": float(metric),
        "severity": pattern["severity"],
        "historical_churn_rate": pattern["historical_churn_rate"],
        "description": pattern["description"],
    }


async def check_warnings(
    snapshot: Dict[str, Any],
    demo_scenario: Optional[str] = None,
) -> List[Dict]:
    if demo_scenario:
        return _demo_warnings(demo_scenario)

    triggered = []
    for pattern in PATTERNS:
        match = _check_pattern(pattern, snapshot)
        if match:
            triggered.append(match)

    return triggered


def _demo_warnings(scenario: str) -> List[Dict]:
    if scenario == "acmesaas":
        return [
            {
                "warning_id": "WARN-20260707-001",
                "fired_at": "2026-07-07T14:23:00",
                "severity": "critical",
                "trigger_metric": "customer_login_frequency",
                "trigger_value": -0.60,
                "root_decision_id": "DEC-20260603-PRICE",
                "days_since_decision": 34,
                "causal_confidence": 0.87,
                "message": (
                    "Customer X (Acme Enterprise, $120K ARR) login frequency dropped 60% "
                    "in the last 7 days — a pattern seen in 87% of accounts that churned "
                    "following a price increase. This traces to the pricing decision of June 3."
                ),
                "recommended_action": "CEO call with Customer X within 48 hours. Consider grandfather pricing offer.",
                "acknowledged": False,
                "demo_scenario": "acmesaas",
            },
            {
                "warning_id": "WARN-20260617-001",
                "fired_at": "2026-06-17T10:05:00",
                "severity": "high",
                "trigger_metric": "subscription_seat_reduction",
                "trigger_value": -0.33,
                "root_decision_id": "DEC-20260603-PRICE",
                "days_since_decision": 14,
                "causal_confidence": 0.71,
                "message": (
                    "Customer X reduced active seats from 45 to 30 — a 33% reduction "
                    "detected by Fivetran Stripe connector. This is an early churn signal "
                    "that traces to the June 3 pricing decision."
                ),
                "recommended_action": "Flag account for Customer Success review. Schedule QBR.",
                "acknowledged": True,
                "demo_scenario": "acmesaas",
            },
        ]

    if scenario == "qwikster":
        return [
            {
                "warning_id": "WARN-QWIK-001",
                "fired_at": "2011-07-13T00:00:00",
                "severity": "critical",
                "trigger_metric": "subscriber_growth_rate",
                "trigger_value": -0.45,
                "root_decision_id": "DEC-20110712-QWIK",
                "days_since_decision": 1,
                "causal_confidence": 0.91,
                "message": (
                    "Subscriber growth decelerated 45% QoQ before the price announcement. "
                    "Internal survey showed 67% subscriber rejection rate of proposed increase. "
                    "Combined with a service split, SENTINEL projects 600K–1M subscriber losses in Q3."
                ),
                "recommended_action": "Halt announcement. A/B test 20% increase with 5% cohort first.",
                "acknowledged": False,
                "demo_scenario": "qwikster",
            }
        ]

    return []
