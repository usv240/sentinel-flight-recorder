from fastapi import APIRouter
from ..db.schemas import AskRequest
from ..db import mongodb
from ..services.gemini_client import answer_why_question

router = APIRouter()


@router.post("/")
async def ask_sentinel(req: AskRequest):
    from ..services.output_writer import write_ask

    if req.demo_scenario == "acmesaas":
        result = _demo_answer(req.question, "acmesaas")
    elif req.demo_scenario == "qwikster":
        result = _demo_answer(req.question, "qwikster")
    else:
        decisions = await mongodb.get_decisions(limit=20)
        result = await answer_why_question(req.question, decisions)

    write_ask(req.question, result, req.demo_scenario)
    return result


def _demo_answer(question: str, scenario: str) -> dict:
    q = question.lower()

    if scenario == "acmesaas":
        if any(w in q for w in ["price", "pricing", "increase", "why did we raise"]):
            return {
                "answer": (
                    "On June 3, 2026, the decision to increase pricing by 20% was made "
                    "to improve unit economics — CAC had risen to $1,800 against an LTV of $9,200. "
                    "However, at the time of that decision, NPS stood at 31 (below the 40-point "
                    "safe threshold) and Customer X was already filing 3x the average support "
                    "ticket volume. SENTINEL would have recommended delaying the increase until "
                    "NPS recovered above 50."
                ),
                "relevant_decision_ids": ["DEC-20260603-PRICE"],
                "confidence": 0.94,
                "sources": ["DEC-20260603-PRICE (June 3, 2026) — Pricing decision with full metrics snapshot"],
            }
        if any(w in q for w in ["churn", "customer x", "lost", "cancel"]):
            return {
                "answer": (
                    "Customer X churned on July 15, 2026, resulting in $120,000 ARR lost. "
                    "The causal trace traces this to the June 3 pricing decision. "
                    "SENTINEL detected the first warning signal on June 17 (seat reduction) "
                    "and fired a critical warning on July 7 — 34 days after the root decision. "
                    "The recommended action was an executive call within 48 hours; "
                    "that call was not made."
                ),
                "relevant_decision_ids": ["DEC-20260603-PRICE"],
                "confidence": 0.87,
                "sources": ["Causal trace TRACE-ACME-001", "Warning WARN-20260707-001"],
            }

    if scenario == "qwikster":
        if any(w in q for w in ["qwikster", "split", "dvd", "price", "why"]):
            return {
                "answer": (
                    "On July 12, 2011, Netflix announced a 60% effective price increase by splitting "
                    "streaming and DVD into two separate services. The decision rationale was to allow "
                    "each business to grow independently. However, subscriber growth had already "
                    "decelerated 45% QoQ, and an internal survey showed 67% of subscribers called "
                    "the increase 'unacceptable'. SENTINEL would have flagged this data the following day."
                ),
                "relevant_decision_ids": ["DEC-20110712-QWIK"],
                "confidence": 0.91,
                "sources": ["DEC-20110712-QWIK", "Netflix Q3 2011 earnings report (public)"],
            }

    return {
        "answer": (
            "Based on the decision log, I can see decisions related to your question. "
            "Try asking more specifically: 'Why did we raise prices?', "
            "'What caused the churn spike?', or 'What data existed when we made the hiring decision?'"
        ),
        "relevant_decision_ids": [],
        "confidence": 0.4,
        "sources": [],
    }
