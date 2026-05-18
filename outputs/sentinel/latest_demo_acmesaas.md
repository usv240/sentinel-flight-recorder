# 📦 SENTINEL — Demo Scenario Loaded
**Scenario:** acmesaas
**Name:** AcmeSaaS — Pricing Disaster
**Loaded:** May 18, 2026 at 14:17 UTC

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
- [CRITICAL] Customer X (Acme Enterprise, $120K ARR) login frequency dropped 60% in the last 7 days — a pattern seen in 87% of accounts that churned following a price increase. This traces to the pricing decision of June 3.
- [HIGH] Customer X reduced active seats from 45 to 30 — a 33% reduction detected by Fivetran Stripe connector. This is an early churn signal that traces to the June 3 pricing decision.

---

## Causal Trace Summary
- **Outcome:** Customer X churned — $120,000 ARR lost
- **Pearson r:** 0.870
- **Days of warning:** 34
- **Chain length:** 5 events

---

## Metrics Snapshot
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
| pipeline_value | $340,000 |
| burn_rate | $95,000 |
| runway_months | 14.2 |

---

## Data Flags
- ⚠️ NPS=31 is below the 40-point warning threshold
- ⚠️ Support tickets 89/week is 3.1x company average
- ⚠️ Customer X: last login 2 days ago, 12 open tickets
