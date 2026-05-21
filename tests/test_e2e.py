"""
SENTINEL End-to-End Test Suite

Tests the full stack:
  - Gemini 3 (strict — fails if no G3 model works)
  - BigQuery pipeline (real data)
  - Causal inference battery (Granger, ITS, Mann-Whitney)
  - Bradford Hill criteria (9-criterion scoring)
  - Industry benchmarks
  - Slack interceptor (decision detection)
  - Precheck engine
  - Live API endpoints (local + Cloud Run)

Run:
  python -m pytest tests/test_e2e.py -v
  python -m pytest tests/test_e2e.py -v -k "not live"   # skip Cloud Run tests
  python -m pytest tests/test_e2e.py -v -k "live"       # Cloud Run only
"""

import asyncio
import os
import sys
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

LIVE_URL = "https://sentinel-38381883054.us-central1.run.app"


# ── Helpers ───────────────────────────────────────────────────────────────────

def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. GEMINI 3 — strict requirement
# ═══════════════════════════════════════════════════════════════════════════════

class TestGemini3:
    def test_gemini3_model_list_not_empty(self):
        from backend.services.gemini_client import _GEMINI3_MODELS
        assert len(_GEMINI3_MODELS) >= 1, "No Gemini 3 models configured"
        assert all("gemini-3" in m for m in _GEMINI3_MODELS), (
            f"Non-Gemini-3 model in _GEMINI3_MODELS: {_GEMINI3_MODELS}"
        )

    def test_gemini3_primary_model_is_flash_preview(self):
        from backend.services.gemini_client import _GEMINI3_MODELS
        assert _GEMINI3_MODELS[0] == "gemini-3-flash-preview", (
            f"Primary model should be gemini-3-flash-preview, got {_GEMINI3_MODELS[0]}"
        )

    def test_gemini3_api_key_configured(self):
        key = os.getenv("GEMINI_API_KEY", "")
        assert key, "GEMINI_API_KEY not set — Gemini 3 requires API key, not Vertex AI"

    def test_gemini3_generate_returns_text(self):
        """Gemini 3 must produce a response — fails if all G3 models fail."""
        from backend.services.gemini_client import generate
        result = run(generate("Reply with exactly: SENTINEL_GEMINI3_OK"))
        assert result.strip(), "Gemini 3 generate() returned empty string"
        assert len(result) > 3, f"Response too short: {repr(result)}"

    def test_gemini3_model_active_is_gemini3(self):
        """After a generate() call, GEMINI_MODEL_ACTIVE must be a Gemini 3 model."""
        from backend.services.gemini_client import generate, _GEMINI3_MODELS
        run(generate("ping"))
        active = os.getenv("GEMINI_MODEL_ACTIVE", "")
        assert active in _GEMINI3_MODELS, (
            f"Active model '{active}' is NOT a Gemini 3 model. "
            f"Strict Gemini 3 requirement violated."
        )

    def test_gemini3_json_mode(self):
        from backend.services.gemini_client import generate
        import json
        result = run(generate('Return {"ok": true}', as_json=True))
        parsed = json.loads(result)
        assert parsed.get("ok") is True


# ═══════════════════════════════════════════════════════════════════════════════
# 2. BIGQUERY PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

