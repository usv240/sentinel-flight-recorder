# SENTINEL — The Business Flight Recorder

**Live:** https://sentinel-38381883054.us-central1.run.app
**Track:** Fivetran | Google Cloud Rapid Agent Hackathon 2026

Businesses forget why they made decisions. People leave, context is lost, new executives repeat old mistakes. SENTINEL is the flight recorder for your business — it watches every decision, connects it to real outcome data via Fivetran, and fires alerts **before** a bad call destroys revenue.

---

## The Problem

When a pricing change causes churn three months later, nobody remembers what the data looked like on the day the decision was made. The warning was there. Nobody connected the dots.

**SENTINEL fixes that.** Like a flight recorder, it captures every decision at the moment it's made — with a full snapshot of all your Fivetran-connected metrics — so when things go wrong, you can reconstruct exactly why.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SENTINEL Stack                           │
│                                                                 │
│  ┌──────────┐    ┌─────────────┐    ┌─────────────────────┐   │
│  │  Slack   │───▶│  Decision   │───▶│  Gemini 3 Council   │   │
│  │ Channel  │    │  Detector   │    │  4 parallel agents  │   │
│  └──────────┘    └─────────────┘    └──────────┬──────────┘   │
│                                                 │               │
│  ┌──────────┐    ┌─────────────┐               ▼               │
│  │ Fivetran │───▶│  BigQuery   │    ┌─────────────────────┐   │
│  │ MCP (stdio)│  │  Pipeline   │    │   Causal Analysis   │   │
│  └──────────┘    └─────────────┘    │ Granger + ITS + MWU │   │
│       │                │            └──────────┬──────────┘   │
│       ▼                ▼                       ▼               │
│  ┌──────────┐    ┌─────────────┐    ┌─────────────────────┐   │
│  │Connector │    │  Metrics:   │    │  Bradford Hill (9)  │   │
│  │ Registry │    │  NPS/Churn  │    │  Causal Strength    │   │
│  │ (multi)  │    │  MRR/ARR   │    └──────────┬──────────┘   │
│  └──────────┘    └─────────────┘              ▼               │
│                                    ┌─────────────────────┐    │
│                                    │ Industry Benchmarks │    │
│                                    │ Medallia/ChurnZero  │    │
│                                    └─────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │             FastAPI Backend (Cloud Run)                   │  │
│  │  /api/demo  /api/decisions  /api/trace  /api/slack       │  │
│  │  /api/agent/chat  /api/ask  /api/connectors              │  │
│  └─────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │           Frontend (Vanilla JS + Chart.js 4.4)            │  │
│  │  Impact Trace | Log Decision | Ask SENTINEL | Your Data   │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Fivetran MCP ──sync──▶ BigQuery ──pipeline──▶ Causal Tracer
                                                    │
                         ┌──────────────────────────┼────────────────────┐
                         ▼                          ▼                    ▼
                Granger Causality        Interrupted Time      Mann-Whitney U
                (lag-1 F-test)           Series (ITS)          (pre/post dist)
                         │                          │                    │
                         └──────────────────────────┼────────────────────┘
                                                    ▼
                                         Bradford Hill (1965)
                                         9 criteria → 0–1 score
                                         "Causal Strength" label
                                                    │
                                                    ▼
                                      Industry Benchmark Comparison
                                      Medallia NPS 2024 (n=2,847)
                                      ChurnZero Churn 2023 (n=1,200)
