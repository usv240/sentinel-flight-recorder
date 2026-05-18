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

    if any(w in q for w in ["different", "should have", "mistake", "wrong"]):
        answers = {
            "acmesaas": (
                "The AcmeSaaS pricing decision should have been delayed until NPS recovered above 50. "
                "At decision time, NPS was 31 — 9 points below the 40-point warning threshold. "
                "The data that existed on June 3 predicted a 0.87 Pearson r causal correlation with churn. "
                "The recommended alternative: grandfather existing customers at current pricing for 6 months, "
                "and test the price increase with a 10% cohort before full rollout."
            ),
            "qwikster": (
                "Netflix should have tested a 20% increase on a small cohort before announcing a 60% increase. "
                "Subscriber growth had already decelerated 45% QoQ — a classic price sensitivity signal. "
                "The Qwikster split was an additional mistake: separating streaming from DVD compounded confusion "
                "and destroyed brand trust. SENTINEL would have recommended: delay announcement, "
                "A/B test 20% increase with 5% of subscribers, monitor for 30 days before full rollout."
            ),
        }
        return {
            "answer": answers.get(scenario, "See the causal trace for specific recommendations."),
            "relevant_decision_ids": [],
            "confidence": 0.91,
            "sources": [f"Causal trace — {scenario}"],
        }

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

    if any(w in q for w in ["pearson", "correlation", "r =", "r=", "causal", "statistic"]):
        return {
            "answer": (
                "SENTINEL uses Pearson r correlation to measure how strongly a business decision "
                "predicted a downstream outcome. The calculation works on the BigQuery metrics history "
                "synced via Fivetran MCP: SENTINEL compares the decision timestamp against the trajectory "
                "of outcome metrics over the following 14-90 days.\n\n"
                "r = 1.0 means perfect causal prediction. r > 0.7 is a strong signal. "
                "r = 0.87 for the AcmeSaaS pricing decision means: '87% of the churn trajectory "
                "was predictable from the data that existed on June 3.' "
                "The p-value (0.003) means there is only a 0.3% chance this correlation is random."
            ),
            "relevant_decision_ids": [],
            "confidence": 0.99,
            "sources": ["SciPy pearsonr", "BigQuery metrics history via Fivetran"],
        }

    if any(w in q for w in ["warning", "early warning", "active", "alert"]):
        s_data = {
            "acmesaas": "AcmeSaaS has 1 active critical warning: Customer X login frequency dropped 60%. This traces to the June 3 pricing decision (r=0.87). Recommended action: CEO call within 48 hours.",
            "qwikster": "The Netflix Qwikster scenario shows 1 critical warning fired on July 13, 2011 — the day after the announcement. 800K subscribers were at risk. SENTINEL recommended halting the announcement and A/B testing first.",
        }
        return {
            "answer": s_data.get(scenario, "No active warnings detected. All metrics are within normal ranges."),
            "relevant_decision_ids": [],
            "confidence": 0.92,
            "sources": [f"Warning engine — pattern match against {scenario} history"],
        }

    if any(w in q for w in ["fivetran", "mcp", "connector", "sync", "data source"]):
        return {
            "answer": (
                "SENTINEL uses the Fivetran MCP (Model Context Protocol) server to connect all data sources. "
                "Before every decision is logged, the agent calls:\n"
                "1. fivetran.list_connectors() — discovers all connected sources\n"
                "2. fivetran.trigger_sync() — forces a fresh data pull\n"
                "3. fivetran.get_connector_schema() — maps available metrics\n\n"
                "The synced data lands in BigQuery, where SENTINEL queries it to build the metrics snapshot "
                "attached to every decision. This makes every tool call auditable — you can see exactly "
                "which Fivetran connector provided which metric."
            ),
            "relevant_decision_ids": [],
            "confidence": 0.99,
            "sources": ["Fivetran MCP server", "BigQuery destination"],
        }

    if any(w in q for w in ["how", "work", "explain", "what is", "architecture", "stack"]):
        return {
            "answer": (
                "SENTINEL is a 5-step business flight recorder:\n\n"
                "1. Fivetran MCP syncs all connected data sources (Stripe, HubSpot, Salesforce)\n"
                "2. A full metrics snapshot is frozen at the exact moment of each decision\n"
                "3. Gemini 2.5 Flash analyzes the decision and calculates Pearson r correlation\n"
                "4. The warning engine pattern-matches current metrics against historical bad-outcome patterns\n"
                "5. When outcomes go wrong, the causal tracer shows the exact chain with days of warning\n\n"
                "Google Cloud Agent Builder orchestrates the full workflow, making every tool call visible."
            ),
            "relevant_decision_ids": [],
            "confidence": 0.99,
            "sources": ["SENTINEL architecture", "Google Cloud Agent Builder"],
        }

    return {
        "answer": (
            "Based on the decision log, I can see context relevant to your question. "
            "For best results, try:\n"
            "• 'Why did we raise prices?' — traces the pricing decision\n"
            "• 'What caused the churn spike?' — full causal chain analysis\n"
            "• 'Explain the Pearson correlation score' — how SENTINEL measures causation\n"
            "• 'How does Fivetran MCP work here?' — technical architecture\n"
            "• 'What are the active early warnings?' — current alert status"
        ),
        "relevant_decision_ids": [],
        "confidence": 0.4,
        "sources": [],
    }