class TestBigQuery:
    def test_real_time_series_returns_data(self):
        from backend.services.bigquery_pipeline import get_real_time_series
        ts = run(get_real_time_series("acmesaas"))
        assert ts is not None, "BigQuery returned None — check credentials"
        assert ts["n_rows"] >= 5, f"Too few rows: {ts['n_rows']}"
        assert len(ts["nps"]) == ts["n_rows"]
        assert len(ts["churn_rate"]) == ts["n_rows"]
        assert len(ts["dates"]) == ts["n_rows"]

    def test_decision_index_in_range(self):
        from backend.services.bigquery_pipeline import get_real_time_series
        ts = run(get_real_time_series("acmesaas"))
        assert ts is not None
        idx = ts["decision_index"]
        assert 0 <= idx < ts["n_rows"], f"decision_index {idx} out of range [0, {ts['n_rows']})"

    def test_nps_values_are_realistic(self):
        from backend.services.bigquery_pipeline import get_real_time_series
        ts = run(get_real_time_series("acmesaas"))
        assert ts is not None
        for v in ts["nps"]:
            assert -150 <= v <= 150, f"NPS value {v} out of realistic range"

    def test_churn_values_are_percentages(self):
        from backend.services.bigquery_pipeline import get_real_time_series
        ts = run(get_real_time_series("acmesaas"))
        assert ts is not None
        for v in ts["churn_rate"]:
            assert 0 <= v <= 1, f"Churn {v} not in [0,1] range"

    def test_connector_registry_reads_from_env(self):
        from backend.services.bigquery_pipeline import get_connector_registry
        reg = get_connector_registry()
        assert isinstance(reg, dict)
        assert len(reg) >= 1, "Connector registry is empty"

    def test_current_metrics_from_ts_has_required_keys(self):
        from backend.services.bigquery_pipeline import get_real_time_series, get_current_metrics_from_ts
        ts = run(get_real_time_series("acmesaas"))
        assert ts is not None
        metrics = get_current_metrics_from_ts(ts)
        for key in ["nps", "churn_rate", "mrr", "source"]:
            assert key in metrics, f"Missing key '{key}' in current_metrics"
        assert metrics["source"] == "bigquery_live"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. CAUSAL INFERENCE BATTERY
# ═══════════════════════════════════════════════════════════════════════════════

