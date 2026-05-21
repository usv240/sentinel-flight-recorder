"""
SENTINEL Slack Integration

Sends real Slack notifications when SENTINEL takes autonomous actions.
This is the visible "agent action" — not a draft email in a database,
an actual message arriving in the team's Slack channel.

Required env vars:
  SLACK_BOT_TOKEN   — xoxb-... (Bot User OAuth Token)
  SLACK_CHANNEL_ID  — C... (channel to post alerts to, e.g. #sentinel-alerts)

If not configured, all functions are no-ops with a logged warning.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional

log = logging.getLogger("sentinel.slack")

try:
    import httpx
    _HTTPX = True
except ImportError:
    _HTTPX = False


def _token() -> str:
    return os.getenv("SLACK_BOT_TOKEN", "")


def _channel() -> str:
    return os.getenv("SLACK_CHANNEL_ID", "")


def is_configured() -> bool:
    return bool(_token() and _channel())


async def send_message(
    text: str,
    blocks: Optional[list] = None,
    color: Optional[str] = None,
) -> dict:
    """
    Post a message to the configured SENTINEL Slack channel.
    color: hex string like '#FF3B30' — adds a colored left border (attachment style).
    """
    if not is_configured():
        log.warning("Slack not configured — set SLACK_BOT_TOKEN and SLACK_CHANNEL_ID")
        return {"ok": False, "error": "not_configured"}

    if not _HTTPX:
        log.error("httpx not installed — cannot send Slack message")
        return {"ok": False, "error": "httpx_missing"}

    payload: dict = {"channel": _channel(), "text": text}

    if blocks and color:
        # Use attachment with color border — same pattern as Datadog/PagerDuty
        payload["attachments"] = [{"color": color, "blocks": blocks}]
    elif blocks:
        payload["blocks"] = blocks

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {_token()}",
                "Content-Type": "application/json",
            },
            content=json.dumps(payload),
        )
        result = resp.json()
        if not result.get("ok"):
            log.error(f"Slack API error: {result.get('error')}")
        return result


async def send_warning_alert(warning: dict, action_plan: dict, snapshot: dict) -> dict:
    """Send a structured Slack alert for autonomous critical warnings."""
    severity = warning.get("severity", "high").upper()
    message = warning.get("message", "Critical pattern detected")
    trigger_metric = warning.get("trigger_metric", "unknown")
    plan = action_plan or {}
    urgency = plan.get("urgency", "48h")

    mrr = snapshot.get("mrr", 0)
    nps = snapshot.get("nps", "?")
    churn = snapshot.get("churn_rate", 0)
    try:
        churn_pct = f"{float(churn):.1%}"
    except Exception:
        churn_pct = str(churn)

    # Color-coded left border by severity — same pattern as PagerDuty/Datadog
    border_color = {"CRITICAL": "#FF3B30", "HIGH": "#FF9500", "MEDIUM": "#FFCC00"}.get(severity, "#8E8E93")
    urgency_label = {
        "immediate": "Immediate action required",
        "48h": "Action required within 48h",
        "7d": "Review within 7 days",
    }.get(urgency, urgency)

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"⚠ *SENTINEL Alert — {severity}*\n{message}"
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Metric*\n{trigger_metric}"},
                {"type": "mrkdwn", "text": f"*Urgency*\n{urgency_label}"},
                {"type": "mrkdwn", "text": f"*MRR*\n${mrr:,.0f}"},
                {"type": "mrkdwn", "text": f"*NPS*\n{nps}"},
                {"type": "mrkdwn", "text": f"*Churn*\n{churn_pct}"},
                {"type": "mrkdwn", "text": f"*Detected*\n{datetime.now().strftime('%b %d, %H:%M UTC')}"},
            ]
        },
    ]

    if plan.get("actions"):
        steps = "\n".join(
            f"{a['step']}. *{a['owner']}:* {a['action']} _({a['deadline']})_"
            for a in plan["actions"][:3]
        )
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Recommended actions*\n{steps}"}
        })

    if plan.get("summary"):
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": plan["summary"]}]
        })

    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": "SENTINEL — autonomous monitoring cycle — no human triggered this"}]
    })

    fallback = f"SENTINEL [{severity}]: {message}"
    return await send_message(fallback, blocks, color=border_color)


async def send_precheck_alert(
    decision_text: str,
    risk_level: str,
    risk_score: float,
    blocking_conditions: list,
    alternatives: list,
    snapshot: dict,
) -> dict:
    """Send alert when a high-risk decision is logged despite SENTINEL's warning."""
    mrr = snapshot.get("mrr", 0)

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*High-Risk Decision Logged*\n"
                    f"_{decision_text}_\n\n"
                    f"Risk score: *{risk_score:.0%}* — decision-maker acknowledged the risk and proceeded."
                )
            }
        },
        {"type": "divider"},
    ]

    if blocking_conditions:
        conds = "\n".join(f"• {c}" for c in blocking_conditions[:3])
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*SENTINEL flagged*\n{conds}"}
        })

    if alternatives:
        alts = "\n".join(f"• {a}" for a in alternatives[:2])
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Safer alternatives (not taken)*\n{alts}"}
        })

    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": f"MRR ${mrr:,.0f} — SENTINEL will monitor this decision every 30 minutes"
        }]
    })

    fallback = f"High-Risk Decision Logged: '{decision_text[:80]}' — Risk {risk_score:.0%}"
    return await send_message(fallback, blocks, color="#FF9500")
