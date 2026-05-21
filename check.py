"""
SENTINEL Health Check
Run with: python check.py

Shows a complete status of all outputs, endpoints, and data quality.
Use this to verify everything is working after a server restart.
"""

import os, json, sys, asyncio, datetime
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path("outputs/sentinel")
import os as _os
API = f"http://localhost:{_os.getenv('APP_PORT', '8080')}"

# ── Colors ────────────────────────────────────────────────────────────────────
OK    = "\033[92mOK\033[0m"
WARN  = "\033[93m!!\033[0m"
FAIL  = "\033[91mXX\033[0m"
BOLD  = "\033[1m"
RESET = "\033[0m"


def section(title):
    print(f"\n{BOLD}{'-'*50}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'-'*50}{RESET}")


def row(icon, label, value=""):
    print(f"  {icon}  {label:<35} {value}")


# ── 1. Output files ───────────────────────────────────────────────────────────
def check_outputs():
    section("Output Files")
    categories = {
        "decisions": ("*.json", "logged decisions"),
        "warnings":  ("*.json", "warnings fired"),
        "asks":      ("*.json", "Q&A sessions"),
        "traces":    ("*.json", "causal traces"),
        "actions":   ("*.json", "autonomous actions"),
        "sessions":  ("*.md",   "session logs"),
        "demo":      ("*.json", "demo loads"),
    }

    for cat, (pattern, label) in categories.items():
        folder = BASE / cat
        if not folder.exists():
            row(FAIL, f"{cat} ({label})", "folder missing")
            continue
        files = list(folder.glob(pattern))
        if not files:
            row(WARN, f"{cat} ({label})", "0 files — server may not have run yet")
            continue

        latest = max(files, key=os.path.getmtime)
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(latest))
        age_hours = (datetime.datetime.now() - mtime).total_seconds() / 3600
        age_str = f"{age_hours:.0f}h ago" if age_hours > 1 else "< 1h ago"

        icon = OK if age_hours < 2 else WARN if age_hours < 24 else FAIL
        row(icon, f"{cat} ({label})", f"{len(files)} files | latest {age_str}")

        # Spot-check latest file for data quality
        try:
            data = json.loads(latest.read_text(encoding="utf-8"))
            if cat == "warnings":
                conf = data.get("causal_confidence", 0)
                if conf == 0:
                    row(WARN, "  └ causal_confidence", "0 — bug (should be > 0)")
                else:
                    row(OK, "  └ causal_confidence", f"{conf:.0%}")
            elif cat == "traces":
                verdict = data.get("causal_analysis", {}).get("verdict", "?")
                source = data.get("data_source", "unknown")
                row(OK if source == "bigquery_live" else WARN,
                    "  └ data_source + verdict", f"{source} | {verdict}")
            elif cat == "actions":
                urgency = data.get("action_plan", {}).get("urgency", "?")
                row(OK, "  └ autonomous action", f"urgency={urgency}")
        except Exception:
            pass


# ── 2. API endpoints ──────────────────────────────────────────────────────────
def check_endpoints():
    section("API Endpoints")
    try:
        import requests
    except ImportError:
        row(WARN, "requests not installed", "pip install requests")
        return

    endpoints = [
        ("GET",  "/api/health",           "Health check"),
        ("GET",  "/api/monitor/status",   "Monitor status"),
        ("GET",  "/api/connectors/list",  "Fivetran connectors (MCP)"),
        ("GET",  "/api/warnings/active",  "Active warnings"),
        ("GET",  "/api/warnings/actions", "Autonomous actions"),
        ("GET",  "/api/decisions/list",   "Decision log"),
        ("GET",  "/api/decisions/snapshot", "Live metrics snapshot"),
        ("GET",  "/api/tool-calls/recent", "MCP call log"),
        ("POST", "/api/mcp",              "MCP endpoint (Agent Studio)"),
    ]

    for method, path, label in endpoints:
        try:
            if method == "POST":
                r = requests.post(
                    API + path, timeout=5,
                    json={"jsonrpc": "2.0", "method": "tools/list", "id": 1, "params": {}}
                )
            else:
                r = requests.get(API + path, timeout=5)

            if r.status_code == 200:
                data = r.json()
                # Extra checks
                note = ""
                if path == "/api/health":
                    note = f"mongodb={data.get('mongodb')} | warnings={data.get('monitor',{}).get('warnings_detected',0)}"
                elif path == "/api/connectors/list":
                    note = f"{data.get('count', 0)} connectors"
                elif path == "/api/warnings/active":
                    note = f"{len(data.get('warnings', []))} active"
                elif path == "/api/warnings/actions":
                    note = f"{data.get('count', 0)} actions taken"
                elif path == "/api/decisions/list":
                    note = f"{len(data.get('decisions', []))} decisions"
                elif path == "/api/mcp":
                    note = f"{len(data.get('result', {}).get('tools', []))} tools"
                row(OK, f"{method} {path}", note or "200 OK")
            else:
                row(FAIL, f"{method} {path}", f"{r.status_code}")
        except requests.exceptions.ConnectionError:
            row(FAIL, f"{method} {path}", "server not running on :8100")
            return  # No point testing rest
        except Exception as e:
            row(WARN, f"{method} {path}", str(e)[:40])


