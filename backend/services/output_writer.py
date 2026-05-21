"""
SENTINEL Output Writer
Writes every agent action to structured files for analysis, debugging, and demo review.

Structure:
  outputs/sentinel/
    sessions/          — full session logs (everything in one file per session)
    decisions/         — individual decision records
    traces/            — causal trace analyses
    warnings/          — early warning events
    asks/              — Q&A interactions
    demo/              — demo scenario snapshots
    latest_*.md        — always-updated latest of each type (for quick review)
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

# ── Directory setup ───────────────────────────────────────────────────────────
BASE = Path("outputs/sentinel")
DIRS = ["sessions", "decisions", "traces", "warnings", "asks", "demo", "actions"]
for d in [BASE] + [BASE / d for d in DIRS]:
    d.mkdir(parents=True, exist_ok=True)

# ── Session log (accumulates everything in one run) ───────────────────────────
_session_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
_session_file = BASE / "sessions" / f"session_{_session_id}.md"
_session_events: List[str] = []


def _log_session(event_type: str, content: str):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"\n---\n## [{ts}] {event_type}\n{content}\n"
    _session_events.append(entry)
    with open(_session_file, "a", encoding="utf-8") as f:
        if len(_session_events) == 1:
            f.write(f"# SENTINEL Session Log\n**Started:** {_session_id}\n")
        f.write(entry)
    # Update latest session pointer
    (BASE / "latest_session.md").write_text(
        f"# Latest Session: {_session_id}\n[Full log]({_session_file})\n\n" +
        "".join(_session_events[-10:]),
        encoding="utf-8"
    )


CURRENCY_KEYS = {"mrr", "arr", "cac", "ltv", "pipeline_value", "burn_rate", "avg_deal_size"}
PERCENT_KEYS  = {"churn_rate", "growth_rate", "conversion_rate", "dvd_revenue_yoy_change"}


def _fmt_metrics(snapshot: Dict) -> str:
    rows = []
    skip = {"captured_at", "sources", "_flags", "raw"}
    for k, v in snapshot.items():
        if k in skip or v is None:
            continue
        try:
            num = float(v)
        except (TypeError, ValueError):
            rows.append(f"| {k} | {v} |")
            continue

        if k in CURRENCY_KEYS:
            rows.append(f"| {k} | ${num:,.0f} |")
        elif k in PERCENT_KEYS or (num < 1.0 and num > 0 and "rate" in k):
            rows.append(f"| {k} | {num:.2%} |")
        elif num > 1000 and k not in {"nps", "active_customers", "support_tickets_7d"}:
            rows.append(f"| {k} | ${num:,.0f} |")
        else:
            rows.append(f"| {k} | {v} |")
    return "\n".join(rows) if rows else "| (no metrics) | — |"


# ── Decision output ───────────────────────────────────────────────────────────
def write_decision(decision: Dict[str, Any], snapshot: Dict[str, Any]) -> str:
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    decision_id = decision.get("decision_id", ts)
    fname = f"decision_{ts}_{decision_id}"

    flags = snapshot.get("_flags", [])
    flags_md = "\n".join(f"- ⚠️ {f}" for f in flags) if flags else "- ✅ No flags at time of decision"
    alts = decision.get("alternatives_considered", [])
    alts_md = "\n".join(f"- {a}" for a in alts) if alts else "- Not recorded"

    md = f"""# ✈️ SENTINEL — Decision Recorded
**Decision ID:** `{decision_id}`
**Logged:** {datetime.now().strftime("%B %d, %Y at %H:%M UTC")}
**Type:** `{decision.get("decision_type", "unknown").upper()}`
**Auto-detected:** {decision.get("auto_detected", False)}
**Detection source:** {decision.get("detection_source", "manual")}

---

## Decision
> {decision.get("decision_text", "")}

**Rationale:** {decision.get("rationale", "Not recorded")}

**Alternatives considered:**
{alts_md}

---

## Metrics Snapshot (Fivetran → BigQuery, captured at decision time)
*Source: {snapshot.get("captured_at", "unknown")}*

| Metric | Value |
|--------|-------|
{_fmt_metrics(snapshot)}

---

## ⚠️ Flags at Time of Decision
{flags_md}

---

## Connected Fivetran Sources
```json
{json.dumps(snapshot.get("sources", {}), indent=2, default=str)}
```

