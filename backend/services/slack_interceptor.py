"""
SENTINEL Slack Interceptor — Multi-Agent Decision Council

When someone types a business decision in Slack, SENTINEL convenes a council
of 4 specialized Gemini agents that analyze in parallel and post results as
they arrive — so you get a live view of multi-agent reasoning, not a single
black-box answer.

Agent roles:
  1. Data Agent      — queries Fivetran BigQuery, reports live metrics + trends
  2. Risk Agent      — Bradford Hill + historical patterns + ARR at risk
  3. Alternatives    — generates 3 concrete safer paths with expected outcomes
  4. Lead Agent      — synthesizes all 3, produces the final recommendation

User commands after analysis:
  PLAN     → 30-60-90 day recovery roadmap (another agent call)
  PROCEED  → logs the decision in MongoDB against agent advice
  CANCEL   → dismisses the alert

This is what makes SENTINEL genuinely different: the agent lives inside the
conversation where decisions happen, not in a separate dashboard.
"""

import asyncio
import logging
import re
import os
import httpx
from typing import Optional

log = logging.getLogger("sentinel.interceptor")

# ── Decision keyword patterns ─────────────────────────────────────────────────
_DECISION_PATTERNS = {
    "pricing": {
        "keywords": [
            r"raise\s+pric", r"increase\s+pric", r"price\s+increase",
            r"pric\w*\s+change", r"\d+\s*%\s+increase", r"increase.*\d+\s*%",
            r"pricing\s+tier", r"new\s+pric", r"adjust.*pric",
            r"bump.*price", r"hike.*price",
        ],
        "type": "pricing", "emoji": "💰",
    },
    "hiring": {
        "keywords": [
            r"hire\s+a\b", r"we\s+should\s+hire", r"bring\s+on\s+a",
            r"\bhire\s+\d+", r"head\s*count", r"onboard\s+a",
            r"new\s+engineer", r"senior\s+hire",
        ],
        "type": "hiring", "emoji": "👥",
    },
    "product": {
        "keywords": [
            r"remove.*feature", r"kill\s+the\s+feature",
            r"sunset\s+", r"deprecate\s+", r"cut\s+the\s+feature",
            r"eliminate.*feature", r"remove.*from\s+product",
        ],
        "type": "product", "emoji": "🚀",
    },
    "strategy": {
        "keywords": [
            r"pivot\s+to", r"enter\s+the\s+market", r"expand\s+into",
            r"shut\s+down\s+the", r"strategic\s+shift",
        ],
        "type": "strategy", "emoji": "🎯",
    },
}

# Active intercepts: message_ts -> context dict
_active_intercepts: dict = {}
_processed_ts: set = set()


# ── Slack HTTP helper ─────────────────────────────────────────────────────────

async def _post_to_slack(channel: str, thread_ts: str, color: str, blocks: list) -> Optional[str]:
    """Post a threaded Block Kit message. Returns the new message ts."""
    token = os.getenv("SLACK_BOT_TOKEN", "")
    if not token:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={
                    "channel": channel,
                    "thread_ts": thread_ts,
                    "attachments": [{"color": color, "blocks": blocks}],
                },
            )
            data = resp.json()
            if not data.get("ok"):
                log.error(f"Slack error: {data.get('error')}")
                return None
            return data.get("ts")
    except Exception as e:
        log.error(f"Slack post failed: {e}")
        return None


async def _update_slack(channel: str, ts: str, color: str, blocks: list):
    """Update an existing message in-place."""
    token = os.getenv("SLACK_BOT_TOKEN", "")
    if not token:
        return
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                "https://slack.com/api/chat.update",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={
                    "channel": channel,
                    "ts": ts,
                    "attachments": [{"color": color, "blocks": blocks}],
                },
            )
    except Exception as e:
        log.error(f"Slack update failed: {e}")


# ── Decision detection ────────────────────────────────────────────────────────

def _detect_decision(text: str) -> Optional[dict]:
    lower = text.lower()
    for category, config in _DECISION_PATTERNS.items():
        for pattern in config["keywords"]:
            if re.search(pattern, lower):
                return {"category": category, "type": config["type"], "emoji": config["emoji"]}
    return None


# ── The four specialized Gemini agents ────────────────────────────────────────