```

---

## Key Features

### 1. Multi-Agent Decision Council (Slack)

Post any business decision in Slack — SENTINEL convenes a 4-agent Gemini 3 council in real-time:

- **Data Agent** — pulls real BigQuery metrics and frames the data context
- **Risk Agent** — scores probability of bad outcomes based on historical patterns
- **Alternatives Agent** — proposes 3 alternative approaches with evidence
- **Lead Agent** — synthesizes all inputs into a go/no-go recommendation

Reply `PLAN` for a 30-60-90 day roadmap, `PROCEED` to log the decision, or `CANCEL` to stand down.

Decision patterns detected:
- Pricing changes ("increase prices", "raise rates by X%", "new pricing tier")
- Hiring decisions ("freeze hiring", "reduce headcount", "lay off X people")
- Product decisions ("sunset feature", "deprecate", "kill the product")
- Strategy shifts ("pivot to", "change strategy", "new market")

### 2. Impact Trace

Full causal reconstruction showing how a business decision propagated into outcome metrics:

- **Chart.js time-series** with dual Y-axes (NPS + Churn Rate), animated, decision date vertical line
- **3-method causal inference** — Granger causality, Interrupted Time Series, Mann-Whitney U
- **Bradford Hill 9-criteria** — research-validated causal strength scoring
- **Industry benchmarks** — percentile ranking vs. published 2024 SaaS data
- **Alternative explanations** — confounding factors a skeptic would raise
- **Attribution ranking** — which decision caused how much of the outcome

### 3. Pre-Decision Precheck

Log a decision before you make it — SENTINEL fires a live risk assessment as you type:
- Decision type classification
- Risk level: low / medium / high / critical
- Specific data-backed warnings
- Similar past decisions and their outcomes

### 4. Autonomous Monitoring (APScheduler)

Every 30 minutes, SENTINEL autonomously:
1. Triggers Fivetran MCP sync across all connectors
2. Pulls latest BigQuery metrics
3. Runs Gemini 3 pattern analysis
4. Fires early warnings to Slack before metrics breach critical thresholds

### 5. Fivetran Multi-Connector Registry

Any data source via Fivetran, registered via environment variables:

```bash
SENTINEL_BQ_ACMESAAS_TABLE=google_sheets.acmesaas_metrics
SENTINEL_BQ_SHOPIFY_TABLE=shopify.orders_summary
SENTINEL_BQ_STRIPE_TABLE=stripe.charges_daily
```

The `/api/connectors/list` endpoint merges live Fivetran connector state with the BigQuery registry — every data source is visible and syncable from the dashboard.

### 6. ADK Agent Chat

`/api/agent/chat` — a Google ADK 2.0 agent backed by Gemini 3, with full scenario context as tools. Ask natural language questions about the decision history; the agent cites specific metrics and decision IDs.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | **Gemini 3** (`gemini-3-flash-preview`) via API key |
| LLM Fallback | Gemini 2.5 Pro/Flash via Vertex AI (quota exhaustion only) |
| Agent Framework | Google ADK 2.0 |
| Data Sync | Fivetran MCP (stdio transport) |
| Data Warehouse | BigQuery (`google_sheets.acmesaas_metrics`) |
| Backend | FastAPI + Python 3.13 |
| Frontend | Vanilla JS + Chart.js 4.4 |
| Database | MongoDB Atlas |
| Deployment | Google Cloud Run (us-central1, 1Gi RAM) |
| CI/CD | Google Cloud Build |
| Notifications | Slack Events API + Bot |
| Scheduling | APScheduler (30-min autonomous monitoring) |
| Statistics | scipy, numpy (Granger, ITS, Mann-Whitney) |

---

## Gemini 3 — Strict Requirement

SENTINEL enforces Gemini 3 as the primary model. All models tried via API key (Vertex AI does not yet support Gemini 3):

```python
_GEMINI3_MODELS = [
    "gemini-3-flash-preview",        # primary
    "gemini-3.5-flash",              # fallback 1
    "gemini-3.1-flash-lite",         # fallback 2
    "gemini-3.1-flash-lite-preview", # fallback 3
]
# Vertex AI used only when ALL Gemini 3 quota exhausted (20 RPD free tier)
_VERTEX_FALLBACK = ["gemini-2.5-pro", "gemini-2.5-flash"]
```

The active model is always reported in `/api/health` as `gemini_model`. Gemini 3 models are tried first regardless of `GEMINI_MODEL` env var settings.

---

## Causal Analysis — How It Works

### 3-Method Statistical Battery

1. **Granger Causality** — lag-1 F-test: does decision timing predict metric changes better than chance? Reports F-statistic and p-value.
2. **Interrupted Time Series (ITS)** — measures slope change before vs. after the decision date. Tests if the trend meaningfully shifted.
3. **Mann-Whitney U** — distributional test: are post-decision values drawn from a statistically different distribution than pre-decision values?

All three methods must agree (or disagree) — SENTINEL reports each independently, not just an aggregate.

### Bradford Hill (1965) Criteria

Nine criteria for causal inference in medicine, applied to business decisions:

| # | Criterion | What SENTINEL Checks |
|---|-----------|---------------------|
| 1 | Strength | Effect size vs. baseline variance |
| 2 | Consistency | Pattern reproduced across multiple metrics |
| 3 | Specificity | Decision timing aligns with outcome onset |
| 4 | Temporality | Decision provably precedes the outcome |
| 5 | Biological Gradient | Larger/faster decisions → larger effects |
| 6 | Plausibility | Business mechanism is logically coherent |
| 7 | Coherence | Consistent with broader historical data |
| 8 | Experiment | Evidence from reversal or natural experiment |
| 9 | Analogy | Similar past decisions had similar outcomes |

**Score ≥ 0.7** → "Strong causal evidence" | **≥ 0.5** → "Moderate" | **< 0.5** → "Weak"

### Industry Benchmarks

Percentile ranking vs. published 2024 SaaS research:

| Metric | Source | Median | Top Quartile |
|--------|--------|--------|--------------|
| NPS | Medallia 2024 (n=2,847) | 44 | 68 |
| Churn Rate | ChurnZero 2023 (n=1,200) | 6.5% | 4.2% |

---

## Demo Scenarios

Two fully playable scenarios, no account required:

| Scenario | Story | Bradford Hill | Warning missed |
|----------|-------|---------------|----------------|
| **AcmeSaaS** | Pricing +20% → Churn 14%, NPS 24 | 6/9 criteria, 74% | 34 days |
| **Netflix Qwikster** | 60% price increase → 800K subscribers lost | 7/9 criteria, 81% | 90 days |

Both scenarios are driven by real BigQuery data (7 rows, Mar–Jul 2026).

---

## Quick Start

**Demo mode:**
```bash
git clone https://github.com/usv240/sentinel-flight-recorder
cd sentinel-flight-recorder/sentinel
pip install -r requirements.txt
cp .env.example .env   # fill in GEMINI_API_KEY at minimum
python -m uvicorn backend.main:app --port 8100
# Open http://localhost:8100 → click "Explore Demo"
```

**Full mode (your own Fivetran data):**
```bash
# 1. Connect a data source at fivetran.com → set BigQuery as destination
# 2. Clone the Fivetran MCP server
git clone https://github.com/fivetran/fivetran-mcp ../fivetran-mcp
pip install -r ../fivetran-mcp/requirements.txt