---
*Recorded by SENTINEL. If this decision leads to a bad outcome, SENTINEL can trace the causal chain back to this moment.*
"""

    path = BASE / "decisions" / f"{fname}.md"
    path.write_text(md, encoding="utf-8")
    (BASE / "latest_decision.md").write_text(md, encoding="utf-8")

    json_path = BASE / "decisions" / f"{fname}.json"
    json_path.write_text(
        json.dumps({"decision": decision, "metrics_snapshot": snapshot}, indent=2, default=str),
        encoding="utf-8",
    )

    _log_session("DECISION LOGGED", f"**{decision.get('decision_text', '')}**\n\nMetrics flags: {len(flags)}\nFile: `{path}`")
    return str(path)


# ── Causal trace output ───────────────────────────────────────────────────────
def write_causal_trace(trace: Dict[str, Any]) -> str:
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    trace_id = trace.get("trace_id", ts)
    fname = f"trace_{ts}_{trace_id}"

    chain_md = ""
    for i, event in enumerate(trace.get("causal_chain", []), 1):
        icon = {"decision": "📋", "signal": "⚠️", "outcome": "💥"}.get(event.get("type", ""), "•")
        chain_md += f"{i}. {icon} **{event.get('date', '?')}** — {event.get('title', '')}\n"
        chain_md += f"   > {event.get('description', '')}\n"
        if event.get("metric_value"):
            chain_md += f"   > `{event.get('metric_label', 'value')}: {event.get('metric_value')}`\n"
        chain_md += "\n"

    signals_md = "\n".join(f"- {s}" for s in trace.get("data_that_predicted_outcome", [])) or "- Not available"
    actions_md = "\n".join(f"{i+1}. {a}" for i, a in enumerate(trace.get("recommended_actions", []))) or "1. Review decision log"

    decision_data_md = ""
    for k, v in trace.get("data_available_at_decision", {}).items():
        decision_data_md += f"| {k} | {v} |\n"

    md = f"""# 🔍 SENTINEL — Causal Trace Analysis
**Trace ID:** `{trace.get("trace_id", "unknown")}`
**Outcome:** {trace.get("outcome_description", "")}
**Analyzed:** {datetime.now().strftime("%B %d, %Y at %H:%M")}

---

## Statistical Finding
| Measure | Value |
|---------|-------|
| Pearson r | **{trace.get("pearson_r", 0):.3f}** |
| p-value | {trace.get("p_value", 1):.4f} |
| Days of warning available | **{trace.get("days_of_warning", 0)} days** |
| Earliest signal | {trace.get("earliest_signal_date", "unknown")} |

---

## Summary
{trace.get("narrative", "")}

---

## The Causal Chain

{chain_md}

---

## Data Available at Decision Time (That Predicted the Outcome)

| Signal | Value |
|--------|-------|
{decision_data_md or "| (no data) | — |"}

---

## What the Data Said (That Nobody Listened To)
{signals_md}

---

## What To Do Differently Next Time
{actions_md}

---
*Generated by SENTINEL — The Business Flight Recorder*
"""

    path = BASE / "traces" / f"{fname}.md"
    path.write_text(md, encoding="utf-8")
    (BASE / "latest_causal_trace.md").write_text(md, encoding="utf-8")

    json_path = BASE / "traces" / f"{fname}.json"
    json_path.write_text(json.dumps(trace, indent=2, default=str), encoding="utf-8")

    _log_session(
        "CAUSAL TRACE",
        f"**Outcome:** {trace.get('outcome_description', '')}\n\n"
        f"r = {trace.get('pearson_r', 0):.3f} | {trace.get('days_of_warning', 0)} days warning | "
        f"File: `{path}`"
    )
    return str(path)


# ── Warning output ────────────────────────────────────────────────────────────
def write_warning(warning: Dict[str, Any]) -> str:
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    warning_id = warning.get("warning_id", ts)
    fname = f"warning_{ts}_{warning_id}"

    severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
        warning.get("severity", "medium"), "⚠️"
    )

    md = f"""# {severity_icon} SENTINEL — Early Warning
**Warning ID:** `{warning_id}`
**Severity:** `{warning.get("severity", "unknown").upper()}`
**Fired:** {datetime.now().strftime("%B %d, %Y at %H:%M UTC")}
**Auto-detected:** Yes (pattern matching)

---

## Warning
> {warning.get("message", "")}

---

## Details
| Field | Value |
|-------|-------|
| Trigger metric | `{warning.get("trigger_metric", "unknown")}` |
| Trigger value | {warning.get("trigger_value", 0):.0%} |
| Causal confidence | **{warning.get("causal_confidence", 0):.0%}** |
| Root decision ID | `{warning.get("root_decision_id", "unknown")}` |
| Days since root decision | {warning.get("days_since_decision", "unknown")} days |

---

## Recommended Action
**{warning.get("recommended_action", "Review decision log")}**

---

