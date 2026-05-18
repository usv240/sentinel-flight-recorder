# SENTINEL — The Business Flight Recorder

**Live:** https://sentinel-38381883054.us-central1.run.app

Businesses forget why they made decisions. People leave, context is lost, new executives repeat old mistakes. SENTINEL records every business decision with its full data context — so when things go wrong, you can trace exactly why.

---

## The Problem

In 2026, every AI agent has a flight recorder. But the humans making billion-dollar decisions? Still nothing.

When a pricing change causes churn three months later, nobody remembers what the data looked like on the day the decision was made. The warning was there. Nobody connected the dots.

SENTINEL fixes that.

---

## What It Does

**Records decisions automatically** — connects to your data sources via Fivetran and captures a full metrics snapshot at the exact moment each decision is made. No manual logging required.

**Traces causal chains** — when outcomes go wrong, SENTINEL calculates the statistical correlation (Pearson r) between past decisions and current outcomes. Not just narrative — actual numbers.

**Fires early warnings** — pattern-matches current metrics against historical bad-outcome patterns. Alerts you before the crisis, not after.

**Answers "why do we do X?"** — any new team member can ask why a pricing, hiring, or strategy decision was made and see exactly what the data said at the time.

---

## Demo Scenarios

Two fully playable scenarios, no account required:

| Scenario | Story | Warning |
|---|---|---|
| **AcmeSaaS** | Pricing +20% → Customer X churns ($120K ARR) | 34 days missed |
| **Netflix Qwikster** | 60% price increase → 800K subscribers lost | Data said it coming |

---

## Stack

- **Fivetran MCP** — connects all data sources, triggers syncs, unified BigQuery destination
- **Google Cloud Agent Builder** — multi-step agent orchestration
- **Gemini 2.5** — causal reasoning, decision extraction, early warning narratives
- **BigQuery** — metrics history from all Fivetran-connected sources
- **MongoDB Atlas** — decision document store with full context snapshots
- **FastAPI** — backend API
- **Google Cloud Run** — hosting

---

## Quick Start

**Demo mode (no setup needed):**
```bash
git clone https://github.com/usv240/sentinel-flight-recorder
cd sentinel-flight-recorder
pip install -r requirements.txt
DEMO_MODE=true uvicorn backend.main:app --port 8100
# Open http://localhost:8100
```

**Full mode (with your own data):**

1. Sign up at [fivetran.com](https://fivetran.com) — connect your data sources
2. Set up BigQuery as the Fivetran destination
3. Clone the official Fivetran MCP server:
   ```bash
   git clone https://github.com/fivetran/fivetran-mcp
   cd fivetran-mcp
   pip install mcp httpx python-dotenv
   FIVETRAN_API_KEY=xxx FIVETRAN_API_SECRET=xxx FIVETRAN_ALLOW_WRITES=true python server.py
   ```
4. Copy `.env.example` to `.env` and fill in your credentials
5. Run: `uvicorn backend.main:app --reload --port 8100`

---

## API

```
GET  /api/health                    Status check
GET  /api/demo/scenarios            List demo scenarios
GET  /api/demo/{scenario}/full      Full demo data
POST /api/decisions/log             Log a decision + snapshot metrics
GET  /api/warnings/active           Active early warnings
POST /api/trace/analyze             Causal chain analysis
GET  /api/trace/demo/{scenario}     Demo causal trace
POST /api/ask/                      Ask about decision history
GET  /api/connectors/list           Fivetran connected sources
```

---

## Deploy

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT/sentinel
gcloud run deploy sentinel \
  --image gcr.io/YOUR_PROJECT/sentinel \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --env-vars-file env-cloud.yaml
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE)
