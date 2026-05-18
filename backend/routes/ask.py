import json
from fastapi import APIRouter
from ..db.schemas import AskRequest
from ..db import mongodb
from ..services.gemini_client import answer_with_scenario_context, answer_why_question

router = APIRouter()

# Full structured scenario facts — used as Gemini context, not as answers
_SCENARIO_CONTEXT = {
    "acmesaas": {
        "company": "AcmeSaaS (fictional B2B SaaS)",
        "period": "June–July 2026",
        "decisions": [
            {
                "id": "DEC-20260603-PRICE",
                "date": "2026-06-03",
                "type": "pricing",
                "text": "Increase all pricing tiers by 20%",
                "rationale": "CAC was rising to $1,800 against LTV of $9,200. Unit economics needed improvement.",
                "alternatives_considered": ["10% increase", "add features instead", "keep pricing"],
                "metrics_at_time": {
                    "mrr": 85000, "arr": 1020000, "churn_rate": 0.09, "nps": 31,
                    "active_customers": 142, "cac": 1800, "ltv": 9200,
                    "support_tickets_7d": 89, "runway_months": 14.2,
                },
                "flags_at_time": [
                    "NPS=31 is below the 40-point warning threshold",
                    "Support tickets 89/week is 3.1x company average",
                    "Customer X: last login 2 days ago, 12 open tickets",
                ],
            },
            {
                "id": "DEC-20260515-HIRE",
                "date": "2026-05-15",
                "type": "hiring",
                "text": "Hire 3 senior engineers for platform reliability",
                "rationale": "Uptime SLA at risk, two enterprise customers complaining",
                "metrics_at_time": {"mrr": 82000, "nps": 38, "churn_rate": 0.07},
            },
        ],
        "outcome": {
            "description": "Customer X (Acme Enterprise, $120K ARR) churned on July 15, 2026",
            "arr_lost": 120000,
            "causal_chain": [
                "Jun 3: Pricing +20% with NPS=31 (below safe threshold)",
                "Jun 17: Customer X reduces seats 45→30 (-33%) — first signal",
                "Jun 28: Customer X ticket: 'evaluating alternatives due to price changes'",
                "Jul 7: Customer X login frequency drops 60% — critical warning fires",
                "Jul 15: Customer X cancels — $120K ARR lost",
            ],
            "days_of_warning_available": 34,
            "pearson_r": 0.87,
            "p_value": 0.003,
        },
        "warnings": [
            {
                "id": "WARN-20260707-001",
                "fired": "2026-07-07",
                "severity": "critical",
                "message": "Customer X login frequency dropped 60% — traces to June 3 pricing decision",
                "recommended_action": "CEO call with Customer X within 48 hours. Consider grandfather pricing.",
            }
        ],
        "what_should_have_happened": (
            "The pricing decision should have been delayed until NPS recovered above 50. "
            "Alternatives: grandfather existing customers for 6 months, test 10% increase with a cohort, "
            "or improve product before raising prices."
        ),
    },
    "qwikster": {
        "company": "Netflix (public company, 2011)",
        "period": "July–October 2011",
        "decisions": [
            {
                "id": "DEC-20110712-QWIK",
                "date": "2011-07-12",
                "type": "pricing",
                "text": "Announce 60% price increase + split DVD/streaming into separate services (Qwikster)",
                "rationale": "Allow streaming and DVD businesses to grow independently with separate focus",
                "metrics_at_time": {
                    "active_customers": 24600000,
                    "subscriber_growth_q1": 3300000,
                    "subscriber_growth_q2": 1800000,
                    "dvd_revenue_yoy_change": -0.10,
                    "price_sensitivity_survey": "67% said 60% increase unacceptable",
                    "churn_rate": 0.042,
                    "nps": 62,
                },
                "flags_at_time": [
                    "Subscriber growth slowing: Q1 +3.3M → Q2 +1.8M (45% deceleration)",
                    "DVD segment revenue declining 10% YoY",
                    "Price sensitivity survey: 67% found 60% increase unacceptable",
                    "Amazon Prime doubled streaming catalog in Q1 2011",
                ],
            }
        ],
        "outcome": {
            "description": "800,000 subscribers lost in Q3 2011 — worst quarter in Netflix history",
            "subscribers_lost": 800000,
            "stock_decline_pct": 77,
            "causal_chain": [
                "Jul 12: Qwikster announced + 60% price increase",
                "Jul 13: Netflix blog receives 82,000 angry comments",
                "Aug 1: Cancellations accelerate — internal projections revised down",
                "Sep 18: Qwikster formally announced — doubles down on failed strategy",
                "Oct 10: Qwikster cancelled 23 days after launch — 800K subscribers already lost",
            ],
            "days_of_warning_available": 0,
            "pearson_r": 0.91,
            "p_value": 0.001,
        },
        "warnings": [
            {
                "id": "WARN-QWIK-001",
                "fired": "2011-07-13",
                "severity": "critical",
                "message": "Subscriber growth decelerated 45% QoQ. 67% survey rejection. Projecting 600K–1M losses.",
                "recommended_action": "Halt announcement. A/B test 20% increase with 5% cohort first.",
            }
        ],
        "what_should_have_happened": (
            "Netflix should have tested a 20% increase with a 5% subscriber cohort before any announcement. "
            "The service split was an additional strategic error — complexity increases churn risk. "
            "The 45% subscriber growth deceleration was a clear signal the value proposition was weakening."
        ),
    },
}


@router.post("/")
async def ask_sentinel(req: AskRequest):
    from ..services.output_writer import write_ask

    if req.demo_scenario in _SCENARIO_CONTEXT:
        ctx = _SCENARIO_CONTEXT[req.demo_scenario]
        result = await answer_with_scenario_context(req.question, ctx)
    else:
        decisions = await mongodb.get_decisions(limit=20)
        result = await answer_why_question(req.question, decisions)

    write_ask(req.question, result, req.demo_scenario)
    return result
