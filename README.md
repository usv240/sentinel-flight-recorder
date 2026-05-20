# SENTINEL — The Business Flight Recorder

**Live:** https://sentinel-38381883054.us-central1.run.app  
**License:** Apache 2.0

Businesses forget why they made decisions. People leave, context is lost, new executives repeat old mistakes. SENTINEL records every business decision with its full Fivetran data context — so when things go wrong, you can trace exactly why.

---

## The Problem

In 2026, every AI agent has a flight recorder. But the humans making billion-dollar decisions? Still nothing.

When a pricing change causes churn three months later, nobody remembers what the data looked like on the day the decision was made. The warning was there. Nobody connected the dots.

SENTINEL fixes that.

---

## What It Does

**Records decisions automatically** — Fivetran MCP triggers a live sync across all connected sources before every decision is captured. A full metrics snapshot is frozen at the exact moment.

**Computes real causal correlation** — Pearson r is calculated from actual weekly time-series data (scipy + numpy). Not a hardcoded number — a computed statistical finding.

**Generates AI causal narratives** — Gemini 3 writes the causal narrative and early warning text based on the real data. Every answer is freshly generated.

**Fires early warnings autonomously** — APScheduler runs a monitoring cycle every 30 minutes: Fivetran MCP → BigQuery → Gemini pattern analysis → warning detection. No user action required.

**Extracts decisions from transcripts** — Paste any meeting transcript, Slack thread, or email. Gemini 3 extracts structured decisions automatically.

**Answers "why do we do X?"** — Ask SENTINEL anything about the decision history. Full scenario context goes to Gemini 3 for every answer.

---

## Demo Scenarios

Two fully playable scenarios, no account required:

| Scenario | Story | Pearson r | Warning missed |
|---|---|---|---|
| **AcmeSaaS** | Pricing +20% → Customer X churns ($120K ARR) | r = 0.87 | 34 days |
| **Netflix Qwikster** | 60% price increase → 800K subscribers lost | r = 0.91 | Data said it coming |

---

## Stack

| Technology | Role |
|---|---|
| **Fivetran MCP** | Connects all data sources via Model Context Protocol. Triggers syncs, lists connectors, provides BigQuery destination |
| **Google Cloud Agent Builder** | Agent orchestration — see `agent/AGENT_BUILDER_SETUP.md` |
| **Gemini 3** | Causal narrative generation, decision extraction from transcripts, early warning text, Q&A |
| **BigQuery** | Metrics history from all Fivetran-connected sources — queried for live data |
| **MongoDB Atlas** | Decision document store with full context snapshots |
| **FastAPI + APScheduler** | Backend API + autonomous 30-minute monitoring loop |
| **Cloud Run** | Serverless hosting |

---

## Quick Start

**Demo mode (no credentials needed):**
```bash
git clone https://github.com/usv240/sentinel-flight-recorder
cd sentinel-flight-recorder/sentinel

# Copy example env and run
cp .env.example .env
DEMO_MODE=true uvicorn backend.main:app --port 8100
# Open http://localhost:8100
```

**Full mode (with your own Fivetran data):**

1. Sign up at [fivetran.com](https://fivetran.com) — free 14-day trial
2. Connect your data sources and set BigQuery as destination
3. Clone the Fivetran MCP server alongside this project:
   ```bash
   git clone https://github.com/fivetran/fivetran-mcp ../fivetran-mcp
   cd ../fivetran-mcp && pip install mcp httpx python-dotenv
   ```
4. Copy `.env.example` to `.env` and fill in your credentials
5. Run: `uvicorn backend.main:app --reload --port 8100`

---

## API

```
GET  /api/health                       Status + monitor state + Gemini model
GET  /api/monitor/status               Autonomous loop last run result
POST /api/monitor/run                  Trigger a monitoring cycle now
GET  /api/decisions/snapshot           Current Fivetran metrics snapshot
POST /api/decisions/log                Record a decision + live snapshot
GET  /api/decisions/list               All logged decisions
GET  /api/warnings/active              Active early warnings
POST /api/trace/analyze                Causal chain analysis
GET  /api/trace/demo/{scenario}        Demo causal trace (acmesaas|qwikster)
POST /api/ask/                         Ask about decision history
POST /api/transcript/extract           Extract decisions from transcript
GET  /api/tool-calls/recent            Recent Fivetran MCP tool calls log
GET  /api/connectors/list              Fivetran connected sources
POST /api/connectors/{id}/sync         Trigger Fivetran sync via MCP
```

---

## Deploy

Build from the parent directory (includes `fivetran-mcp/` in the container):

```bash
cd ..  # parent directory containing both sentinel/ and fivetran-mcp/
gcloud builds submit . --tag gcr.io/YOUR_PROJECT/sentinel
gcloud run deploy sentinel \
  --image gcr.io/YOUR_PROJECT/sentinel \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --env-vars-file sentinel/env-cloud.yaml
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE)
