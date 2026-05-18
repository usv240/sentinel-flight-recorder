# ✈️ SENTINEL — Decision Recorded
**Decision ID:** `DEC-20260518-86B803`
**Logged:** May 18, 2026 at 14:17 UTC
**Type:** `HIRING`
**Auto-detected:** False
**Detection source:** manual

---

## Decision
> FLOW TEST: Freeze all hiring for Q3

**Rationale:** Runway below 12 months

**Alternatives considered:**
- Not recorded

---

## Metrics Snapshot (Fivetran → BigQuery, captured at decision time)
*Source: 2026-06-03T09:00:00*

| Metric | Value |
|--------|-------|
| mrr | $85,000 |
| arr | $1,020,000 |
| churn_rate | 9.00% |
| nps | 31 |
| active_customers | 142 |
| cac | $1,800 |
| ltv | $9,200 |
| support_tickets_7d | 89 |
| burn_rate | $95,000 |
| runway_months | 14.2 |

---

## ⚠️ Flags at Time of Decision
- ⚠️ NPS=31 is below the 40-point warning threshold
- ⚠️ Support tickets 89/week is 3.1x company average
- ⚠️ Customer X: last login 2 days ago, 12 open tickets

---

## Connected Fivetran Sources
```json
{
  "stripe": {
    "mrr": 85000,
    "active_customers": 142,
    "churn_rate": 0.09
  },
  "hubspot": {
    "open_deals": 23,
    "pipeline_value": 340000
  }
}
```

---
*Recorded by SENTINEL. If this decision leads to a bad outcome, SENTINEL can trace the causal chain back to this moment.*
