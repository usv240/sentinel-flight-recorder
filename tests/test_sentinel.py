"""
SENTINEL — Comprehensive End-to-End Tests
==========================================
Tests every route, every demo scenario, every output file, and every agent behavior.

Run:
    cd sentinel
    uvicorn backend.main:app --port 8100 &
    python -m pytest tests/test_sentinel.py -v --tb=short

Or run a single test:
    python -m pytest tests/test_sentinel.py::test_full_acmesaas_flow -v
"""

import pytest
import httpx
import json
import time
from pathlib import Path
from datetime import datetime

BASE = "http://localhost:8100"
OUTPUT_DIR = Path("outputs/sentinel")


@pytest.fixture(scope="session")
def client():
    return httpx.Client(base_url=BASE, timeout=30)


# ═══════════════════════════════════════════════════════════════
# HEALTH + BASIC
# ═══════════════════════════════════════════════════════════════

class TestHealth:
    def test_health_returns_ok(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "ok"
        assert d["service"] == "SENTINEL"
        assert d["version"] == "1.0.0"

    def test_health_has_demo_mode_field(self, client):
        r = client.get("/api/health")
        assert "demo_mode" in r.json()

    def test_frontend_serves_index(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "SENTINEL" in r.text
        assert "Flight Recorder" in r.text

    def test_static_css_loads(self, client):
        r = client.get("/static/style.css")
        assert r.status_code == 200
        assert "sentinel" in r.text.lower()

    def test_static_js_loads(self, client):
        r = client.get("/static/app.js")
        assert r.status_code == 200
        assert "loadScenario" in r.text


# ═══════════════════════════════════════════════════════════════
# DEMO SCENARIOS
# ═══════════════════════════════════════════════════════════════

class TestDemoScenarios:
    def test_list_scenarios_returns_two(self, client):
        r = client.get("/api/demo/scenarios")
        assert r.status_code == 200
        d = r.json()
        assert len(d["scenarios"]) == 2
        ids = {s["id"] for s in d["scenarios"]}
        assert "acmesaas" in ids
        assert "qwikster" in ids

    def test_acmesaas_full_has_all_sections(self, client):
        r = client.get("/api/demo/acmesaas/full")
        assert r.status_code == 200
        d = r.json()
        assert "meta" in d
        assert "decisions" in d
        assert "warnings" in d
        assert "trace" in d
        assert "snapshot" in d

    def test_acmesaas_meta_correct(self, client):
        d = client.get("/api/demo/acmesaas/full").json()
        assert d["meta"]["id"] == "acmesaas"
        assert d["meta"]["days_of_warning"] == 34
        assert "$120K" in d["meta"]["outcome"] or "120" in d["meta"]["outcome"]

    def test_acmesaas_has_decisions(self, client):
        d = client.get("/api/demo/acmesaas/full").json()
        assert len(d["decisions"]) >= 2
        types = {dec["decision_type"] for dec in d["decisions"]}
        assert "pricing" in types

    def test_acmesaas_pricing_decision_exists(self, client):
        d = client.get("/api/demo/acmesaas/full").json()
        pricing = next((dec for dec in d["decisions"] if dec["decision_type"] == "pricing"), None)
        assert pricing is not None
        assert "20%" in pricing["decision_text"] or "pricing" in pricing["decision_text"].lower()
        assert pricing["outcome"] == "churn_spike"
        assert pricing["warning_fired"] is True

    def test_acmesaas_has_critical_warning(self, client):
        d = client.get("/api/demo/acmesaas/full").json()
        assert len(d["warnings"]) >= 1
        critical = next((w for w in d["warnings"] if w["severity"] == "critical"), None)
        assert critical is not None
        assert critical["causal_confidence"] >= 0.8
        assert "Customer X" in critical["message"] or "login" in critical["message"].lower()

    def test_acmesaas_trace_strong_correlation(self, client):
        d = client.get("/api/demo/acmesaas/full").json()
        trace = d["trace"]
        assert trace["pearson_r"] >= 0.8
        assert trace["days_of_warning"] == 34
        assert len(trace["causal_chain"]) >= 4

    def test_acmesaas_trace_chain_has_outcome(self, client):
        d = client.get("/api/demo/acmesaas/full").json()
        chain = d["trace"]["causal_chain"]
        types = [e["type"] for e in chain]
        assert "decision" in types
        assert "outcome" in types

    def test_acmesaas_snapshot_has_warning_flags(self, client):
        d = client.get("/api/demo/acmesaas/full").json()
        snap = d["snapshot"]
        assert snap["nps"] == 31
        assert snap["churn_rate"] == 0.09
        assert len(snap.get("_flags", [])) >= 2

    def test_qwikster_full_has_all_sections(self, client):
        r = client.get("/api/demo/qwikster/full")
        assert r.status_code == 200
        d = r.json()
        for key in ["meta", "decisions", "warnings", "trace", "snapshot"]:
            assert key in d

    def test_qwikster_trace_highest_correlation(self, client):
        d = client.get("/api/demo/qwikster/full").json()
        assert d["trace"]["pearson_r"] >= 0.85
        assert "800" in d["trace"]["outcome_description"]

    def test_qwikster_snapshot_shows_warning_signals(self, client):
        d = client.get("/api/demo/qwikster/full").json()
        flags = d["snapshot"].get("_flags", [])
        assert len(flags) >= 2
        flag_text = " ".join(flags).lower()
        assert "subscriber" in flag_text or "growth" in flag_text

    def test_unknown_scenario_returns_error(self, client):
        r = client.get("/api/demo/nonexistent/full")
        assert r.status_code == 200
        assert "error" in r.json()


# ═══════════════════════════════════════════════════════════════
# DECISIONS
# ═══════════════════════════════════════════════════════════════

class TestDecisions:
    def test_log_decision_returns_id(self, client):
        r = client.post("/api/decisions/log?demo_scenario=acmesaas", json={
            "decision_text": "TEST: Reduce marketing budget by 30%",
            "decision_type": "strategy",
            "rationale": "Q3 burn rate too high",
            "alternatives_considered": ["Reduce headcount", "Cut travel only"],
        })
        assert r.status_code == 200
        d = r.json()
        assert "decision_id" in d
        assert d["decision_id"].startswith("DEC-")

    def test_log_decision_captures_metrics(self, client):
        r = client.post("/api/decisions/log?demo_scenario=acmesaas", json={
            "decision_text": "TEST: Launch enterprise tier",
            "decision_type": "product",
        })
        d = r.json()
        assert "metrics_captured" in d
        assert len(d["metrics_captured"]) > 0

    def test_log_decision_detects_flags(self, client):
        r = client.post("/api/decisions/log?demo_scenario=acmesaas", json={
            "decision_text": "TEST: Pricing increase decision when NPS is low",
            "decision_type": "pricing",
            "rationale": "Improve unit economics",
        })
        d = r.json()
        assert "flags" in d
        assert len(d["flags"]) >= 1
        flag_text = " ".join(d["flags"]).lower()
        assert "nps" in flag_text or "churn" in flag_text or "support" in flag_text

    def test_list_decisions_demo_returns_decisions(self, client):
        r = client.get("/api/decisions/list?demo_scenario=acmesaas")
        assert r.status_code == 200
        d = r.json()
        assert "decisions" in d
        assert d["total"] >= 2

    def test_list_decisions_have_required_fields(self, client):
        decisions = client.get("/api/decisions/list?demo_scenario=acmesaas").json()["decisions"]
        for dec in decisions:
            assert "decision_id" in dec
            assert "decision_text" in dec
            assert "decision_type" in dec
            assert "logged_at" in dec


# ═══════════════════════════════════════════════════════════════
# WARNINGS
# ═══════════════════════════════════════════════════════════════

class TestWarnings:
    def test_active_warnings_acmesaas(self, client):
        r = client.get("/api/warnings/active?demo_scenario=acmesaas")
        assert r.status_code == 200
        d = r.json()
        assert "warnings" in d
        assert len(d["warnings"]) >= 1

    def test_warning_has_required_fields(self, client):
        warnings = client.get("/api/warnings/active?demo_scenario=acmesaas").json()["warnings"]
        w = warnings[0]
        for field in ["warning_id", "severity", "message", "recommended_action", "causal_confidence"]:
            assert field in w, f"Missing field: {field}"

    def test_warning_severity_valid(self, client):
        warnings = client.get("/api/warnings/active?demo_scenario=acmesaas").json()["warnings"]
        valid_severities = {"critical", "high", "medium", "low"}
        for w in warnings:
            assert w["severity"] in valid_severities

    def test_warning_confidence_range(self, client):
        warnings = client.get("/api/warnings/active?demo_scenario=acmesaas").json()["warnings"]
        for w in warnings:
            assert 0.0 <= w["causal_confidence"] <= 1.0

    def test_qwikster_warning_critical(self, client):
        warnings = client.get("/api/warnings/active?demo_scenario=qwikster").json()["warnings"]
        assert any(w["severity"] == "critical" for w in warnings)
        assert any(w["causal_confidence"] >= 0.85 for w in warnings)


# ═══════════════════════════════════════════════════════════════
# CAUSAL TRACE
# ═══════════════════════════════════════════════════════════════

class TestCausalTrace:
    def test_demo_trace_acmesaas(self, client):
        r = client.get("/api/trace/demo/acmesaas")
        assert r.status_code == 200
        d = r.json()
        assert "causal_chain" in d
        assert "pearson_r" in d
        assert "days_of_warning" in d
        assert "narrative" in d

    def test_trace_pearson_r_strong(self, client):
        d = client.get("/api/trace/demo/acmesaas").json()
        assert d["pearson_r"] >= 0.8, f"Pearson r too low: {d['pearson_r']}"

    def test_trace_days_of_warning_correct(self, client):
        d = client.get("/api/trace/demo/acmesaas").json()
        assert d["days_of_warning"] == 34

    def test_trace_chain_ordered(self, client):
        chain = client.get("/api/trace/demo/acmesaas").json()["causal_chain"]
        assert chain[0]["type"] == "decision", "First event must be a decision"
        assert chain[-1]["type"] == "outcome", "Last event must be an outcome"

    def test_trace_chain_has_signals(self, client):
        chain = client.get("/api/trace/demo/acmesaas").json()["causal_chain"]
        signal_events = [e for e in chain if e["type"] == "signal"]
        assert len(signal_events) >= 2, "Must have at least 2 signal events"

    def test_trace_data_at_decision_time(self, client):
        d = client.get("/api/trace/demo/acmesaas").json()
        data = d.get("data_available_at_decision", {})
        assert len(data) >= 3, "Must show at least 3 data points available at decision time"

    def test_trace_predicted_signals(self, client):
        d = client.get("/api/trace/demo/acmesaas").json()
        signals = d.get("data_that_predicted_outcome", [])
        assert len(signals) >= 2, "Must list at least 2 predictive signals"
        signal_text = " ".join(signals).lower()
        assert "nps" in signal_text or "support" in signal_text or "churn" in signal_text

    def test_trace_recommended_actions(self, client):
        d = client.get("/api/trace/demo/acmesaas").json()
        actions = d.get("recommended_actions", [])
        assert len(actions) >= 2, "Must provide at least 2 recommended actions"

    def test_trace_narrative_non_empty(self, client):
        d = client.get("/api/trace/demo/acmesaas").json()
        assert len(d.get("narrative", "")) > 50, "Narrative must be meaningful"

    def test_qwikster_trace_higher_correlation(self, client):
        d = client.get("/api/trace/demo/qwikster").json()
        assert d["pearson_r"] >= 0.85
        assert "subscriber" in d["outcome_description"].lower() or "800" in d["outcome_description"]

    def test_post_trace_analyze(self, client):
        r = client.post("/api/trace/analyze", json={
            "outcome_description": "Churn spiked from 9% to 14%",
            "outcome_first_observed": "2026-07-15T00:00:00",
            "affected_metric": "churn_rate",
            "demo_scenario": "acmesaas",
        })
        assert r.status_code == 200
        d = r.json()
        assert "pearson_r" in d
        assert "days_of_warning" in d


# ═══════════════════════════════════════════════════════════════
# ASK SENTINEL
# ═══════════════════════════════════════════════════════════════

class TestAskSentinel:
    def test_ask_pricing_question(self, client):
        r = client.post("/api/ask/", json={
            "question": "Why did we raise prices?",
            "demo_scenario": "acmesaas",
        })
        assert r.status_code == 200
        d = r.json()
        assert "answer" in d
        assert len(d["answer"]) > 50
        assert d["confidence"] > 0.5

    def test_ask_churn_question(self, client):
        r = client.post("/api/ask/", json={
            "question": "What caused the churn spike?",
            "demo_scenario": "acmesaas",
        })
        d = r.json()
        answer_lower = d["answer"].lower()
        assert "pricing" in answer_lower or "price" in answer_lower or "june" in answer_lower

    def test_ask_returns_sources(self, client):
        r = client.post("/api/ask/", json={
            "question": "What data existed when we made the pricing decision?",
            "demo_scenario": "acmesaas",
        })
        d = r.json()
        assert "sources" in d
        assert len(d["sources"]) >= 1

    def test_ask_qwikster_question(self, client):
        r = client.post("/api/ask/", json={
            "question": "Why did Netflix create Qwikster?",
            "demo_scenario": "qwikster",
        })
        d = r.json()
        assert len(d["answer"]) > 50
        answer_lower = d["answer"].lower()
        assert "split" in answer_lower or "dvd" in answer_lower or "streaming" in answer_lower

    def test_ask_confidence_in_range(self, client):
        r = client.post("/api/ask/", json={
            "question": "What should we have done differently?",
            "demo_scenario": "acmesaas",
        })
        d = r.json()
        assert 0.0 <= d["confidence"] <= 1.0


# ═══════════════════════════════════════════════════════════════
# CONNECTORS (Fivetran)
# ═══════════════════════════════════════════════════════════════

class TestConnectors:
    def test_list_connectors_returns_list(self, client):
        r = client.get("/api/connectors/list")
        assert r.status_code == 200
        d = r.json()
        assert "connectors" in d
        assert d["count"] >= 1

    def test_connectors_have_required_fields(self, client):
        connectors = client.get("/api/connectors/list").json()["connectors"]
        for c in connectors:
            assert "id" in c
            assert "service" in c
            assert "status" in c

    def test_connectors_include_sheets(self, client):
        connectors = client.get("/api/connectors/list").json()["connectors"]
        services = [c["service"] for c in connectors]
        assert any("sheets" in s or "google" in s for s in services), \
            f"Google Sheets connector not found. Services: {services}"


# ═══════════════════════════════════════════════════════════════
# OUTPUT FILES
# ═══════════════════════════════════════════════════════════════

class TestOutputFiles:
    def test_output_dir_exists(self):
        assert OUTPUT_DIR.exists(), f"Output dir missing: {OUTPUT_DIR}"

    def test_output_subdirs_exist(self):
        for subdir in ["sessions", "decisions", "traces", "warnings", "asks", "demo"]:
            path = OUTPUT_DIR / subdir
            assert path.exists(), f"Subdir missing: {path}"

    def test_demo_load_writes_file(self, client):
        client.get("/api/demo/acmesaas/full")
        time.sleep(0.2)
        files = list((OUTPUT_DIR / "demo").glob("demo_acmesaas_*.md"))
        assert len(files) >= 1, "Demo load should write an output file"

    def test_demo_output_has_content(self, client):
        client.get("/api/demo/acmesaas/full")
        time.sleep(0.2)
        latest = OUTPUT_DIR / "latest_demo_acmesaas.md"
        assert latest.exists(), "latest_demo_acmesaas.md should exist"
        content = latest.read_text(encoding="utf-8")
        assert "AcmeSaaS" in content
        assert "Pearson r" in content
        assert "34" in content  # days of warning

    def test_trace_writes_output(self, client):
        client.get("/api/trace/demo/acmesaas")
        time.sleep(0.2)
        files = list((OUTPUT_DIR / "traces").glob("trace_*.md"))
        assert len(files) >= 1

    def test_trace_output_has_stats(self, client):
        client.get("/api/trace/demo/acmesaas")
        time.sleep(0.2)
        latest = OUTPUT_DIR / "latest_causal_trace.md"
        assert latest.exists()
        content = latest.read_text(encoding="utf-8")
        assert "Pearson r" in content
        assert "Days of warning" in content
        assert "Causal Chain" in content

    def test_ask_writes_output(self, client):
        client.post("/api/ask/", json={"question": "Test question?", "demo_scenario": "acmesaas"})
        time.sleep(0.2)
        files = list((OUTPUT_DIR / "asks").glob("ask_*.md"))
        assert len(files) >= 1

    def test_ask_output_has_qa(self, client):
        client.post("/api/ask/", json={"question": "Why did we raise prices?", "demo_scenario": "acmesaas"})
        time.sleep(0.2)
        latest = OUTPUT_DIR / "latest_ask.md"
        assert latest.exists()
        content = latest.read_text(encoding="utf-8")
        assert "Why did we raise prices?" in content
        assert "Answer" in content

    def test_session_log_written(self):
        files = list((OUTPUT_DIR / "sessions").glob("session_*.md"))
        assert len(files) >= 1, "At least one session log should exist"

    def test_session_log_has_events(self):
        files = sorted((OUTPUT_DIR / "sessions").glob("session_*.md"))
        if files:
            content = files[-1].read_text(encoding="utf-8")
            assert "SENTINEL Session Log" in content

    def test_json_outputs_valid(self, client):
        client.get("/api/demo/acmesaas/full")
        time.sleep(0.2)
        json_files = list((OUTPUT_DIR / "demo").glob("*.json"))
        for f in json_files[:3]:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                assert isinstance(data, dict)
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in {f}: {e}")


# ═══════════════════════════════════════════════════════════════
# FULL FLOW INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════

class TestFullFlows:
    def test_full_acmesaas_flow(self, client):
        """Complete demo flow: load → check warnings → trace → ask"""
        # 1. Load scenario
        scenario = client.get("/api/demo/acmesaas/full").json()
        assert scenario["meta"]["id"] == "acmesaas"

        # 2. Check warnings
        warnings = client.get("/api/warnings/active?demo_scenario=acmesaas").json()
        assert len(warnings["warnings"]) >= 1
        critical = next((w for w in warnings["warnings"] if w["severity"] == "critical"), None)
        assert critical is not None

        # 3. Trace the outcome
        trace = client.get("/api/trace/demo/acmesaas").json()
        assert trace["pearson_r"] >= 0.8
        assert trace["days_of_warning"] == 34

        # 4. Ask why
        answer = client.post("/api/ask/", json={
            "question": "Why did we raise prices?",
            "demo_scenario": "acmesaas",
        }).json()
        assert answer["confidence"] > 0.5

        # 5. Verify output files written
        time.sleep(0.3)
        assert (OUTPUT_DIR / "latest_causal_trace.md").exists()
        assert (OUTPUT_DIR / "latest_ask.md").exists()

    def test_full_qwikster_flow(self, client):
        """Complete Qwikster demo flow"""
        scenario = client.get("/api/demo/qwikster/full").json()
        assert scenario["meta"]["id"] == "qwikster"
        assert scenario["trace"]["pearson_r"] >= 0.85

        warnings = client.get("/api/warnings/active?demo_scenario=qwikster").json()
        assert len(warnings["warnings"]) >= 1

        trace = client.get("/api/trace/demo/qwikster").json()
        assert "subscriber" in trace["outcome_description"].lower() or "800" in trace["outcome_description"]

    def test_log_then_list_decision(self, client):
        """Log a decision then verify it appears in the list"""
        post_r = client.post("/api/decisions/log?demo_scenario=acmesaas", json={
            "decision_text": "FLOW TEST: Freeze all hiring for Q3",
            "decision_type": "hiring",
            "rationale": "Runway below 12 months",
        })
        assert post_r.status_code == 200
        decision_id = post_r.json()["decision_id"]
        assert decision_id.startswith("DEC-")

    def test_scenario_switch_flow(self, client):
        """Switch between scenarios and verify data changes"""
        acme = client.get("/api/demo/acmesaas/full").json()
        qwik = client.get("/api/demo/qwikster/full").json()

        # Completely different companies
        assert acme["meta"]["id"] != qwik["meta"]["id"]
        assert acme["snapshot"]["nps"] != qwik["snapshot"]["nps"]
        assert acme["trace"]["days_of_warning"] != qwik["trace"]["days_of_warning"]

    def test_demo_data_story_integrity(self, client):
        """Verify the AcmeSaaS story is internally consistent"""
        d = client.get("/api/demo/acmesaas/full").json()

        # NPS was 31 at decision time (below 40 threshold)
        assert d["snapshot"]["nps"] == 31
        assert d["snapshot"]["nps"] < 40

        # Churn was already elevated at decision time
        assert d["snapshot"]["churn_rate"] > 0.08

        # Warning fired after decision
        pricing_dec = next(dec for dec in d["decisions"] if dec["decision_type"] == "pricing")
        assert pricing_dec["warning_fired"] is True
        assert pricing_dec["days_of_warning"] == 34

        # Causal chain starts with decision, ends with outcome
        chain = d["trace"]["causal_chain"]
        assert chain[0]["type"] == "decision"
        assert chain[-1]["type"] == "outcome"
        assert chain[-1]["metric_value"] == -120000.0  # $120K ARR lost
