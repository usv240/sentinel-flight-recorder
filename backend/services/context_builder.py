import os
from datetime import datetime
from typing import Dict, Any, Optional
from .fivetran_client import list_connectors

# BigQuery client — only imported when available
try:
    from google.cloud import bigquery as bq_module
    _BQ_AVAILABLE = True
except ImportError:
    _BQ_AVAILABLE = False

_bq_client = None


def _get_bq():
    global _bq_client
    if not _BQ_AVAILABLE:
        return None
    if _bq_client is None:
        project = os.getenv("GOOGLE_PROJECT_ID")
        _bq_client = bq_module.Client(project=project) if project else None
    return _bq_client


def _bq_query(sql: str) -> Optional[list]:
    client = _get_bq()
    if not client:
        return None
    try:
        rows = list(client.query(sql).result())
        return [dict(r) for r in rows]
    except Exception:
        return None


async def build_metrics_snapshot(demo_scenario: Optional[str] = None) -> Dict[str, Any]:
    """
    Pull current metrics from all connected Fivetran sources via BigQuery.
    Falls back to demo data when BigQuery is not configured.
    """
    if demo_scenario:
        return _demo_snapshot(demo_scenario)

    snapshot: Dict[str, Any] = {"captured_at": datetime.utcnow().isoformat(), "sources": {}}
    dataset = os.getenv("BIGQUERY_DATASET_PREFIX", "sentinel_")
    project = os.getenv("GOOGLE_PROJECT_ID", "")

    # Primary: query Fivetran-synced Google Sheets data (acmesaas_metrics)
    # Table: google_sheets.acmesaas_metrics (created by Fivetran sync)
    sheets_sql = f"""
    SELECT
      date,
      mrr,
      arr,
      churn_rate,
      nps,
      active_customers,
      cac,
      ltv,
      support_tickets_7d,
      runway_months
    FROM `{project}.google_sheets.acmesaas_metrics`
    ORDER BY date DESC
    LIMIT 1
    """
    sheets_result = _bq_query(sheets_sql)
    if sheets_result:
        r = sheets_result[0]
        snapshot["sources"]["google_sheets"] = {"status": "connected", "table": "acmesaas_metrics"}
        snapshot["mrr"] = r.get("mrr")
        snapshot["arr"] = r.get("arr")
        snapshot["churn_rate"] = r.get("churn_rate")
        snapshot["nps"] = r.get("nps")
        snapshot["active_customers"] = r.get("active_customers")
        snapshot["cac"] = r.get("cac")
        snapshot["ltv"] = r.get("ltv")
        snapshot["support_tickets_7d"] = r.get("support_tickets_7d")
        snapshot["runway_months"] = r.get("runway_months")

        # Auto-detect flags from live data
        flags = []
        if snapshot.get("nps") and snapshot["nps"] < 40:
            flags.append(f"NPS={snapshot['nps']} is below the 40-point warning threshold")
        if snapshot.get("churn_rate") and snapshot["churn_rate"] > 0.08:
            flags.append(f"Churn rate {snapshot['churn_rate']:.1%} exceeds 8% threshold")
        if snapshot.get("support_tickets_7d") and snapshot["support_tickets_7d"] > 60:
            flags.append(f"Support tickets {snapshot['support_tickets_7d']}/week is elevated")
        if snapshot.get("runway_months") and snapshot["runway_months"] < 6:
            flags.append(f"Runway {snapshot['runway_months']:.1f} months — below 6-month safety threshold")
        if flags:
            snapshot["_flags"] = flags
    else:
        snapshot["sources"]["google_sheets"] = {"status": "not_connected"}

    snapshot["captured_at"] = datetime.utcnow().isoformat()

    # If BigQuery had no results, use partial demo data
    if not any(v for v in snapshot["sources"].values() if isinstance(v, dict) and "status" not in v):
        snapshot.update(_demo_snapshot("acmesaas_live"))

    return snapshot


def _demo_snapshot(scenario: str) -> Dict[str, Any]:
    """Pre-built metric snapshots for demo scenarios."""
    snapshots = {
        "acmesaas": {  # alias → baseline (for demo_scenario=acmesaas)
            "captured_at": "2026-06-03T09:00:00",
            "mrr": 85000, "arr": 1020000, "churn_rate": 0.09, "nps": 31,
            "active_customers": 142, "cac": 1800, "ltv": 9200,
            "support_tickets_7d": 89, "burn_rate": 95000, "runway_months": 14.2,
            "sources": {
                "stripe": {"mrr": 85000, "active_customers": 142, "churn_rate": 0.09},
                "hubspot": {"open_deals": 23, "pipeline_value": 340000},
            },
            "_flags": [
                "NPS=31 is below the 40-point warning threshold",
                "Support tickets 89/week is 3.1x company average",
                "Customer X: last login 2 days ago, 12 open tickets",
            ],
        },
        "acmesaas_baseline": {
            "captured_at": "2026-06-03T09:00:00",
            "mrr": 85000,
            "arr": 1020000,
            "churn_rate": 0.09,
            "nps": 31,
            "active_customers": 142,
            "cac": 1800,
            "ltv": 9200,
            "support_tickets_7d": 89,
            "pipeline_value": 340000,
            "burn_rate": 95000,
            "runway_months": 14.2,
            "sources": {
                "stripe": {"mrr": 85000, "active_customers": 142, "churn_rate": 0.09},
                "hubspot": {"open_deals": 23, "pipeline_value": 340000},
                "mixpanel": {"dau": 1240, "wau": 4800},
                "quickbooks": {"burn_rate": 95000, "cash_on_hand": 1350000},
            },
            "_flags": [
                "NPS=31 is below the 40-point warning threshold",
                "Support tickets 89/week is 3.1x company average",
                "Customer X: last login 2 days ago, 12 open tickets",
            ],
        },
        "acmesaas_live": {
            "captured_at": datetime.utcnow().isoformat(),
            "mrr": 91000,
            "arr": 1092000,
            "churn_rate": 0.07,
            "nps": 44,
            "active_customers": 158,
            "cac": 1950,
            "ltv": 11200,
            "support_tickets_7d": 34,
            "pipeline_value": 420000,
            "burn_rate": 98000,
            "runway_months": 16.8,
            "sources": {
                "stripe": {"mrr": 91000, "active_customers": 158, "churn_rate": 0.07},
                "hubspot": {"open_deals": 31, "pipeline_value": 420000},
            },
        },
        "qwikster_baseline": {
            "captured_at": "2011-07-12T00:00:00",
            "mrr": 32800000,
            "arr": 393600000,
            "active_customers": 24600000,
            "churn_rate": 0.042,
            "nps": 62,
            "sources": {
                "stripe": {"mrr": 32800000, "active_customers": 24600000},
            },
            "_flags": [
                "Subscriber growth slowing: Q1 2011 added 3.3M, Q2 2011 added only 1.8M",
                "DVD segment revenue declining 10% YoY",
                "Price sensitivity surveys: 67% of surveyed subscribers said 60% increase is unacceptable",
            ],
        },
    }
    return snapshots.get(scenario, snapshots["acmesaas_live"])