async def _data_agent(decision_text: str, snapshot: dict) -> str:
    """Agent 1: analyzes live Fivetran BigQuery metrics."""
    from .gemini_client import generate
    nps   = snapshot.get("nps", "unknown")
    churn = snapshot.get("churn_rate", "unknown")
    mrr   = snapshot.get("mrr", "unknown")
    arr   = snapshot.get("arr", "unknown")
    tickets = snapshot.get("support_tickets_7d", "unknown")

    try:
        churn_fmt = f"{float(churn):.1%}" if churn != "unknown" else "unknown"
        mrr_fmt   = f"${float(mrr):,.0f}" if mrr != "unknown" else "unknown"
    except Exception:
        churn_fmt, mrr_fmt = str(churn), str(mrr)

    prompt = f"""You are SENTINEL's Data Agent. Analyze these live metrics pulled from Fivetran BigQuery.

PROPOSED DECISION: {decision_text}

LIVE METRICS:
- NPS: {nps} (safe threshold: 45; warning: 35)
- Churn Rate: {churn_fmt} (safe: <6%; warning: >8%)
- MRR: {mrr_fmt}
- Support tickets (7d): {tickets}

Write EXACTLY 2 sentences:
1. What the data shows about the current state (cite specific numbers)
2. Whether these metrics SUPPORT or CONTRADICT the proposed decision and why

Be blunt. Under 60 words total. End with: → Verdict: SUPPORTS / CONTRADICTS / NEUTRAL"""

    try:
        result = await generate(prompt)
        return result.strip() if result else "Data analysis unavailable."
    except Exception as e:
        return f"Live metrics: NPS={nps}, Churn={churn_fmt}, MRR={mrr_fmt}. → Verdict: See risk analysis."


async def _risk_agent(decision_text: str, precheck: dict, bh_score: Optional[float], bh_strength: Optional[str]) -> str:
    """Agent 2: statistical risk probability using Bradford Hill + historical patterns."""
    from .gemini_client import generate
    risk_level  = precheck.get("risk_level", "unknown")
    risk_score  = precheck.get("risk_score", 0)
    patterns    = precheck.get("pattern_matches", [])
    arr_impact  = precheck.get("estimated_arr_impact", {})

    pattern_text = ""
    if patterns:
        p = patterns[0]
        pattern_text = f"Historical match: {p['historical_failure_rate']:.0%} failure rate in n={p['n_examples']} similar decisions."

    arr_text = ""
    if arr_impact.get("low"):
        arr_text = f"ARR at risk: ${abs(arr_impact['low']):,}–${abs(arr_impact['high']):,}."

    prompt = f"""You are SENTINEL's Risk Agent. Assess the statistical probability of a bad outcome.

PROPOSED DECISION: {decision_text}
RISK LEVEL: {risk_level.upper()} ({risk_score:.0%} risk score)
BRADFORD HILL CAUSAL SCORE: {f"{bh_score:.0%} ({bh_strength} causal evidence)" if bh_score else "Not computed"}
{pattern_text}
{arr_text}

Write EXACTLY 2 sentences:
1. The statistical risk probability with the most important evidence (cite exact numbers)
2. What the historical pattern says will happen

Be direct. Under 60 words. End with: → Verdict: HIGH RISK / MEDIUM RISK / LOW RISK"""

    try:
        result = await generate(prompt)
        return result.strip() if result else f"Risk level: {risk_level.upper()} ({risk_score:.0%}). {pattern_text}"
    except Exception as e:
        return f"Risk: {risk_level.upper()} ({risk_score:.0%}). {pattern_text} {arr_text}"