# ── 3. BigQuery pipeline ──────────────────────────────────────────────────────
async def check_bigquery():
    section("BigQuery Pipeline (Real Data)")
    try:
        from dotenv import load_dotenv
        load_dotenv(".env")
        from backend.services.bigquery_pipeline import get_real_time_series
        ts = await get_real_time_series("acmesaas")
        if ts:
            import os; proj = os.getenv("GOOGLE_PROJECT_ID","not set")
        row(OK, "BigQuery connection",          f"project={proj}")
            row(OK, "acmesaas_metrics rows",        f"{ts['n_rows']} rows ({ts['dates'][0]} → {ts['dates'][-1]})")
            row(OK, "Decision date in data",        f"{ts['decision_date']} (index {ts['decision_index']})")
            row(OK, "NPS at decision",              f"{ts['nps'][ts['decision_index']]}")
            row(OK, "Churn at decision",            f"{ts['churn_rate'][ts['decision_index']]:.1%}")
            row(OK, "Churn at outcome (latest)",    f"{ts['churn_rate'][-1]:.1%} (+{(ts['churn_rate'][-1]/ts['churn_rate'][ts['decision_index']]-1):.0%})")
        else:
            row(FAIL, "BigQuery query",             "returned no data")
    except Exception as e:
        row(FAIL, "BigQuery connection",            str(e)[:60])


# ── 4. Causal battery on real data ────────────────────────────────────────────
async def check_causal():
    section("Causal Inference Battery (Real BigQuery Data)")
    try:
        from dotenv import load_dotenv
        load_dotenv(".env")
        from backend.services.bigquery_pipeline import get_real_time_series
        from backend.services.causal_tracer import _run_causal_battery
        ts = await get_real_time_series("acmesaas")
        if not ts:
            row(FAIL, "No data", "BigQuery unavailable")
            return
        ca = _run_causal_battery(ts["churn_rate"], ts["nps"], ts["decision_index"], "churn_rate")
        g = ca["granger"]
        its = ca["interrupted_time_series"]
        mwu = ca["mann_whitney"]
        v = ca["verdict"]
        sig = ca["significant_tests"]

        row(OK if g["significant"] else WARN,
            "Granger causality (NPS→churn)",
            f"p={g.get('p_value','?')} | {'significant' if g['significant'] else 'not significant'}")
        row(OK if its["significant"] else WARN,
            "Interrupted Time Series",
            f"slope {its.get('slope_before','?'):.4f}→{its.get('slope_after','?'):.4f} | {'sig' if its['significant'] else 'not sig'}")
        row(OK if mwu["significant"] else WARN,
            "Mann-Whitney U pre/post",
            f"p={mwu.get('p_value','?')} | {'significant' if mwu['significant'] else 'not significant'}")
        row(OK if sig >= 2 else WARN,
            "Overall verdict",
            f"{v} ({sig}/3 tests significant)")
        row(OK,
            "Effect size",
            f"{ca.get('effect_size_pct','?')}% change in churn pre→post decision")
    except Exception as e:
        row(FAIL, "Causal battery", str(e)[:60])


# ── 5. Slack ──────────────────────────────────────────────────────────────────
def check_slack():
    section("Slack Integration")
    from dotenv import load_dotenv
    load_dotenv(".env")
    token = os.getenv("SLACK_BOT_TOKEN", "")
    channel = os.getenv("SLACK_CHANNEL_ID", "")
    row(OK if token else FAIL, "SLACK_BOT_TOKEN",    "set" if token else "missing — add to .env")
    row(OK if channel else FAIL, "SLACK_CHANNEL_ID", channel if channel else "missing — add to .env")
    if token and channel:
        row(OK, "Slack configured",                  "alerts will fire on critical warnings")


# ── 6. New features (post-restart) ────────────────────────────────────────────
def check_new_features():
    section("New Features Status")
    try:
        import requests
        # Precheck endpoint
        r = requests.post(f"{API}/api/decisions/precheck", timeout=5, json={
            "decision_text": "Raise prices 20%", "decision_type": "pricing"
        })
        if r.status_code == 200:
            data = r.json()
            row(OK, "Pre-decision precheck",        f"risk={data.get('risk_level')} ({data.get('risk_score',0):.0%})")
        else:
            row(FAIL, "Pre-decision precheck",      f"{r.status_code} — restart server")

        # Custom analysis endpoint
        r2 = requests.post(f"{API}/api/custom/analyze", timeout=15, json={
            "decision_text": "Raise prices", "decision_date": "2026-06-01",
            "churn_at_decision": 0.09, "churn_now": 0.14,
            "nps_at_decision": 31, "nps_now": 24,
        })
        if r2.status_code == 200:
            data2 = r2.json()
            row(OK, "Custom analysis (Your Data)",  f"verdict={data2.get('verdict')}")
        else:
            row(WARN, "Custom analysis",            f"{r2.status_code}")

        # Agent chat
        r3 = requests.post(f"{API}/api/agent/chat", timeout=30, json={
            "message": "What is SENTINEL? One sentence."
        })
        if r3.status_code == 200:
            row(OK, "ADK agent (/api/agent/chat)",  "responding")
        else:
            row(FAIL, "ADK agent",                  f"{r3.status_code} — may need restart")

    except requests.exceptions.ConnectionError:
        row(WARN, "New features",                   "server not running — start with: uvicorn backend.main:app --port 8100")
    except Exception as e:
        row(WARN, "New features check",             str(e)[:50])


# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    print(f"\n{BOLD}SENTINEL Health Check — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}{RESET}")

    check_outputs()
    check_endpoints()
    await check_bigquery()
    await check_causal()
    check_slack()
    check_new_features()

    section("Summary")
    print("  Run this anytime: python check.py")
    port = _os.getenv('APP_PORT', '8080')
    print(f"  Restart server:   uvicorn backend.main:app --host 0.0.0.0 --port {port}")
    print(f"  Trigger monitor:  curl -X POST http://localhost:{port}/api/monitor/run")
    print()


if __name__ == "__main__":
    asyncio.run(main())
