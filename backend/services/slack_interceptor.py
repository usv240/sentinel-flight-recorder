"""
SENTINEL Slack Interceptor

Watches Slack messages for business decisions and intervenes BEFORE they're made.
This is what transforms SENTINEL from a dashboard into an agent that lives inside
the conversation where decisions actually happen.

Flow:
  1. Someone types "let's raise prices 20%" in Slack
  2. Slack sends the message to /api/slack/events (Cloud Run)
  3. SENTINEL detects a decision keyword pattern
  4. Runs precheck engine against live BigQuery data
  5. Posts analysis back to the thread within ~15 seconds
  6. User replies REVIEW → SENTINEL sends safer alternatives
  7. User replies PROCEED → SENTINEL logs the decision in MongoDB

No human triggered any of this. SENTINEL decided to act.
"""

import logging
import re
import os
import httpx
from typing import Optional

log = logging.getLogger("sentinel.interceptor")

# ── Decision keyword patterns ──────────────────────────────────────────────────
# Each entry: list of regex patterns that suggest this decision type is being made
_DECISION_PATTERNS = {
    "pricing": {
        "keywords": [
            r"raise\s+pric", r"increase\s+pric", r"price\s+increase",
            r"pric\w*\s+change", r"\d+\s*%\s+increase", r"increase.*\d+\s*%",
            r"pricing\s+tier", r"new\s+pric", r"adjust.*pric",
            r"bump.*price", r"hike.*price",
        ],
        "type": "pricing",
        "emoji": "💰",
    },
    "hiring": {
        "keywords": [
            r"hire\s+a\b", r"we\s+should\s+hire", r"bring\s+on\s+a",
            r"\bhire\s+\d+", r"head\s*count", r"onboard\s+a",
            r"new\s+engineer", r"senior\s+hire",
        ],
        "type": "hiring",
        "emoji": "👥",
    },
    "product": {
        "keywords": [
            r"remove.*feature", r"kill\s+the\s+feature",
            r"sunset\s+", r"deprecate\s+", r"cut\s+the\s+feature",
            r"eliminate.*feature", r"remove.*from\s+product",
        ],
        "type": "product",
        "emoji": "🚀",
    },
    "strategy": {
        "keywords": [
            r"pivot\s+to", r"enter\s+the\s+market", r"expand\s+into",
            r"shut\s+down\s+the", r"strategic\s+shift",
        ],
        "type": "strategy",
        "emoji": "🎯",
    },
}

# ── State: active intercepts waiting for REVIEW/PROCEED ────────────────────────
# Maps message_ts -> intercept context. In-memory is fine for demo; prod uses MongoDB.
_active_intercepts: dict = {}
_processed_ts: set = set()  # dedup guard


def _detect_decision(text: str) -> Optional[dict]:
    """Return the first matching decision pattern, or None."""
    lower = text.lower()
    for category, config in _DECISION_PATTERNS.items():
        for pattern in config["keywords"]:
            if re.search(pattern, lower):
                return {
                    "category": category,
                    "type": config["type"],
                    "emoji": config["emoji"],
                }
    return None


async def _post_to_slack(channel: str, thread_ts: str, color: str, blocks: list):
    """Post a Block Kit message as a thread reply with a colored sidebar."""
    token = os.getenv("SLACK_BOT_TOKEN", "")
    if not token:
        log.warning("SLACK_BOT_TOKEN not set — skipping post")
        return
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "channel": channel,
                    "thread_ts": thread_ts,
                    "attachments": [{"color": color, "blocks": blocks}],
                },
            )
            data = resp.json()
            if not data.get("ok"):
                log.error(f"Slack API error: {data.get('error')}")
    except Exception as e:
        log.error(f"Slack post failed: {e}")