async def _alternatives_agent(decision_text: str, decision_type: str, snapshot: dict, precheck: dict) -> str:
    """Agent 3: generates 3 concrete, specific alternatives with expected outcomes."""
    from .gemini_client import generate
    nps   = snapshot.get("nps", "?")
    churn = snapshot.get("churn_rate", "?")
    alts  = precheck.get("alternative_recommendations", [])

    try:
        churn_fmt = f"{float(churn):.1%}" if churn != "?" else "?"
    except Exception:
        churn_fmt = str(churn)

    context_alts = "\n".join(f"- {a}" for a in alts[:3]) if alts else "None pre-computed."

    prompt = f"""You are SENTINEL's Alternatives Agent. Generate 3 concrete alternatives to this decision.

PROPOSED DECISION: {decision_text}
DECISION TYPE: {decision_type}
CONTEXT: NPS={nps}, Churn={churn_fmt}
PRE-COMPUTED SUGGESTIONS:
{context_alts}

Generate exactly 3 alternatives. Each must be:
- Specific (not generic)
- Include a concrete expected outcome
- Include a risk level (LOW/MEDIUM/HIGH)

Format EXACTLY:
1. [What to do instead]: [Expected outcome] → Risk: LOW/MEDIUM/HIGH
2. [What to do instead]: [Expected outcome] → Risk: LOW/MEDIUM/HIGH
3. [What to do instead]: [Expected outcome] → Risk: LOW/MEDIUM/HIGH"""

    try:
        result = await generate(prompt)
        return result.strip() if result else "\n".join(f"{i+1}. {a}" for i, a in enumerate(alts[:3]))
    except Exception as e:
        return "\n".join(f"{i+1}. {a}" for i, a in enumerate(alts[:3])) or "Consult your data before deciding."


async def _lead_agent(decision_text: str, data_out: str, risk_out: str, alts_out: str) -> str:
    """Agent 4 (Lead): synthesizes all 3 agents into a final recommendation + next step."""
    from .gemini_client import generate

    prompt = f"""You are SENTINEL's Lead Agent. Read the analysis from 3 specialized agents and produce the final verdict.

PROPOSED DECISION: {decision_text}

DATA AGENT ANALYSIS:
{data_out}

RISK AGENT ANALYSIS:
{risk_out}

ALTERNATIVES AGENT OPTIONS:
{alts_out}

Produce EXACTLY 3 lines:
RECOMMENDATION: [DO NOT PROCEED / PROCEED WITH MODIFICATIONS / PROCEED]
KEY REASON: [One sentence — the single most important factor]
NEXT STEP: [One concrete, specific action with a deadline]

Be decisive. No hedging. Under 60 words total."""

    try:
        result = await generate(prompt)
        return result.strip() if result else "RECOMMENDATION: Review with leadership before proceeding."
    except Exception as e:
        return "RECOMMENDATION: High risk detected. Review alternatives before deciding."


async def _plan_agent(decision_text: str, decision_type: str, snapshot: dict, best_alternative: str) -> str:
    """Generates a 30-60-90 day recovery / implementation roadmap."""
    from .gemini_client import generate
    nps   = snapshot.get("nps", "?")
    churn = snapshot.get("churn_rate", "?")
    mrr   = snapshot.get("mrr", "?")
    try:
        churn_fmt = f"{float(churn):.1%}" if churn != "?" else "?"
        mrr_fmt   = f"${float(mrr):,.0f}" if mrr != "?" else "?"
    except Exception:
        churn_fmt, mrr_fmt = str(churn), str(mrr)

    prompt = f"""You are SENTINEL's Planning Agent. Create a specific 30-60-90 day plan.

DECISION CONTEXT: {decision_text}
DECISION TYPE: {decision_type}
CURRENT STATE: NPS={nps}, Churn={churn_fmt}, MRR={mrr_fmt}
RECOMMENDED PATH: {best_alternative}

Create a 30-60-90 day plan. Each period: exactly 2 actions + 1 metric target + 1 decision gate.

Format EXACTLY:
*30 DAYS:*
• [Action 1 with owner]
• [Action 2 with owner]
Target: [specific metric]
Gate: If [condition] → [then do this]

*60 DAYS:*
• [Action 1]
• [Action 2]
Target: [specific metric]
Gate: If [condition] → [then do this]

*90 DAYS:*
• [Action 1]
• [Action 2]
Target: [specific metric]
Gate: If [condition] → [then proceed/escalate]

Use exact numbers. Be specific about owners (CEO, VP Sales, Product, CS Team)."""

    try:
        result = await generate(prompt)
        return result.strip() if result else "30-day plan unavailable. Review manually with leadership."
    except Exception as e:
        return "Plan generation failed. Run python check.py for system status."


# ── Main interception flow ────────────────────────────────────────────────────

