# 🔴 SENTINEL — Early Warning
**Warning ID:** `WARN-QWIK-001`
**Severity:** `CRITICAL`
**Fired:** May 18, 2026 at 14:17 UTC
**Auto-detected:** Yes (pattern matching)

---

## Warning
> Subscriber growth decelerated 45% QoQ before the price announcement. Internal survey showed 67% subscriber rejection rate of proposed increase. Combined with a service split, SENTINEL projects 600K–1M subscriber losses in Q3.

---

## Details
| Field | Value |
|-------|-------|
| Trigger metric | `subscriber_growth_rate` |
| Trigger value | -45% |
| Causal confidence | **91%** |
| Root decision ID | `DEC-20110712-QWIK` |
| Days since root decision | 1 days |

---

## Recommended Action
**Halt announcement. A/B test 20% increase with 5% cohort first.**

---

## Pattern Description
This warning was triggered because current metrics match a pattern that preceded
bad outcomes in 91% of historical cases with similar signals.

---
*SENTINEL fired this warning automatically based on pattern matching against the decision history.*