## Pattern Description
This warning was triggered because current metrics match a pattern that preceded
bad outcomes in {warning.get("causal_confidence", 0):.0%} of historical cases with similar signals.

---
*SENTINEL fired this warning automatically based on pattern matching against the decision history.*
"""

    path = BASE / "warnings" / f"{fname}.md"
    path.write_text(md, encoding="utf-8")
    (BASE / "latest_warning.md").write_text(md, encoding="utf-8")

    json_path = BASE / "warnings" / f"{fname}.json"
    json_path.write_text(json.dumps(warning, indent=2, default=str), encoding="utf-8")

    _log_session(
        f"WARNING FIRED [{warning.get('severity', '?').upper()}]",
        f"**{warning.get('message', '')}**\n\n"
        f"Confidence: {warning.get('causal_confidence', 0):.0%} | "
        f"File: `{path}`"
    )
    return str(path)


# ── Ask output ────────────────────────────────────────────────────────────────
def write_ask(question: str, answer: Dict[str, Any], scenario: Optional[str] = None) -> str:
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    fname = f"ask_{ts}"

    md = f"""# 💬 SENTINEL — Q&A Record
**Asked:** {datetime.now().strftime("%B %d, %Y at %H:%M UTC")}
**Scenario:** {scenario or "live"}

---

## Question
> {question}

---

## SENTINEL's Answer
{answer.get("answer", "")}

---

## Sources
{chr(10).join(f"- {s}" for s in answer.get("sources", [])) or "- Decision log"}

---

## Metadata
| Field | Value |
|-------|-------|
| Confidence | {answer.get("confidence", 0):.0%} |
| Relevant decisions | {", ".join(answer.get("relevant_decision_ids", [])) or "none"} |

---
*Answered by SENTINEL using the decision log and Fivetran data context.*
"""

    path = BASE / "asks" / f"{fname}.md"
    path.write_text(md, encoding="utf-8")
    (BASE / "latest_ask.md").write_text(md, encoding="utf-8")

    json_path = BASE / "asks" / f"{fname}.json"
    json_path.write_text(json.dumps({"question": question, "answer": answer}, indent=2, default=str), encoding="utf-8")

    _log_session("ASK SENTINEL", f"**Q:** {question}\n\n**A:** {answer.get('answer', '')[:200]}...")
    return str(path)


# ── Demo scenario output ──────────────────────────────────────────────────────
def write_demo_load(scenario: str, data: Dict[str, Any]) -> str:
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    fname = f"demo_{scenario}_{ts}"

    meta = data.get("meta", {})
    decisions = data.get("decisions", [])
    warnings = data.get("warnings", [])
    trace = data.get("trace", {})
    snapshot = data.get("snapshot", {})

    md = f"""# 📦 SENTINEL — Demo Scenario Loaded
**Scenario:** {scenario}
**Name:** {meta.get("name", scenario)}
**Loaded:** {datetime.now().strftime("%B %d, %Y at %H:%M UTC")}

---

## Scenario Summary
| Field | Value |
|-------|-------|
| Company | {meta.get("company", "—")} |
| Period | {meta.get("period", "—")} |
| Outcome | {meta.get("outcome", "—")} |
| Days of warning | {meta.get("days_of_warning", "—")} |

**Description:** {meta.get("description", "")}

---

## Decisions Loaded ({len(decisions)})
{chr(10).join(f"- `{d.get('decision_id')}` — {d.get('decision_text', '')} [{d.get('decision_type')}] → {d.get('outcome', '?')}" for d in decisions)}

---

## Active Warnings ({len(warnings)})
{chr(10).join(f"- [{w.get('severity', '?').upper()}] {w.get('message', '')}" for w in warnings)}

---

## Causal Trace Summary
- **Outcome:** {trace.get("outcome_description", "—")}
- **Pearson r:** {trace.get("pearson_r", 0):.3f}
- **Days of warning:** {trace.get("days_of_warning", 0)}
- **Chain length:** {len(trace.get("causal_chain", []))} events

---

## Metrics Snapshot
| Metric | Value |
|--------|-------|
{_fmt_metrics(snapshot)}

---