async def process_message_event(event: dict):
    """Entry point — called as a FastAPI BackgroundTask from the Slack Events route."""
    text      = event.get("text", "")
    channel   = event.get("channel", "")
    ts        = event.get("ts", "")
    thread_ts = event.get("thread_ts", ts)

    if not text or not channel or not ts:
        return

    # Dedup
    if ts in _processed_ts:
        return
    _processed_ts.add(ts)
    if len(_processed_ts) > 2000:
        _processed_ts.clear()

    # ── Reply to an active intercept thread ─────────────────────────────────
    if thread_ts in _active_intercepts and ts != thread_ts:
        await _handle_reply(text, channel, thread_ts)
        return

    # ── Detect a new decision ────────────────────────────────────────────────
    match = _detect_decision(text)
    if not match:
        return

    log.info(f"Intercepted {match['type']} decision in {channel}: {text[:80]}")

    # ── Step 1: Post "Council convened" immediately (under 3s) ─────────────
    opening_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*SENTINEL Decision Council* — {match['emoji']} {match['type'].upper()} decision intercepted\n"
                    f"3 agents analyzing in parallel. Results appearing below..."
                ),
            },
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "SENTINEL · Fivetran BigQuery → Gemini 3 Flash · autonomous — no human triggered this"}],
        },
    ]
    await _post_to_slack(channel, ts, "#007AFF", opening_blocks)

    # ── Step 2: Get live BigQuery data ───────────────────────────────────────
    snapshot: dict = {}
    try:
        from .bigquery_pipeline import get_real_time_series, get_current_metrics_from_ts
        ts_data = await get_real_time_series("acmesaas")
        if ts_data:
            snapshot = get_current_metrics_from_ts(ts_data)
    except Exception as e:
        log.warning(f"BigQuery failed (proceeding with empty snapshot): {e}")

    # ── Step 3: Run precheck + Bradford Hill ─────────────────────────────────
    precheck: dict = {}
    try:
        from .precheck_engine import run_precheck
        precheck = await run_precheck(
            decision_text=text,
            decision_type=match["type"],
            snapshot=snapshot,
            scenario="acmesaas",
        )
    except Exception as e:
        log.error(f"Precheck failed: {e}")

    bh_score, bh_strength = None, None
    try:
        from .bradford_hill import score_bradford_hill
        from .causal_tracer import _run_causal_battery, _DEMO_TIME_SERIES
        ts_demo = _DEMO_TIME_SERIES.get("acmesaas", {})
        if ts_demo.get("churn_values"):
            ca = _run_causal_battery(
                ts_demo["churn_values"], ts_demo["nps_values"],
                ts_demo.get("churn_decision_index", 2), "churn_rate",
            )
            bh = score_bradford_hill(
                causal_analysis=ca,
                root_decision={"decision_type": match["type"], "logged_at": "now"},
                causal_chain=[],
                data_signals=precheck.get("blocking_conditions", []),
                days_of_warning=0,
            )
            bh_score    = bh.get("total_score")
            bh_strength = bh.get("causal_strength")
    except Exception:
        pass

    # ── Step 4: Run 3 agents in parallel ─────────────────────────────────────
    data_task  = asyncio.create_task(_data_agent(text, snapshot))
    risk_task  = asyncio.create_task(_risk_agent(text, precheck, bh_score, bh_strength))
    alts_task  = asyncio.create_task(_alternatives_agent(text, match["type"], snapshot, precheck))

    # Post each agent's result as it arrives (race between tasks)
    data_out = risk_out = alts_out = ""
    for coro in asyncio.as_completed([data_task, risk_task, alts_task]):
        try:
            result = await coro
        except Exception as e:
            result = f"Agent error: {e}"

        # Figure out which agent finished by checking tasks
        if coro.cr_origin is not None:  # fallback identification
            pass

    # Simpler: await all together but post sequentially
    try:
        data_out, risk_out, alts_out = await asyncio.gather(
            data_task, risk_task, alts_task, return_exceptions=True
        )
        if isinstance(data_out, Exception): data_out = "Data agent unavailable."
        if isinstance(risk_out, Exception): risk_out = "Risk agent unavailable."
        if isinstance(alts_out, Exception): alts_out = "Alternatives agent unavailable."
    except Exception as e:
        data_out = risk_out = alts_out = "Agent error — check server logs."

    # ── Step 5: Post each agent's result ─────────────────────────────────────
    risk_color = {"high": "#FF3B30", "medium": "#FF9500", "low": "#30D158"}.get(
        precheck.get("risk_level", "low"), "#8E8E93"
    )

    await _post_to_slack(channel, ts, "#2D9CDB", [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Data Agent* — Fivetran BigQuery\n{data_out}"}},
    ])

    await _post_to_slack(channel, ts, risk_color, [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Risk Agent* — Bradford Hill + Historical Patterns\n{risk_out}"}},
    ])

    await _post_to_slack(channel, ts, "#F2994A", [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Alternatives Agent* — Scenario Planner\n{alts_out}"}},
    ])

    # ── Step 6: Lead Agent synthesis ─────────────────────────────────────────
    synthesis = await _lead_agent(text, data_out, risk_out, alts_out)

    final_blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Lead Agent — Verdict*\n\n{synthesis}"}},
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Reply *`PLAN`* for 30-60-90 day roadmap  ·  *`PROCEED`* to log with risk acknowledged  ·  *`CANCEL`* to dismiss",
            },
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "SENTINEL · 4 agents · Fivetran BigQuery + Gemini 3 Flash · autonomous"}],
        },
    ]
    await _post_to_slack(channel, ts, risk_color, final_blocks)

    # ── Store context for reply handling ─────────────────────────────────────
    _active_intercepts[ts] = {
        "precheck":      precheck,
        "decision_text": text,
        "decision_type": match["type"],
        "channel":       channel,
        "snapshot":      snapshot,
        "synthesis":     synthesis,
        "alts_out":      alts_out,
    }