async def process_message_event(event: dict):
    """
    Main entry point — called from the Slack Events route as a background task.
    Detects decisions, runs precheck, posts analysis.
    """
    text    = event.get("text", "")
    channel = event.get("channel", "")
    ts      = event.get("ts", "")
    thread_ts = event.get("thread_ts", ts)  # root of thread

    if not text or not channel or not ts:
        return

    # Dedup — Slack sometimes sends duplicates
    if ts in _processed_ts:
        return
    _processed_ts.add(ts)
    if len(_processed_ts) > 2000:
        _processed_ts.clear()

    # ── If this is a reply inside an active intercept thread ───────────────────
    if thread_ts in _active_intercepts and ts != thread_ts:
        await _handle_reply(text, channel, thread_ts)
        return

    # ── Detect a new decision ──────────────────────────────────────────────────
    match = _detect_decision(text)
    if not match:
        return

    log.info(f"Intercepted {match['type']} decision in {channel}: {text[:80]}")

    # ── Get live metrics from BigQuery ─────────────────────────────────────────
    snapshot: dict = {}
    try:
        from .bigquery_pipeline import get_real_time_series, get_current_metrics_from_ts
        ts_data = await get_real_time_series("acmesaas")
        if ts_data:
            snapshot = get_current_metrics_from_ts(ts_data)
    except Exception as e:
        log.warning(f"BigQuery snapshot failed (using empty): {e}")

    # ── Run precheck engine ────────────────────────────────────────────────────
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
        return

    # ── Run Bradford Hill for extra credibility ────────────────────────────────
    bh_score = None
    bh_strength = None
    try:
        from .bradford_hill import score_bradford_hill
        from .causal_tracer import _run_causal_battery, _DEMO_TIME_SERIES
        ts_demo = _DEMO_TIME_SERIES.get("acmesaas", {})
        if ts_demo:
            ca = _run_causal_battery(
                ts_demo.get("churn_values", []),
                ts_demo.get("nps_values", []),
                ts_demo.get("churn_decision_index", 2),
                "churn_rate",
            )
            bh = score_bradford_hill(
                causal_analysis=ca,
                root_decision={"decision_type": match["type"], "logged_at": "now"},
                causal_chain=[],
                data_signals=precheck.get("blocking_conditions", []),
                days_of_warning=0,
            )
            bh_score = bh.get("total_score", 0)
            bh_strength = bh.get("causal_strength", "")
    except Exception:
        pass

    # ── Store for REVIEW/PROCEED handling ──────────────────────────────────────
    _active_intercepts[ts] = {
        "precheck":      precheck,
        "decision_text": text,
        "decision_type": match["type"],
        "channel":       channel,
        "snapshot":      snapshot,
    }

    # ── Build and post the interception message ─────────────────────────────────
    await _post_interception(channel, ts, match, precheck, bh_score, bh_strength)


