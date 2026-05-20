# 🟠 SENTINEL — Early Warning
**Warning ID:** `WARN-20260519-D2EC59`
**Severity:** `HIGH`
**Fired:** May 19, 2026 at 14:59 UTC
**Auto-detected:** Yes (pattern matching)

---

## Warning
> Support tickets over the last 7 days have increased by a staggering 3400%. The root decision is unknown, and historical patterns reveal that support tickets tripling the average combined with a login frequency drop lead to churn within 21 days.

---

## Details
| Field | Value |
|-------|-------|
| Trigger metric | `support_tickets_7d` |
| Trigger value | 3400% |
| Causal confidence | **0%** |
| Root decision ID | `unknown` |
| Days since root decision | unknown days |

---

## Recommended Action
**Review decision log**

---

## Pattern Description
This warning was triggered because current metrics match a pattern that preceded
bad outcomes in 0% of historical cases with similar signals.

---
*SENTINEL fired this warning automatically based on pattern matching against the decision history.*