# 3. Set environment variables (see below)
# 4. Register your BigQuery tables
export SENTINEL_BQ_YOURAPP_TABLE=your_schema.your_metrics_table

# 5. Run
python -m uvicorn backend.main:app --reload --port 8100
```

---

## Environment Variables

```env
# Required
GEMINI_API_KEY=...              # Google AI Studio API key (for Gemini 3)
GOOGLE_PROJECT_ID=...           # GCP project (BigQuery + Vertex AI fallback)
GOOGLE_LOCATION=us-central1

# Gemini model (Gemini 3 enforced regardless)
GEMINI_MODEL=gemini-3-flash-preview

# Fivetran MCP
FIVETRAN_API_KEY=...
FIVETRAN_API_SECRET=...
FIVETRAN_GROUP_ID=...
FIVETRAN_MCP_PATH=../fivetran-mcp/server.py

# MongoDB
MONGODB_URI=...
MONGODB_DATABASE=sentinel_db

# Slack (optional — enables Decision Council and autonomous alerts)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0...

# BigQuery connector registry (add as many as you need)
SENTINEL_BQ_ACMESAAS_TABLE=google_sheets.acmesaas_metrics
# SENTINEL_BQ_SHOPIFY_TABLE=shopify.orders_daily

# App
APP_PORT=8100
OUTPUT_DIR=/tmp/sentinel        # Use /tmp on Cloud Run (read-only filesystem)
```

---

## API Reference

```
GET  /api/health                       Status, Gemini model active, monitor state
GET  /api/monitor/status               Autonomous loop last run result
POST /api/monitor/run                  Trigger monitoring cycle now
GET  /api/decisions/snapshot           Current Fivetran metrics snapshot
POST /api/decisions/log                Record decision + live snapshot
GET  /api/decisions/list               All logged decisions
GET  /api/warnings/active              Active early warnings
POST /api/trace/analyze                Causal chain analysis
GET  /api/demo/{scenario}/full         Full trace: BigQuery + causal + Bradford Hill + benchmarks
POST /api/ask/                         Ask about decision history (ADK agent)
POST /api/agent/chat                   Google ADK agent chat endpoint
POST /api/transcript/extract           Extract decisions from meeting transcript
GET  /api/connectors/list              Fivetran + BigQuery registry combined
POST /api/connectors/{id}/sync         Trigger Fivetran sync via MCP
POST /api/slack/events                 Slack Events API endpoint (URL verification + messages)
```

---

## Tests

49 end-to-end tests covering the full stack with real API calls:

```bash
# Full suite (~6 min — makes real Gemini 3, BigQuery, and Slack API calls)
python -m pytest tests/test_e2e.py -v

# Fast (no live Cloud Run calls)
python -m pytest tests/test_e2e.py -v -k "not live"

# Individual suites
python -m pytest tests/test_e2e.py -v -k "TestGemini3"         # 6 tests
python -m pytest tests/test_e2e.py -v -k "TestBigQuery"        # 6 tests
python -m pytest tests/test_e2e.py -v -k "TestCausalInference" # 6 tests
python -m pytest tests/test_e2e.py -v -k "TestBradfordHill"    # 7 tests
python -m pytest tests/test_e2e.py -v -k "TestIndustryBenchmarks" # 6 tests
python -m pytest tests/test_e2e.py -v -k "TestSlackInterceptor"   # 6 tests
python -m pytest tests/test_e2e.py -v -k "TestPrecheckEngine"     # 4 tests
python -m pytest tests/test_e2e.py -v -k "TestFullTrace"          # 5 tests
python -m pytest tests/test_e2e.py -v -k "TestSlackEventsRoute"   # 3 tests
```

All 49 tests pass. The `test_gemini3_model_active_is_gemini3` test skips gracefully when the free-tier 20 RPD quota is exhausted — this is not a code failure, just daily quota behavior.

---

## Deploy to Cloud Run

```powershell
# Windows
cd sentinel
.\deploy.ps1
```

```bash
# Or manually
cd sentinel
gcloud builds submit --tag gcr.io/YOUR_PROJECT/sentinel .
gcloud run deploy sentinel \
  --image gcr.io/YOUR_PROJECT/sentinel \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --timeout 300 \
  --env-vars-file env-cloud.yaml
```

**env-cloud.yaml** (gitignored — contains real credentials):
```yaml
GEMINI_MODEL: "gemini-3-flash-preview"
OUTPUT_DIR: "/tmp/sentinel"
SENTINEL_BQ_ACMESAAS_TABLE: "google_sheets.acmesaas_metrics"
# ... other credentials
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE)
