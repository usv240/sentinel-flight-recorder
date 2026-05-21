# SENTINEL — The Business Flight Recorder
## Devpost Submission Text

---

### What it does

SENTINEL is the flight recorder for your business. It watches every business decision, connects it to real-time Fivetran data, and fires alerts before a bad call destroys revenue.

When a pricing change causes churn three months later, nobody remembers what the data looked like the day the decision was made. The warning was there. Nobody connected the dots.

SENTINEL fixes that with five interconnected agent systems:

**1. Multi-Agent Decision Council** — Post a business decision in Slack and SENTINEL convenes a 4-agent Gemini 3 council within 60 seconds: a Data Agent (pulls real BigQuery metrics), a Risk Agent (scores bad outcome probability), an Alternatives Agent (proposes evidence-backed alternatives), and a Lead Agent (synthesizes a go/no-go recommendation). Reply PLAN/PROCEED/CANCEL to trigger follow-up.

**2. Impact Trace** — A full causal reconstruction showing exactly how a decision propagated into outcome metrics. Three independent statistical methods (Granger causality, Interrupted Time Series, Mann-Whitney U) run in parallel. Bradford Hill's 9 causal criteria (from epidemiology) are scored against the data. Results are ranked against published industry benchmarks (Medallia NPS 2024, ChurnZero Churn 2023).

**3. Pre-Decision Precheck** — Log a decision before you make it. SENTINEL fires a live risk assessment as you type, with specific data-backed warnings. High-risk flags go to Slack immediately.

**4. Autonomous Monitoring** — APScheduler runs every 30 minutes: Fivetran MCP syncs all connectors → BigQuery pipeline reads latest metrics → Gemini 3 analyzes patterns → early warnings post to Slack before metrics breach critical thresholds. No human action required.

**5. Ask SENTINEL** — Google ADK 2.0 agent backed by Gemini 3. Ask anything about the decision history. The agent cites specific metrics, decision IDs, and Fivetran-connected data sources in every answer.

---

### How we built it

**Fivetran MCP as the data backbone** — Fivetran's Model Context Protocol (stdio transport) is our live data layer. `list_connections` shows all connected sources, `trigger_sync` keeps data fresh before every decision is logged, and `get_connection_schema_config` tells SENTINEL what metrics exist in BigQuery. The multi-connector registry lets you register any number of BigQuery tables via environment variables (`SENTINEL_BQ_*_TABLE`), making SENTINEL data-source agnostic from day one.

**Gemini 3 — strictly enforced** — All LLM calls try Gemini 3 models first (`gemini-3-flash-preview`, `gemini-3.5-flash`, `gemini-3.1-flash-lite`) via API key. Gemini 3 is only accessible via API key mode (not Vertex AI), so we built a dedicated `_get_gemini3_client()` that routes Gemini 3 calls through the key while Vertex AI handles quota fallback. The candidate ordering is enforced in code regardless of what `GEMINI_MODEL` is set to.

**3-method causal inference battery** — We didn't want to show correlation and call it causation. Granger causality (F-test at lag 1), Interrupted Time Series (pre/post slope comparison), and Mann-Whitney U (distributional shift) run independently. Bradford Hill's 1965 epidemiological criteria are then scored: strength, consistency, specificity, temporality, biological gradient, plausibility, coherence, experiment evidence, and analogy. The score produces a "causal strength" label backed by 60 years of scientific methodology.

**Real BigQuery data** — Seven rows of real metrics (NPS, churn rate, MRR, ARR) from March to July 2026 drive all analysis. The decision index is at row 2 (June 3, 2026). Every chart, every statistical test, every benchmark comparison runs on this real data.

**Google ADK 2.0 agent** — The `/api/agent/chat` endpoint uses Google ADK's `LlmAgent` with Gemini 3 as the backing model. A custom `InMemorySessionService` manages conversation state across turns. The agent has full scenario context injected as system instructions.