## Data Flags
{chr(10).join(f"- ⚠️ {f}" for f in snapshot.get("_flags", [])) or "- No flags"}
"""

    path = BASE / "demo" / f"{fname}.md"
    path.write_text(md, encoding="utf-8")
    (BASE / f"latest_demo_{scenario}.md").write_text(md, encoding="utf-8")

    json_path = BASE / "demo" / f"{fname}.json"
    json_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    _log_session(
        f"DEMO LOADED [{scenario.upper()}]",
        f"**{meta.get('name', scenario)}** | {len(decisions)} decisions | "
        f"{len(warnings)} warnings | r={trace.get('pearson_r', 0):.2f} | "
        f"File: `{path}`"
    )
    return str(path)


# ── Autonomous action plan output ────────────────────────────────────────────
def write_action_plan(action: Dict[str, Any]) -> str:
    """Write an autonomous action taken by SENTINEL to a file."""
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    action_id = action.get("action_id", ts)
    fname = f"action_{ts}_{action_id}"

    plan = action.get("action_plan", {})
    actions_md = ""
    for a in plan.get("actions", []):
        actions_md += f"**Step {a.get('step', '?')}** [{a.get('owner', '?')}]: {a.get('action', '')} — *{a.get('deadline', '?')}*\n\n"

    md = f"""# 🤖 SENTINEL — Autonomous Action Taken
**Action ID:** `{action_id}`
**Triggered by:** Warning `{action.get('triggered_by_warning', 'unknown')}`
**Severity:** `{action.get('severity', 'unknown').upper()}`
**Created by:** `{action.get('created_by', 'SENTINEL_MONITOR')}` (autonomous — no human triggered this)
**Created at:** {action.get('created_at', ts)}

---

## What SENTINEL Detected
{plan.get('summary', 'Critical pattern detected — immediate review required')}

---

## Action Plan
**Urgency:** `{plan.get('urgency', '48h')}`

{actions_md or "See action_plan field for details."}

---

## Watch Metric
Monitor **{plan.get('metric_to_watch', 'unknown')}** for recovery.

## Escalate If
{plan.get('escalate_if', 'No improvement within 14 days')}

---
*This action plan was created autonomously by SENTINEL. No human initiated this.*
*SENTINEL detected the pattern, evaluated severity, generated this plan, and logged it.*
"""

    path = BASE / "actions" / f"{fname}.md"
    path.write_text(md, encoding="utf-8")
    (BASE / "latest_action.md").write_text(md, encoding="utf-8")

    json_path = BASE / "actions" / f"{fname}.json"
    json_path.write_text(json.dumps(action, indent=2, default=str), encoding="utf-8")

    _log_session(
        "SENTINEL AUTONOMOUS ACTION",
        f"**Action ID:** {action_id}\n**Summary:** {plan.get('summary', '')}\n"
        f"**Urgency:** {plan.get('urgency', '?')} | File: `{path}`"
    )
    return str(path)


# ── Transcript extract output ─────────────────────────────────────────────────
def write_transcript_extract(transcript: str, decisions: list, source: str = "meeting") -> str:
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    fname = f"transcript_{ts}"

    decisions_md = ""
    for i, d in enumerate(decisions, 1):
        decisions_md += f"### {i}. {d.get('decision_text', '')}\n"
        decisions_md += f"- **Type:** `{d.get('decision_type', 'unknown')}`\n"
        decisions_md += f"- **Rationale:** {d.get('rationale', 'not stated')}\n"
        decisions_md += f"- **Participants:** {', '.join(d.get('participants', [])) or 'not stated'}\n"
        decisions_md += f"- **Confidence:** {d.get('confidence', 0):.0%}\n"
        decisions_md += f"- **Metrics captured:** {len(d.get('metrics_captured', []))} fields\n"
        decisions_md += f"- **Decision ID:** `{d.get('decision_id', '?')}`\n\n"

    md = f"""# 📝 SENTINEL — Transcript Extraction
**Source:** {source}
**Extracted:** {datetime.now().strftime("%B %d, %Y at %H:%M UTC")}
**Decisions found:** {len(decisions)}

---

## Original Transcript
```
{transcript[:2000]}{"..." if len(transcript) > 2000 else ""}
```

---

## Extracted Decisions

{decisions_md or "No decisions extracted."}

---
*Extracted by SENTINEL using Gemini 2.5 Flash. Each decision automatically logged with a Fivetran metrics snapshot.*
"""

    path = BASE / "decisions" / f"{fname}.md"
    path.write_text(md, encoding="utf-8")
    (BASE / "latest_transcript.md").write_text(md, encoding="utf-8")

    json_path = BASE / "decisions" / f"{fname}.json"
    json_path.write_text(
        json.dumps({"source": source, "decisions": decisions, "transcript_preview": transcript[:500]}, indent=2, default=str),
        encoding="utf-8",
    )

    _log_session(
        "TRANSCRIPT EXTRACTED",
        f"**Source:** {source} | **Decisions found:** {len(decisions)}\n\n"
        + "\n".join(f"- {d.get('decision_text', '')}" for d in decisions[:5])
        + f"\nFile: `{path}`"
    )
    return str(path)
