# 📦 SENTINEL — Demo Scenario Loaded
**Scenario:** acmesaas
**Name:** AcmeSaaS — Pricing Disaster
**Loaded:** May 18, 2026 at 20:02 UTC

---

## Scenario Summary
| Field | Value |
|-------|-------|
| Company | AcmeSaaS (fictional) |
| Period | June–July 2026 |
| Outcome | $120K ARR lost |
| Days of warning | 34 |

**Description:** AcmeSaaS raised prices 20% to improve unit economics. Their NPS was 31 at decision time — 9 points below the warning threshold. Customer X showed 12 support tickets and a login gap of 2 days. 34 days of warning were available. None were acted on.

---

## Decisions Loaded (3)
- `DEC-20260603-PRICE` — Increase all pricing tiers by 20% [pricing] → churn_spike
- `DEC-20260515-HIRE` — Hire 3 senior engineers to accelerate product roadmap [hiring] → positive
- `DEC-20260428-PIVOT` — Pivot focus to enterprise segment, pause SMB outbound [strategy] → monitoring

---

## Active Warnings (2)
- [CRITICAL] **ALERT: Customer login frequency has plummeted by 60%. This critical drop directly follows the 20% pricing tier increase 34 days ago, mirroring the pattern seen in 87% of churned accounts after similar price hikes when NPS was below 40.**
- [HIGH] Immediate alert: Subscription seats have decreased by 33%. This directly follows the 20% pricing tier increase implemented 14 days ago, which historical data identifies as an early churn signal.

---

## Causal Trace Summary
- **Outcome:** Customer X churned — $120,000 ARR lost
- **Pearson r:** 0.998
- **Days of warning:** 34
- **Chain length:** 5 events

---

## Metrics Snapshot
| Metric | Value |
|--------|-------|
| mrr | $91,000 |
| arr | $1,092,000 |
| churn_rate | 7.00% |
| nps | 44 |
| active_customers | 158 |
| cac | $1,950 |
| ltv | $11,200 |
| support_tickets_7d | 34 |
| pipeline_value | $340,000 |
| burn_rate | $95,000 |
| runway_months | 16.8 |
| _data_source | bigquery_live |

---

## Data Flags
- ⚠️ NPS=31 is below the 40-point warning threshold
- ⚠️ Support tickets 89/week is 3.1x company average
- ⚠️ Customer X: last login 2 days ago, 12 open tickets
