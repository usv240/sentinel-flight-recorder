# 📦 SENTINEL — Demo Scenario Loaded
**Scenario:** qwikster
**Name:** Netflix Qwikster — The $3B Mistake
**Loaded:** May 20, 2026 at 15:23 UTC

---

## Scenario Summary
| Field | Value |
|-------|-------|
| Company | Netflix (public) |
| Period | July–October 2011 |
| Outcome | Stock -77%, 800K subscribers lost, Qwikster cancelled in 23 days |
| Days of warning | 0 |

**Description:** Netflix announced a 60% price increase combined with a DVD/streaming split. Subscriber growth had already decelerated 45% QoQ. Internal surveys showed 67% of subscribers called the increase 'unacceptable'. SENTINEL would have flagged this on July 13, the day after the announcement.

---

## Decisions Loaded (1)
- `DEC-20110712-QWIK` — Announce 60% price increase + Qwikster DVD spinoff [pricing] → catastrophic

---

## Active Warnings (1)
- [CRITICAL] Subscriber growth deceleration has increased by 45%. This directly follows yesterday's announcement of a 60% price increase and Qwikster split, echoing historical patterns of 45% QoQ subscriber growth deceleration, 67% internal survey rejection, and 82,000 negative social comments within 24 hours.

---

## Causal Trace Summary
- **Outcome:** 800,000 subscribers lost — worst quarter in Netflix history
- **Pearson r:** 0.945
- **Days of warning:** 0
- **Chain length:** 5 events

---

## Metrics Snapshot
| Metric | Value |
|--------|-------|
| mrr | $32,800,000 |
| arr | $393,600,000 |
| active_customers | 24600000 |
| churn_rate | 4.20% |
| nps | 62 |
| _data_source | demo_baseline |

---

## Data Flags
- ⚠️ Subscriber growth slowing: Q1 2011 added 3.3M, Q2 2011 added only 1.8M
- ⚠️ DVD segment revenue declining 10% YoY
- ⚠️ Price sensitivity surveys: 67% of surveyed subscribers said 60% increase is unacceptable
