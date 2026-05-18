# 🟠 SENTINEL — Early Warning
**Warning ID:** `WARN-20260518-C8D484`
**Severity:** `HIGH`
**Fired:** May 18, 2026 at 18:56 UTC
**Auto-detected:** Yes (pattern matching)

---

## Warning
> **WARNING:** Support tickets over the last 7 days have increased by 3400%. The root decision for this surge is unknown, but historical patterns show that support tickets 3x average combined with a login frequency drop reliably leads to churn within 21 days.

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
