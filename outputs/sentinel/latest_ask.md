# 💬 SENTINEL — Q&A Record
**Asked:** May 20, 2026 at 15:27 UTC
**Scenario:** acmesaas

---

## Question
> What caused the churn spike?

---

## SENTINEL's Answer
The churn spike was caused by Customer X (Acme Enterprise) churning on July 15, 2026, resulting in a loss of $120,000 ARR. The primary trigger was the 20% pricing increase decision (`DEC-20260603-PRICE`) made on June 3, 2026. At the time of this decision, the NPS was 31, which was below the 40-point warning threshold, and Customer X already had 12 open support tickets.

Following the pricing change:
- On June 17, Customer X reduced seats by 33% (45→30).
- On June 28, Customer X explicitly stated they were 'evaluating alternatives due to price changes'.
- On July 7, a critical warning (`WARN-20260707-001`) fired due to a 60% drop in Customer X's login frequency.

The Pearson correlation coefficient (r) of 0.87 with a p-value of 0.003 indicates a strong, statistically significant positive relationship between the pricing decision and the subsequent churn. The scenario data does not specify a Fivetran-connected source for these metrics.

To prevent similar future churn, it is recommended to delay significant pricing changes until NPS recovers above 50, and consider grandfathering existing customers for a transitional period, as outlined in `what_should_have_happened`.

---

## Sources
- decisions.DEC-20260603-PRICE
- decisions.DEC-20260603-PRICE.metrics_at_time.nps
- decisions.DEC-20260603-PRICE.flags_at_time
- outcome.description
- outcome.arr_lost
- outcome.causal_chain
- outcome.pearson_r
- outcome.p_value
- warnings.WARN-20260707-001
- what_should_have_happened

---

## Metadata
| Field | Value |
|-------|-------|
| Confidence | 95% |
| Relevant decisions | DEC-20260603-PRICE |

---
*Answered by SENTINEL using the decision log and Fivetran data context.*