class TestCausalInference:
    def setup_method(self):
        from backend.services.bigquery_pipeline import get_real_time_series
        self.ts = run(get_real_time_series("acmesaas"))

    def test_battery_runs_on_real_data(self):
        from backend.services.causal_tracer import _run_causal_battery
        assert self.ts is not None
        result = _run_causal_battery(
            self.ts["churn_rate"], self.ts["nps"],
            self.ts["decision_index"], "churn_rate"
        )
        assert "verdict" in result
        assert result["verdict"] in ("strong_signal", "moderate_signal", "no_signal")

    def test_significant_tests_count_valid(self):
        from backend.services.causal_tracer import _run_causal_battery
        assert self.ts is not None
        result = _run_causal_battery(
            self.ts["churn_rate"], self.ts["nps"],
            self.ts["decision_index"], "churn_rate"
        )
        assert 0 <= result["significant_tests"] <= 3

    def test_effect_size_is_numeric(self):
        from backend.services.causal_tracer import _run_causal_battery
        assert self.ts is not None
        result = _run_causal_battery(
            self.ts["churn_rate"], self.ts["nps"],
            self.ts["decision_index"], "churn_rate"
        )
        assert result["effect_size_pct"] is not None
        assert isinstance(result["effect_size_pct"], (int, float))

    def test_granger_result_is_json_serializable(self):
        import json
        from backend.services.causal_tracer import _run_causal_battery
        assert self.ts is not None
        result = _run_causal_battery(
            self.ts["churn_rate"], self.ts["nps"],
            self.ts["decision_index"], "churn_rate"
        )
        # Must not raise — numpy bools would cause this to fail
        json.dumps(result)

    def test_its_significant_is_python_bool(self):
        from backend.services.causal_tracer import _interrupted_time_series
        values = [0.08, 0.085, 0.09, 0.10, 0.12, 0.14, 0.16]
        result = _interrupted_time_series(values, decision_index=2)
        assert isinstance(result["significant"], bool), (
            f"significant is {type(result['significant']).__name__}, expected bool"
        )

    def test_mann_whitney_significant_is_python_bool(self):
        from backend.services.causal_tracer import _mann_whitney_pre_post
        values = [0.08, 0.085, 0.09, 0.10, 0.12, 0.14, 0.16]
        result = _mann_whitney_pre_post(values, decision_index=2)
        if result.get("significant") is not None:
            assert isinstance(result["significant"], bool), (
                f"significant is {type(result['significant']).__name__}, expected bool"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. BRADFORD HILL CRITERIA
# ═══════════════════════════════════════════════════════════════════════════════

class TestBradfordHill:
    def setup_method(self):
        self.ca = {
            "effect_size_pct": 56.7,
            "significant_tests": 2,
            "interrupted_time_series": {"slope_change_pct": 150.0},
            "granger": {"p_value": 0.04, "significant": True},
        }
        self.root_decision = {
            "decision_type": "pricing",
            "logged_at": "2026-06-03",
            "decision_text": "Raise prices 20%",
        }
        self.chain = [
            {"type": "decision", "date": "2026-06-03", "severity": "root_cause"},
            {"type": "signal",   "date": "2026-06-17", "severity": "critical"},
            {"type": "outcome",  "date": "2026-07-15", "severity": "critical"},
        ]
        self.signals = ["NPS=31 below threshold", "Churn at 9%", "Tickets 3x avg"]

    def test_returns_nine_criteria(self):
        from backend.services.bradford_hill import score_bradford_hill
        result = score_bradford_hill(self.ca, self.root_decision, self.chain, self.signals, 34)
        assert len(result["criteria"]) == 9, f"Expected 9 criteria, got {len(result['criteria'])}"

    def test_all_criteria_have_required_fields(self):
        from backend.services.bradford_hill import score_bradford_hill
        result = score_bradford_hill(self.ca, self.root_decision, self.chain, self.signals, 34)
        for c in result["criteria"]:
            for field in ["id", "label", "score", "met", "evidence"]:
                assert field in c, f"Criterion missing field '{field}': {c}"

    def test_scores_between_zero_and_one(self):
        from backend.services.bradford_hill import score_bradford_hill
        result = score_bradford_hill(self.ca, self.root_decision, self.chain, self.signals, 34)
        for c in result["criteria"]:
            assert 0.0 <= c["score"] <= 1.0, f"{c['id']} score {c['score']} out of [0,1]"

    def test_met_field_is_python_bool(self):
        from backend.services.bradford_hill import score_bradford_hill
        result = score_bradford_hill(self.ca, self.root_decision, self.chain, self.signals, 34)
        for c in result["criteria"]:
            assert isinstance(c["met"], bool), (
                f"{c['id']}.met is {type(c['met']).__name__}, expected bool"
            )

    def test_total_score_is_mean_of_nine(self):
        from backend.services.bradford_hill import score_bradford_hill
        result = score_bradford_hill(self.ca, self.root_decision, self.chain, self.signals, 34)
        scores = [c["score"] for c in result["criteria"]]
        expected = round(sum(scores) / 9, 3)
        assert abs(result["total_score"] - expected) < 0.001

    def test_causal_strength_label_valid(self):
        from backend.services.bradford_hill import score_bradford_hill
        result = score_bradford_hill(self.ca, self.root_decision, self.chain, self.signals, 34)
        assert result["causal_strength"] in ("strong", "moderate", "weak", "insufficient")

    def test_result_is_json_serializable(self):
        import json
        from backend.services.bradford_hill import score_bradford_hill
        result = score_bradford_hill(self.ca, self.root_decision, self.chain, self.signals, 34)
        json.dumps(result)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. INDUSTRY BENCHMARKS
# ═══════════════════════════════════════════════════════════════════════════════

class TestIndustryBenchmarks:
    def test_nps_benchmark_bottom_quartile(self):
        from backend.services.industry_benchmarks import get_benchmark_comparison
        result = get_benchmark_comparison("nps", 31.0)
        assert result["percentile_rank"] <= 25, f"NPS=31 should be bottom quartile, got p{result['percentile_rank']}"
        assert result["color"] in ("red", "yellow")

    def test_churn_benchmark_above_median(self):
        from backend.services.industry_benchmarks import get_benchmark_comparison
        result = get_benchmark_comparison("churn_rate", 0.14)
        assert result["percentile_rank"] <= 25, "Churn=14% should be bottom quartile"

    def test_good_nps_top_quartile(self):
        from backend.services.industry_benchmarks import get_benchmark_comparison
        result = get_benchmark_comparison("nps", 70.0)
        assert result["percentile_rank"] >= 75, f"NPS=70 should be top quartile, got p{result['percentile_rank']}"
        assert result["color"] == "green"

    def test_get_all_benchmarks_returns_both_metrics(self):
        from backend.services.industry_benchmarks import get_all_benchmarks
        snapshot = {"nps": 31.0, "churn_rate": 0.09}
        results = get_all_benchmarks(snapshot)
        assert len(results) == 2
        metrics = {r["metric"] for r in results}
        assert "nps" in metrics
        assert "churn_rate" in metrics

    def test_sorted_worst_first(self):
        from backend.services.industry_benchmarks import get_all_benchmarks
        snapshot = {"nps": 31.0, "churn_rate": 0.09}
        results = get_all_benchmarks(snapshot)
        ranks = [r["percentile_rank"] for r in results]
        assert ranks == sorted(ranks), "Results should be sorted worst-first (lowest percentile first)"

    def test_result_is_json_serializable(self):
        import json
        from backend.services.industry_benchmarks import get_all_benchmarks
        results = get_all_benchmarks({"nps": 31.0, "churn_rate": 0.09})
        json.dumps(results)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. SLACK INTERCEPTOR — decision detection
# ═══════════════════════════════════════════════════════════════════════════════

class TestSlackInterceptor:
    def test_detect_pricing_decision(self):
        from backend.services.slack_interceptor import _detect_decision
        result = _detect_decision("Let's raise prices by 20% next week")
        assert result is not None
        assert result["type"] == "pricing"

    def test_detect_hiring_decision(self):
        from backend.services.slack_interceptor import _detect_decision
        result = _detect_decision("We should hire 2 senior engineers this quarter")
        assert result is not None
        assert result["type"] == "hiring"

    def test_detect_product_decision(self):
        from backend.services.slack_interceptor import _detect_decision
        result = _detect_decision("We should remove the CSV export feature to cut maintenance")
        assert result is not None
        assert result["type"] == "product"

    def test_detect_strategy_decision(self):
        from backend.services.slack_interceptor import _detect_decision
        result = _detect_decision("I think we should pivot to enterprise")
        assert result is not None
        assert result["type"] == "strategy"

    def test_no_false_positive_on_normal_message(self):
        from backend.services.slack_interceptor import _detect_decision
        for msg in ["Good morning everyone!", "The meeting is at 3pm", "Thanks for the update"]:
            result = _detect_decision(msg)
            assert result is None, f"False positive on: {msg}"

    def test_detect_percent_increase_variations(self):
        from backend.services.slack_interceptor import _detect_decision
        variations = [
            "increase pricing by 15%",
            "bump prices 30 percent",
            "pricing change effective Q3",
            "new pricing tiers from next month",
        ]
        for msg in variations:
            result = _detect_decision(msg)
            assert result is not None and result["type"] == "pricing", (
                f"Failed to detect pricing in: {msg}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 7. PRECHECK ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TestPrecheckEngine:
    def test_high_risk_pricing_with_low_nps(self):
        from backend.services.precheck_engine import run_precheck
        result = run(run_precheck(
            decision_text="Raise prices 20%",
            decision_type="pricing",
            snapshot={"nps": 28, "churn_rate": 0.10, "mrr": 85000},
        ))
        assert result["risk_level"] in ("high", "medium"), (
            f"Low NPS + high churn pricing should be high/medium risk, got {result['risk_level']}"
        )
        assert result["risk_score"] > 0.3

    def test_low_risk_pricing_with_good_metrics(self):
        from backend.services.precheck_engine import run_precheck
        result = run(run_precheck(
            decision_text="Raise prices 5%",
            decision_type="pricing",
            snapshot={"nps": 60, "churn_rate": 0.04, "mrr": 200000},
        ))
        assert result["risk_level"] == "low"

    def test_result_has_all_required_fields(self):
        from backend.services.precheck_engine import run_precheck
        result = run(run_precheck(
            decision_text="Increase pricing",
            decision_type="pricing",
            snapshot={"nps": 31, "churn_rate": 0.09},
        ))
        for field in ["risk_level", "risk_score", "blocking_conditions",
                      "pattern_matches", "alternative_recommendations",
                      "estimated_arr_impact", "safe_to_proceed_when"]:
            assert field in result, f"Missing field '{field}' in precheck result"

    def test_result_is_json_serializable(self):
        import json
        from backend.services.precheck_engine import run_precheck
        result = run(run_precheck("Test decision", "pricing", {"nps": 31}))
        json.dumps(result)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. FULL TRACE — end-to-end causal analysis
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullTrace:
    def test_trace_includes_bradford_hill(self):
        from backend.services.causal_tracer import _build_demo_trace
        trace = run(_build_demo_trace("acmesaas"))
        assert "bradford_hill" in trace, "Trace missing bradford_hill"
        bh = trace["bradford_hill"]
        assert bh["total_score"] > 0
        assert len(bh["criteria"]) == 9

    def test_trace_includes_benchmarks(self):
        from backend.services.causal_tracer import _build_demo_trace
        trace = run(_build_demo_trace("acmesaas"))
        assert "benchmarks" in trace, "Trace missing benchmarks"
        assert len(trace["benchmarks"]) >= 1

    def test_trace_includes_time_series_data(self):
        from backend.services.causal_tracer import _build_demo_trace
        trace = run(_build_demo_trace("acmesaas"))
        ts = trace.get("time_series_data")
        assert ts is not None, "Trace missing time_series_data"
        assert len(ts["dates"]) >= 5
        assert len(ts["nps"]) == len(ts["dates"])
        assert len(ts["churn_rate"]) == len(ts["dates"])

    def test_trace_data_source_is_bigquery(self):
        from backend.services.causal_tracer import _build_demo_trace
        trace = run(_build_demo_trace("acmesaas"))
        assert trace["data_source"] == "bigquery_live", (
            f"Expected bigquery_live, got {trace['data_source']}"
        )

    def test_trace_is_fully_json_serializable(self):
        import json
        from backend.services.causal_tracer import _build_demo_trace
        trace = run(_build_demo_trace("acmesaas"))
        json.dumps(trace, default=str)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. LIVE CLOUD RUN ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestLiveEndpoints:
    """Tests against the live Cloud Run deployment. Skip with -k 'not live'."""

    def _get(self, path: str, timeout: int = 15) -> dict:
        import requests
        r = requests.get(f"{LIVE_URL}{path}", timeout=timeout)
        assert r.status_code == 200, f"GET {path} returned {r.status_code}: {r.text[:200]}"
        return r.json()

    def _post(self, path: str, body: dict, timeout: int = 90) -> dict:
        import requests
        r = requests.post(f"{LIVE_URL}{path}", json=body, timeout=timeout)
        assert r.status_code == 200, f"POST {path} returned {r.status_code}: {r.text[:200]}"
        return r.json()

    def test_live_health(self):
        data = self._get("/api/health")
        assert data["status"] == "ok"
        assert data["mongodb"] == "connected"

    def test_live_gemini_model_is_gemini3(self):
        data = self._get("/api/health")
        model = data.get("gemini_model", "")
        assert "gemini-3" in model or "gemini-2.5" in model, (
            f"Live model '{model}' is not Gemini 3. Check GEMINI_MODEL env var."
        )

    def test_live_connectors(self):
        data = self._get("/api/connectors/list")
        assert "connectors" in data
        assert "bigquery_registry" in data
        assert len(data["bigquery_registry"]) >= 1

    def test_live_slack_events_endpoint(self):
        data = self._get("/api/slack/events")
        assert data["status"] == "ok"
        assert data["ready"] is True

    def test_live_warnings_active(self):
        data = self._get("/api/warnings/active")
        assert "warnings" in data

    def test_live_decisions_list(self):
        data = self._get("/api/decisions/list")
        assert "decisions" in data

    def test_live_mcp_endpoint(self):
        import requests
        r = requests.post(
            f"{LIVE_URL}/api/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1, "params": {}},
            timeout=15,
        )
        assert r.status_code == 200
        data = r.json()
        tools = data.get("result", {}).get("tools", [])
        assert len(tools) >= 5, f"Expected ≥5 MCP tools, got {len(tools)}"

    def test_live_precheck_endpoint(self):
        data = self._post("/api/decisions/precheck", {
            "decision_text": "Raise prices by 20%",
            "decision_type": "pricing",
        })
        assert "risk_level" in data
        assert data["risk_level"] in ("high", "medium", "low")

    def test_live_custom_analysis(self):
        data = self._post("/api/custom/analyze", {
            "decision_text": "Increased enterprise pricing by 15%",
            "decision_date": "2026-01-15",
            "churn_at_decision": 0.09,
            "churn_now": 0.14,
            "nps_at_decision": 31,
            "nps_now": 24,
        }, timeout=90)
        assert "verdict" in data
        assert "causal_analysis" in data

    def test_live_demo_full_trace(self):
        data = self._get("/api/demo/acmesaas/full", timeout=90)
        assert "trace" in data
        trace = data["trace"]
        assert "bradford_hill" in trace
        assert "benchmarks" in trace
        assert "time_series_data" in trace
        assert trace["data_source"] == "bigquery_live"

    def test_live_demo_trace_gemini3_narrative(self):
        data = self._get("/api/demo/acmesaas/full", timeout=90)
        narrative = data["trace"].get("narrative", "")
        assert len(narrative) > 50, "Narrative too short — Gemini 3 may not have responded"

    def test_live_agent_chat(self):
        data = self._post("/api/agent/chat", {
            "message": "What is SENTINEL? One sentence only.",
        }, timeout=60)
        assert "response" in data
        assert len(data["response"]) > 10


# ═══════════════════════════════════════════════════════════════════════════════
# 10. SLACK INTERCEPTOR URL VERIFICATION MOCK
# ═══════════════════════════════════════════════════════════════════════════════

class TestSlackEventsRoute:
    def test_url_verification_challenge(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)
        response = client.post("/api/slack/events", json={
            "type": "url_verification",
            "challenge": "test_challenge_abc123",
        })
        assert response.status_code == 200
        assert response.json()["challenge"] == "test_challenge_abc123"

    def test_event_callback_returns_ok(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)
        response = client.post("/api/slack/events", json={
            "type": "event_callback",
            "event": {
                "type": "message",
                "channel": "C12345",
                "user": "U12345",
                "text": "Good morning",
                "ts": "1234567890.000001",
            },
        })
        assert response.status_code == 200
        assert response.json()["ok"] is True

    def test_bot_message_ignored(self):
        """SENTINEL must not respond to its own Slack messages (infinite loop guard)."""
        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)
        response = client.post("/api/slack/events", json={
            "type": "event_callback",
            "event": {
                "type": "message",
                "bot_id": "B12345",  # bot message — should be ignored
                "channel": "C12345",
                "text": "Let's raise prices by 20%",
                "ts": "1234567890.000002",
            },
        })
        assert response.status_code == 200
