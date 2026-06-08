"""
SENTINEL — Tests for the credibility-hardening features added in June 2026.

Covers everything introduced after the initial build:
  - Gemini model reconciliation (shared accessors + ADK agent model resolution)
  - Integration diagnostics  (/api/health/integrations, honest live-vs-demo)
  - Fivetran source tagging   (_source/_live, never present mock as live)
  - trigger_sync fix          (request_body required — was silently failing)
  - Context-builder provenance (_data_source/_live on snapshots)
  - Health + MCP HTTP server   (in-process, no deploy needed)
  - Agent chat response contract (honest model + tool trace)

Most tests run in-process (TestClient / direct calls) and pass regardless of
whether live credentials are present. Tests that require live Fivetran API
access skip gracefully in demo mode.

Run:
  python -m pytest tests/test_new_features.py -v
"""

import asyncio
import os
import sys
import json
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _client():
    from fastapi.testclient import TestClient
    from backend.main import app
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. GEMINI MODEL RECONCILIATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestGeminiModelReconciliation:
    """Guards against the code/marketing drift where the ADK agent silently
    defaulted to gemini-2.5 while everything else claimed Gemini 3."""

    def test_accessors_exist_and_typed(self):
        from backend.services import gemini_client as g
        assert isinstance(g.get_gemini3_models(), list) and g.get_gemini3_models()
        assert isinstance(g.get_vertex_fallback_models(), list)
        assert isinstance(g.get_configured_model(), str) and g.get_configured_model()
        assert isinstance(g.get_active_model(), str) and g.get_active_model()
        assert isinstance(g.gemini3_quota_exhausted(), bool)

    def test_is_gemini3_model_classifies_correctly(self):
        from backend.services import gemini_client as g
        assert g.is_gemini3_model("gemini-3-flash-preview") is True
        assert g.is_gemini3_model("gemini-2.5-flash") is False

    def test_configured_model_is_gemini3_by_default(self):
        from backend.services import gemini_client as g
        assert "gemini-3" in g.get_configured_model() or g.get_configured_model() in g.get_gemini3_models()

    def test_agent_shares_same_model_tiers(self):
        from backend.services import gemini_client as g
        from agent import sentinel_agent as a
        assert a._GEMINI3_MODELS == g.get_gemini3_models()
        assert a._VERTEX_FALLBACK == g.get_vertex_fallback_models()

    def test_agent_primary_is_gemini3_fallback_is_vertex(self):
        from agent import sentinel_agent as a
        assert "gemini-3" in a._primary_model()
        assert "gemini-2.5" in a._fallback_model()

    def test_agent_configures_apikey_backend_for_gemini3(self):
        from agent import sentinel_agent as a
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("No GEMINI_API_KEY to exercise the API-key backend path")
        a._configure_adk_for_model("gemini-3-flash-preview")
        assert os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") == "FALSE"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. INTEGRATION DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDiagnostics:
    def test_gather_returns_all_integrations(self):
        from backend.services.diagnostics import gather_integration_status
        d = run(gather_integration_status())
        assert d["posture"] in ("demo", "partially_live", "fully_live")
        for key in ("gemini", "fivetran", "bigquery", "mongodb", "adk", "slack"):
            assert key in d["integrations"], f"missing integration: {key}"
            assert "status" in d["integrations"][key]

    def test_every_status_is_valid_label(self):
        from backend.services.diagnostics import gather_integration_status
        valid = {"live", "configured", "demo", "error", "unavailable"}
        d = run(gather_integration_status())
        for k, v in d["integrations"].items():
            assert v["status"] in valid, f"{k} has invalid status {v['status']}"

    def test_result_is_json_serializable(self):
        from backend.services.diagnostics import gather_integration_status
        json.dumps(run(gather_integration_status()))

    def test_endpoint_returns_posture(self):
        r = _client().get("/api/health/integrations")
        assert r.status_code == 200
        assert r.json()["posture"] in ("demo", "partially_live", "fully_live")

    def test_fivetran_probe_never_claims_live_while_mock(self):
        """If fivetran reports 'live' it MUST have a real (non-mock) connector."""
        from backend.services.diagnostics import gather_integration_status
        ft = run(gather_integration_status())["integrations"]["fivetran"]
        if ft["status"] == "live":
            assert ft.get("live_connectors", 0) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# 3. FIVETRAN SOURCE TAGGING (never present mock as live)
# ═══════════════════════════════════════════════════════════════════════════════