async def _post_interception(
    channel: str,
    thread_ts: str,
    match: dict,
    precheck: dict,
    bh_score: Optional[float],
    bh_strength: Optional[str],
):
    risk_level  = precheck.get("risk_level", "low")
    risk_score  = precheck.get("risk_score", 0)
    conditions  = precheck.get("blocking_conditions", [])
    patterns    = precheck.get("pattern_matches", [])
    gemini      = precheck.get("gemini_advice", "")
    arr_impact  = precheck.get("estimated_arr_impact", {})
    metrics     = precheck.get("current_metrics", {})

    color = {"high": "#FF3B30", "medium": "#FF9500", "low": "#30D158"}.get(risk_level, "#8E8E93")
    icon  = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(risk_level, "⚪")

    # Metrics field
    nps   = metrics.get("nps")
    churn = metrics.get("churn_rate")
    metrics_lines = []
    if nps is not None:
        flag = " ⚠️ below safe threshold (40)" if float(nps) < 40 else " ✅"
        metrics_lines.append(f"• NPS: *{float(nps):.0f}*{flag}")
    if churn is not None:
        flag = " ⚠️ above warning threshold (8%)" if float(churn) > 0.08 else " ✅"
        metrics_lines.append(f"• Churn: *{float(churn):.1%}*{flag}")
    metrics_text = "\n".join(metrics_lines) or "No live metrics"

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"{match['emoji']}  *SENTINEL intercepted a potential "
                    f"{match['type'].upper()} decision*\n"
                    f"{icon}  Risk level: *{risk_level.upper()}* — {risk_score:.0%} risk score"
                ),
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Live Metrics (Fivetran → BigQuery)*\n{metrics_text}"},
                {
                    "type": "mrkdwn",
                    "text": (
                        f"*Bradford Hill Causal Score*\n"
                        f"{f'{bh_score:.0%} ({bh_strength} causal evidence)' if bh_score else 'Running...'}"
                    ),
                },
            ],
        },
    ]

    if patterns:
        p = patterns[0]
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Historical pattern match:* "
                    f"{p['historical_failure_rate']:.0%} of {match['type']} decisions under these "
                    f"conditions led to *{p['outcome']}* (n={p['n_examples']} companies)"
                ),
            },
        })

    if arr_impact.get("low") and risk_level in ("high", "medium"):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Estimated ARR at risk:* ${abs(arr_impact['low']):,} – ${abs(arr_impact['high']):,}",
            },
        })

    if gemini:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Gemini 2.5 Flash analysis:*\n_{gemini}_"},
        })

    if risk_level in ("high", "medium"):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Reply *`REVIEW`* to see safer alternatives  ·  Reply *`PROCEED`* to log this decision with risk acknowledged",
            },
        })
    else:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "✅ Low-risk given current metrics. Reply *`LOG`* to record it in SENTINEL.",
            },
        })

    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": "✈️ *SENTINEL* — autonomous interception · no human triggered this · data: Fivetran → BigQuery → Gemini",
        }],
    })

    await _post_to_slack(channel, thread_ts, color, blocks)


async def _handle_reply(text: str, channel: str, thread_ts: str):
    """Handle REVIEW / PROCEED / LOG replies in an intercepted thread."""
    cmd = text.strip().upper()
    intercept = _active_intercepts.get(thread_ts)
    if not intercept:
        return

    if "REVIEW" in cmd:
        precheck = intercept.get("precheck", {})
        alts = precheck.get("alternative_recommendations", [])
        safe = precheck.get("safe_to_proceed_when", [])

        alt_lines = "\n".join(f"{i+1}. {a}" for i, a in enumerate(alts[:3])) or "No alternatives available."
        safe_lines = "\n".join(f"• {s}" for s in safe[:3])

        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "✈️ *SENTINEL: Safer Alternatives*"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": alt_lines}},
        ]
        if safe_lines:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Safe to proceed when:*\n{safe_lines}"},
            })
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "Reply *`PROCEED`* when ready to log, or *`CANCEL`* to dismiss."}],
        })
        await _post_to_slack(channel, thread_ts, "#007AFF", blocks)

    elif any(w in cmd for w in ("PROCEED", "LOG", "YES")):
        decision_id = "UNKNOWN"
        try:
            from ..db import mongodb
            decision_id = await mongodb.insert_decision({
                "decision_text":       intercept.get("decision_text", ""),
                "decision_type":       intercept.get("decision_type", "unknown"),
                "source":              "slack_interception",
                "against_agent_advice": intercept.get("precheck", {}).get("risk_level") in ("high", "medium"),
                "risk_level_at_log":   intercept.get("precheck", {}).get("risk_level", "unknown"),
                "metrics_snapshot":    intercept.get("snapshot", {}),
                "rationale":           "Logged via Slack after SENTINEL interception",
            })
        except Exception as e:
            log.error(f"Failed to log intercepted decision: {e}")

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"✅ *Decision logged* — ID: `{decision_id}`\n"
                        "SENTINEL will monitor metrics for the next 90 days. "
                        "If a causal pattern emerges, you'll be alerted automatically."
                    ),
                },
            },
        ]
        await _post_to_slack(channel, thread_ts, "#30D158", blocks)
        _active_intercepts.pop(thread_ts, None)

    elif "CANCEL" in cmd:
        _active_intercepts.pop(thread_ts, None)
        await _post_to_slack(channel, thread_ts, "#8E8E93", [
            {"type": "section", "text": {"type": "mrkdwn", "text": "✈️ SENTINEL dismissed. Decision not logged."}}
        ])