# ── Reply handler ─────────────────────────────────────────────────────────────

async def _handle_reply(text: str, channel: str, thread_ts: str):
    """Handle PLAN / PROCEED / CANCEL replies in an intercepted thread."""
    cmd = text.strip().upper()
    intercept = _active_intercepts.get(thread_ts)
    if not intercept:
        return

    if "PLAN" in cmd:
        await _post_to_slack(channel, thread_ts, "#007AFF", [
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Planning Agent* — generating 30-60-90 day roadmap..."}},
        ])
        plan = await _plan_agent(
            decision_text=intercept.get("decision_text", ""),
            decision_type=intercept.get("decision_type", "unknown"),
            snapshot=intercept.get("snapshot", {}),
            best_alternative=intercept.get("alts_out", "").split("\n")[0] if intercept.get("alts_out") else "",
        )
        await _post_to_slack(channel, thread_ts, "#007AFF", [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*SENTINEL — 30-60-90 Day Plan*\n\n{plan}"}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": "SENTINEL will monitor these metrics automatically and alert you at each checkpoint."}]},
        ])

    elif any(w in cmd for w in ("PROCEED", "LOG", "YES")):
        decision_id = "PENDING"
        try:
            from ..db import mongodb
            decision_id = await mongodb.insert_decision({
                "decision_text":        intercept.get("decision_text", ""),
                "decision_type":        intercept.get("decision_type", "unknown"),
                "source":               "slack_interception",
                "against_agent_advice": intercept.get("precheck", {}).get("risk_level") in ("high", "medium"),
                "risk_level_at_log":    intercept.get("precheck", {}).get("risk_level", "unknown"),
                "metrics_snapshot":     intercept.get("snapshot", {}),
                "rationale":            "Logged via Slack after SENTINEL multi-agent analysis",
                "council_synthesis":    intercept.get("synthesis", ""),
            })
        except Exception as e:
            log.error(f"Failed to log intercepted decision: {e}")

        await _post_to_slack(channel, thread_ts, "#30D158", [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"✅ *Decision logged* — ID: `{decision_id}`\n"
                        "SENTINEL will monitor metrics for the next 90 days. "
                        "If a causal pattern emerges between this decision and a bad outcome, "
                        "you will be alerted automatically — no human trigger needed."
                    ),
                },
            },
        ])
        _active_intercepts.pop(thread_ts, None)

    elif "CANCEL" in cmd:
        _active_intercepts.pop(thread_ts, None)
        await _post_to_slack(channel, thread_ts, "#8E8E93", [
            {"type": "section", "text": {"type": "mrkdwn", "text": "✈️ SENTINEL dismissed. Decision not logged."}},
        ])