class TestFivetranSourceTagging:
    def test_call_result_is_source_tagged(self):
        from backend.services.mcp_client import call_mcp_tool
        r = run(call_mcp_tool("list_connections"))
        assert r.get("_source") in ("mcp", "rest", "demo")
        assert isinstance(r.get("_live"), bool)
        if r.get("_source") == "demo":
            assert r["_live"] is False

    def test_fivetran_mode_is_valid(self):
        from backend.services.mcp_client import fivetran_mode, fivetran_has_creds
        assert fivetran_mode() in ("mcp", "rest", "demo")
        assert isinstance(fivetran_has_creds(), bool)

    def test_tag_source_marks_demo_not_live(self):
        from backend.services.mcp_client import _tag_source
        assert _tag_source({}, "demo")["_live"] is False
        assert _tag_source({}, "mcp")["_live"] is True
        assert _tag_source({}, "rest")["_live"] is True

    def test_items_or_mock_returns_empty_when_live(self):
        from backend.services.mcp_client import _items_or_mock
        live_empty = {"data": {"items": []}, "_live": True, "_source": "mcp"}
        assert _items_or_mock(live_empty, lambda: [{"id": "mock_x"}]) == []

    def test_items_or_mock_falls_back_when_not_live(self):
        from backend.services.mcp_client import _items_or_mock
        demo = {"_live": False, "_source": "demo"}
        out = _items_or_mock(demo, lambda: [{"id": "mock_x"}])
        assert out and out[0]["id"] == "mock_x"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. TRIGGER_SYNC FIX (request_body required — was silently failing)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTriggerSyncFix:
    def test_trigger_sync_sends_force_request_body(self, monkeypatch):
        from backend.services import mcp_client
        captured = {}

        async def fake_call(tool, args=None):
            captured["tool"] = tool
            captured["args"] = args or {}
            return {"code": "Success"}

        monkeypatch.setattr(mcp_client, "call_mcp_tool", fake_call)
        result = run(mcp_client.trigger_sync("conn_123"))
        assert result is True
        assert captured["args"].get("connection_id") == "conn_123"
        assert captured["args"].get("request_body") == {"force": True}

    def test_trigger_sync_interprets_success_code(self, monkeypatch):
        from backend.services import mcp_client

        async def ok(tool, args=None):
            return {"code": "Success", "message": "Sync triggered"}

        monkeypatch.setattr(mcp_client, "call_mcp_tool", ok)
        assert run(mcp_client.trigger_sync("c")) is True

    def test_trigger_sync_detects_validation_error(self, monkeypatch):
        from backend.services import mcp_client

        async def bad(tool, args=None):
            return {"raw": "Input validation error: request_body is a required property"}

        monkeypatch.setattr(mcp_client, "call_mcp_tool", bad)
        assert run(mcp_client.trigger_sync("c")) is False

    def test_trigger_sync_live(self):
        from backend.services.mcp_client import fivetran_mode, list_connectors, trigger_sync
        if fivetran_mode() == "demo":
            pytest.skip("Fivetran in demo mode — no live connectors to sync")
        cons = run(list_connectors())
        real = [c for c in cons if not str(c.get("id", "")).startswith("mock_")]
        if not real:
            pytest.skip("No real Fivetran connectors available to sync")
        assert run(trigger_sync(real[0]["id"])) is True


# ═══════════════════════════════════════════════════════════════════════════════
# 5. CONTEXT BUILDER PROVENANCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestContextBuilderProvenance:
    def test_demo_snapshot_tagged_demo(self):
        from backend.services.context_builder import build_metrics_snapshot
        snap = run(build_metrics_snapshot(demo_scenario="acmesaas"))
        assert snap.get("_data_source") == "demo"
        assert snap.get("_live") is False

    def test_live_snapshot_has_provenance_fields(self):
        from backend.services.context_builder import build_metrics_snapshot
        snap = run(build_metrics_snapshot())
        assert snap.get("_data_source") in ("bigquery_live", "demo")
        assert isinstance(snap.get("_live"), bool)
        if snap.get("_data_source") == "bigquery_live":
            assert snap.get("_table")

    def test_primary_table_resolves(self):
        from backend.services.context_builder import _primary_table
        t = _primary_table()
        assert isinstance(t, str) and "." in t


