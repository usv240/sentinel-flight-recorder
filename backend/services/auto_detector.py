"""
Auto-detects business decisions from Fivetran data changes.
Watches for significant deltas in key metrics and creates pending
decision candidates — no manual logging required.
"""
from datetime import datetime
from typing import List, Dict, Any
from .fivetran_client import get_sync_history, list_connectors


DETECTION_RULES = [
    {
        "connector_service": "stripe",
        "change_type": "price_object_updated",
        "decision_type": "pricing",
        "label": "Pricing change detected",
        "description_template": "Stripe price object updated — possible pricing decision",
    },
    {
        "connector_service": "quickbooks",
        "change_type": "employee_count_delta",
        "delta_threshold": 0.1,  # 10% headcount change
        "decision_type": "hiring",
        "label": "Significant headcount change detected",
        "description_template": "Headcount changed by {delta:.0%} — possible hiring or layoff decision",
    },
    {
        "connector_service": "google_ads",
        "change_type": "spend_delta",
        "delta_threshold": 0.25,  # 25% spend change
        "decision_type": "strategy",
        "label": "Significant ad spend change detected",
        "description_template": "Ad spend changed by {delta:.0%} — possible growth strategy decision",
    },
    {
        "connector_service": "hubspot",
        "change_type": "stage_bulk_change",
        "delta_threshold": 0.2,
        "decision_type": "strategy",
        "label": "Large pipeline stage shift detected",
        "description_template": "20%+ of deals moved stage simultaneously — possible sales strategy change",
    },
]


async def detect_from_fivetran() -> List[Dict[str, Any]]:
    """
    Poll Fivetran sync history for significant data changes.
    Returns a list of pending decision candidates.
    """
    candidates: List[Dict[str, Any]] = []
    connectors = await list_connectors()

    for connector in connectors:
        service = connector.get("service", "")
        connector_id = connector.get("id", "")

        for rule in DETECTION_RULES:
            if rule["connector_service"] != service:
                continue

            history = await get_sync_history(connector_id, limit=5)
            if not history:
                continue

            # Check if there was a meaningful sync recently
            latest = history[0] if history else {}
            if latest.get("status") == "successful" and latest.get("rows_updated", 0) > 0:
                candidates.append({
                    "auto_detected": True,
                    "detection_source": f"{service}_{rule['change_type']}",
                    "decision_type": rule["decision_type"],
                    "decision_text": rule["label"],
                    "description": rule["description_template"].format(delta=0.2),
                    "detected_at": datetime.utcnow().isoformat(),
                    "connector_id": connector_id,
                    "connector_service": service,
                    "pending_confirmation": True,
                })

    return candidates


def detect_from_snapshot_delta(
    current: Dict[str, Any], previous: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare two metric snapshots and detect significant changes
    that likely indicate a business decision was made.
    """
    candidates = []

    checks = [
        ("mrr", "pricing", "MRR changed by {delta:.0%} — possible pricing or churn event"),
        ("cac", "strategy", "CAC changed by {delta:.0%} — possible acquisition strategy shift"),
        ("churn_rate", "product", "Churn rate changed by {delta:.0%} — significant customer health shift"),
        ("active_customers", "product", "Active customers changed by {delta:.0%}"),
    ]

    for metric, decision_type, template in checks:
        cur = current.get(metric)
        prev = previous.get(metric)
        if cur is None or prev is None or prev == 0:
            continue
        delta = (float(cur) - float(prev)) / abs(float(prev))
        if abs(delta) >= 0.10:  # 10%+ change triggers detection
            candidates.append({
                "auto_detected": True,
                "detection_source": f"metrics_delta_{metric}",
                "decision_type": decision_type,
                "decision_text": template.format(delta=delta),
                "delta": delta,
                "metric": metric,
                "previous_value": prev,
                "current_value": cur,
                "detected_at": datetime.utcnow().isoformat(),
                "pending_confirmation": True,
            })

    return candidates
