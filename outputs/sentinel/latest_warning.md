# 🟠 SENTINEL — Early Warning
**Warning ID:** `WARN-20260520-EA183B`
**Severity:** `HIGH`
**Fired:** May 20, 2026 at 15:31 UTC
**Auto-detected:** Yes (pattern matching)

---

## Warning
> Support tickets over the last 7 days have surged by an unprecedented 3400%. The root decision behind this event is unknown, but historical patterns show that support tickets tripling average combined with decreased login frequency predicts customer churn within 21 days.

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