# ═══════════════════════════════════════════════════════════════════════════════
# 6. HEALTH + MCP HTTP SERVER (in-process)
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthAndMcpHttp:
    def test_health_reports_active_and_configured_model(self):
        d = _client().get("/api/health").json()
        assert "gemini_model" in d
        assert "gemini_model_configured" in d
        assert "gemini3_quota_exhausted" in d

    def test_mcp_get_discovery(self):
        """Agent Builder / Agent Studio probes the endpoint with GET first."""
        r = _client().get("/api/mcp")
        assert r.status_code == 200
        d = r.json()
        assert d["protocolVersion"] == "2025-03-26"
        assert d["server"]["name"]
        assert len(d["tools"]) == 9
        assert "agent_builder" in d["usage"]

    def test_mcp_initialize(self):
        r = _client().post("/api/mcp", json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        body = r.json()
        assert body["result"]["protocolVersion"] == "2025-03-26"
        assert body["result"]["serverInfo"]["name"]

    def test_mcp_tools_list(self):
        r = _client().post("/api/mcp", json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools = r.json()["result"]["tools"]
        assert len(tools) == 9, f"expected 9 MCP tools, got {len(tools)}"
        names = {t["name"] for t in tools}
        assert "list_fivetran_connectors" in names
        assert "trigger_fivetran_sync" in names

    def test_mcp_tools_call(self):
        r = _client().post("/api/mcp", json={
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "list_fivetran_connectors", "arguments": {}}})
        content = r.json()["result"]["content"]
        assert content and content[0]["type"] == "text"

    def test_connectors_platform_shape(self):
        d = _client().get("/api/connectors/platform").json()
        assert "summary" in d and "connectors" in d
        for k in ("groups", "connectors", "live_connectors", "destinations", "webhooks"):
            assert k in d["summary"]


# ═══════════════════════════════════════════════════════════════════════════════
# 7. AGENT CHAT RESPONSE CONTRACT
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentChatContract:
    def test_agent_chat_reports_model_and_trace(self):
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("No GEMINI_API_KEY — agent needs a live model")
        r = _client().post("/api/agent/chat", json={
            "message": "List our Fivetran connectors. One short sentence."})
        assert r.status_code == 200
        d = r.json()
        assert "model" in d and "model_fallback" in d
        assert "tool_trace" in d and isinstance(d["tool_trace"], list)
        assert d["steps"] == len(d["tool_trace"])
        from backend.services import gemini_client as g
        assert d["model"] in (g.get_gemini3_models() + g.get_vertex_fallback_models())


# ═══════════════════════════════════════════════════════════════════════════════
# 8. RICHER DATASET + QWIKSTER HONESTY
# ═══════════════════════════════════════════════════════════════════════════════

class TestRicherDatasetAndHonesty:
    def test_richer_dataset_file_valid(self):
        """data/acmesaas_metrics.csv has the decision row + required columns."""
        import csv
        path = Path(__file__).parent.parent / "data" / "acmesaas_metrics.csv"
        assert path.exists(), "richer dataset CSV missing"
        rows = list(csv.DictReader(path.open()))
        assert len(rows) >= 15, f"expected >=15 rows for statistical power, got {len(rows)}"
        required = {"date", "mrr", "nps", "churn_rate", "support_tickets_7d"}
        assert required.issubset(rows[0].keys())
        assert any(r["date"] == "2026-06-03" for r in rows), "decision-date row 2026-06-03 missing"

    def test_richer_dataset_yields_three_of_three(self):
        """The richer series must score 3/3 — the reason to ship it."""
        import csv
        from backend.services.causal_tracer import _run_causal_battery
        path = Path(__file__).parent.parent / "data" / "acmesaas_metrics.csv"
        rows = list(csv.DictReader(path.open()))
        nps = [float(r["nps"]) for r in rows]
        churn = [float(r["churn_rate"]) for r in rows]
        di = next(i for i, r in enumerate(rows) if r["date"] == "2026-06-03")
        a = _run_causal_battery(time_series=churn, indicator_series=nps,
                                decision_index=di, metric_name="churn_rate")
        assert a["significant_tests"] == 3, f"expected 3/3, got {a['significant_tests']}"
        assert a["verdict"] == "strong_signal"

    def test_qwikster_trace_is_not_falsely_live(self):
        """Qwikster must NOT report bigquery_live (it's a historical case study)."""
        from backend.services.causal_tracer import _build_demo_trace
        t = run(_build_demo_trace("qwikster"))
        assert t.get("data_source") != "bigquery_live", (
            "Qwikster must not claim live BigQuery — it's a 2011 public case study"
        )

    def test_acmesaas_trace_is_live(self):
        """AcmeSaaS should be genuinely BigQuery-live (skips if no creds)."""
        from backend.services.mcp_client import fivetran_has_creds
        if not (os.getenv("GOOGLE_PROJECT_ID") and fivetran_has_creds()):
            pytest.skip("No live BigQuery/Fivetran creds")
        from backend.services.causal_tracer import _build_demo_trace
        t = run(_build_demo_trace("acmesaas"))
        assert t.get("data_source") == "bigquery_live"