**Cloud Run deployment** — The backend runs on Cloud Run (us-central1, 1Gi RAM, 300s timeout). The read-only Cloud Run filesystem required wrapping all file writes in OSError handlers and routing `OUTPUT_DIR` to `/tmp/sentinel`.

---

### Challenges we ran into

**Gemini 3 is API-key only** — Early builds tried Gemini 3 via Vertex AI and hit 404 "model not found" errors. The fix: route Gemini 3 models through a dedicated API key client, keep Vertex AI for fallback-only. The candidate list always tries Gemini 3 first regardless of environment configuration.

**Free-tier quota (20 RPD)** — With 49 E2E tests that all call Gemini 3, we hit the 20 requests-per-day limit. The fix: detect `429 RESOURCE_EXHAUSTED` in the exception handler, add it to the fallback trigger keywords, and update tests to skip (not fail) when quota is exhausted — distinguishing quota exhaustion from code errors.

**numpy bool serialization** — `numpy.bool_` isn't JSON-serializable. `causal_tracer.py` was returning `numpy.bool_` values for significance flags. Fixed by wrapping: `bool(abs(slope_change) > abs(pre_slope) * 0.2)`.

**Cloud Run filesystem** — Cloud Run's read-only filesystem caused `output_writer.py` to crash on every request. Fixed by adding `_safe_write()` that wraps all writes in `try/except OSError`, and pointing `OUTPUT_DIR` to `/tmp/sentinel`.

**Slack 3-second response requirement** — Slack Events API requires a response within 3 seconds or it retries. The multi-agent council takes 60+ seconds. Fixed with FastAPI `BackgroundTasks`: acknowledge Slack immediately, run the 4-agent pipeline in the background.

---

### Accomplishments we're proud of

- 49 end-to-end tests, all green, covering Gemini 3 enforcement, BigQuery live data, causal inference battery, Bradford Hill 9 criteria, industry benchmarks, Slack interceptor, precheck engine, and full trace
- Bradford Hill criteria applied to business decisions — a genuine methodological contribution, not just correlation math
- The 4-agent Slack council running in real-time (verified working: all 4 agents responded within 2 minutes in live testing)
- The audit trail concept: every decision logged at the moment with a frozen snapshot of all metrics, queryable forever
- Chart.js time-series with real BigQuery data, animated dual axes, decision date overlay

---

### What we learned

Gemini 3 is fast, production-quality, and genuinely better at nuanced causal reasoning tasks than 2.5-pro in our testing — especially for the Bradford Hill scoring where the model needed to evaluate multiple criteria simultaneously with domain-specific reasoning.

Fivetran MCP's stdio transport is underrated. Having `trigger_sync` as a first-class tool means SENTINEL always has fresh data before a decision is logged — you never get a stale snapshot because the sync is built into the decision-logging workflow.

Causal inference is hard to communicate to non-statisticians. The Bradford Hill framing (named criteria, binary met/not-met, single 0-1 score) turns "we ran 3 statistical tests" into something a CEO can evaluate in 10 seconds.

---

### Built with

- Gemini 3 (gemini-3-flash-preview) via Google AI Studio API key
- Google ADK 2.0 (agent framework)
- Fivetran MCP (data sync, stdio transport)
- Google BigQuery (metrics time-series)
- Google Cloud Run (deployment)
- Google Cloud Build (CI/CD)
- FastAPI + Python 3.13
- MongoDB Atlas
- Slack Events API
- Chart.js 4.4
- scipy / numpy (statistical analysis)
- APScheduler (autonomous monitoring)

---

### Try it

**Live:** https://sentinel-38381883054.us-central1.run.app

1. Click **"Explore Demo"** → choose AcmeSaaS or Qwikster
2. Click **"Impact Trace"** → see the causal chain, Chart.js visualization, Bradford Hill scores, benchmarks
3. Click **"Log Decision"** → watch the precheck fire in real-time as you type
4. Click **"Ask SENTINEL"** → ask "why did churn spike?" and get a sourced answer
