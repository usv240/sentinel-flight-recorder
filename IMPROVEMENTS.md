# SENTINEL — Honest Problems & Fixes

## Critical Issues Found (May 2026 audit)

---

### ISSUE 1: Fivetran MCP is not being used — it's the REST API
**File:** `backend/services/fivetran_client.py`
**Problem:** All Fivetran calls go to `https://api.fivetran.com/v1/...` via `httpx`.
That is the Fivetran REST API, not the Model Context Protocol server.
The hackathon track requires `github.com/fivetran/fivetran-mcp` — a stdio-based MCP server
where an agent calls `list_connectors`, `trigger_sync`, etc. as structured tool calls
that appear in an agent reasoning trace.
**Fix:** Implement `mcp_client.py` — spawns the fivetran-mcp subprocess, communicates via JSON-RPC, falls back to REST if MCP server is not running.
**Status:** [ ] TODO

---

### ISSUE 2: Google Cloud Agent Builder is not set up
**File:** `agent/AGENT_BUILDER_SETUP.md` describes it but it has not been created.
**Problem:** Without Agent Builder, there is no agent. There is a FastAPI server that calls
Gemini directly — that is not agent orchestration. Judges check the Agent Builder
playground reasoning trace. Missing this = disqualification from Fivetran track.
**Fix:** Set up in GCP console following `AGENT_BUILDER_SETUP.md`.
**Status:** [ ] TODO (requires GCP console — user action)

---

### ISSUE 3: Demo is 100% hardcoded static data — Gemini never runs
**Files:** `backend/routes/ask.py`, `backend/services/causal_tracer.py`, `backend/services/warning_engine.py`
**Problem:**
- `_demo_answer()` in ask.py returns hardcoded Python strings. Gemini is never called.
- `_build_demo_trace()` in causal_tracer.py returns a hardcoded dict with `"pearson_r": 0.87` as a literal.
- `_demo_warnings()` in warning_engine.py returns hardcoded dicts.
- A judge reading the source code sees that `r = 0.87` is a number in a Python file.
**Fix:** Build rich context from scenario data, call `generate()` for all prose fields.
**Status:** [ ] TODO

---

### ISSUE 4: Pearson r is a hardcoded literal, not a computation
**File:** `backend/services/causal_tracer.py:42` — `"pearson_r": 0.87`
**Problem:** The `_pearson_r()` function exists and uses scipy/numpy correctly,
but it is never called in the demo path. The number 0.87 is a hardcoded constant.
**Fix:** Build actual time-series (weekly metrics from decision day to outcome day)
and call `_pearson_r()` to get the real computed value.
**Status:** [ ] TODO

---

### ISSUE 5: The real BigQuery data is bypassed in demo mode
**File:** `backend/services/context_builder.py:42-43`
```python
if demo_scenario:
    return _demo_snapshot(demo_scenario)  # skips BigQuery entirely
```
**Problem:** A real Fivetran→BigQuery table (`google_sheets.acmesaas_metrics`, 7 rows)
exists and works. Demo mode never queries it. Showing live data would make the demo
genuinely impressive vs. static hardcoded values.
**Fix:** In demo mode, query BigQuery first, merge with scenario structure, fallback only if query fails.
**Status:** [ ] TODO

---

### ISSUE 6: Meeting transcript → decisions feature exists in code but has no UI or route
**File:** `backend/services/gemini_client.py:119` — `extract_decisions_from_transcript()` is implemented
**Problem:** This is one of the most creative, differentiating features. You paste a meeting
transcript and AI extracts structured decisions. No route, no endpoint, no UI.
**Fix:** Add `POST /api/decisions/extract-transcript` route + textarea UI in dashboard.
**Status:** [ ] TODO

---

### ISSUE 7: MCP tool calls shown in activity feed are fake JavaScript strings
**File:** `frontend/app.js:549-556`
```js
addActivity('fivetran', '⚡ MCP: fivetran.list_connectors()');  // hardcoded fake text
```
**Problem:** These labels are `addActivity()` calls with hardcoded text. They do not correspond
to real tool calls being made. The backend uses REST API; the frontend pretends MCP is running.
**Fix:** Backend emits real tool call logs with timing; frontend streams them via SSE or polling.
**Status:** [ ] TODO

---

### ISSUE 8: Log Decision modal shows fake "Fivetran snapshot" with simulated delays
**File:** `frontend/app.js:376-413`
**Problem:** `loadModalMetrics()` adds fake activity items with `_sleep(600)` and `_sleep(400)`.
No actual Fivetran call is triggered. The "Fivetran Snapshot — Captured Now" badge is misleading.
**Fix:** POST to backend which actually calls Fivetran (or MCP), returns real metrics.
**Status:** [ ] TODO

---

## Fix Priority

| # | Fix | Impact | Effort | Status |
|---|-----|--------|--------|--------|
| 1 | Gemini for all Ask/trace/warning prose | High | Low | TODO |
| 2 | Compute real Pearson r from time series | High | Low | TODO |
| 3 | Meeting transcript feature | High | Medium | TODO |
| 4 | Fivetran MCP subprocess client | Critical | High | TODO |
| 5 | BigQuery in demo mode | Medium | Medium | TODO |
| 6 | Agent Builder setup | Critical | GCP console | User action |
| 7 | Real backend tool call log → SSE → frontend | Medium | Medium | TODO |
| 8 | Log Decision triggers real Fivetran sync | Medium | Low (with MCP) | TODO |

---

## Architecture Goal (post-fixes)

```
User action
    │
    ▼
Frontend (app.js)
    │ POST /api/...
    ▼
FastAPI backend
    │
    ├─► Fivetran MCP subprocess ──► fivetran.list_connectors()
    │                                fivetran.trigger_sync()
    │                                fivetran.get_connector_schema()
    │
    ├─► BigQuery ─────────────────► SELECT * FROM google_sheets.acmesaas_metrics
    │
    ├─► Gemini 2.5 Flash ─────────► analyze_causal_chain(real data)
    │                                generate_warning_narrative(real metrics)
    │                                extract_decisions_from_transcript()
    │                                answer_why_question(full context)
    │
    └─► MongoDB Atlas ─────────────► store decision + real metrics snapshot
```

Every response is computed. Nothing is hardcoded.
