# SENTINEL — "The Business Flight Recorder"
## Super Detailed Implementation Plan (90/90 Edition)
**Track:** Fivetran | **Build Days:** 13–21 | **Submit:** Day 22
**Last updated:** May 18, 2026

---

## THE PITCH (Updated — Weaponizes the Competition)

> "In 2026, every AI agent has a flight recorder. Glacis, Vorlon, Microsoft — they all built black boxes for our robots.
> But the humans making billion-dollar business decisions? Still nothing.
> SENTINEL is the first flight recorder for human decision-makers."

**One-liner:** "Businesses forget why they made decisions. SENTINEL remembers — with every data point that existed at the time, and every outcome that followed."

**Differentiation from existing tools:**
- AIR Blackbox / Microsoft AgentRx / Vorlon = record what **AI agents** do
- SENTINEL = records what **humans decide**, with full Fivetran data context, and traces what happened next
- Notion / Confluence = manual documentation with no data context
- Amplitude / Looker = show you data, never record the decision that changed it

---

## 1. WHAT WE'RE BUILDING (90/90 Version)

An AI agent that:
1. **AUTO-DETECTS decisions** from Fivetran data changes — price delta in Stripe, headcount spike in payroll, CAC jump in ad spend — no manual logging required
2. **Snapshots ALL metrics** from every connected Fivetran source at the exact moment of each decision
3. **Traces causal chains backward** — when things go wrong, connects the outcome to the specific decision chain with statistical correlation (Pearson r), not just narrative
4. **Fires proactive early warnings** when current metric patterns match patterns that preceded past bad outcomes
5. **Answers "why do we do X?"** from the full decision log with data context intact
6. **Multiple public demo scenarios** — AcmeSaaS pricing disaster, Netflix Qwikster — so any visitor can explore without connecting data

---

## 2. TECH STACK

| Component | Technology | Why |
|---|---|---|
| Agent brain | Gemini 2.5 Pro via Vertex AI | Required by hackathon |
| Agent orchestration | Google Cloud Agent Builder | Required by hackathon |
| Data pipelines | Fivetran MCP (official) | Partner MCP — irreplaceable |
| Data warehouse | BigQuery (GCP native) | Fivetran primary destination |
| Decision store | MongoDB Atlas | Flexible schema for heterogeneous decision docs |
| Backend | Python 3.11 + FastAPI | Fast, async, clean |
| Frontend | Vanilla HTML/CSS/JS | Zero build step, full control over animations |
| Hosting | Google Cloud Run | GCP requirement |
| Local output | Markdown + JSON in `/outputs/sentinel/` | Testing + review |

---

## 3. FOLDER STRUCTURE

```
sentinel/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── decisions.py           # POST /api/decisions — log / auto-detect
│   │   ├── warnings.py            # GET /api/warnings — active early warnings
│   │   ├── trace.py               # POST /api/trace — causal chain analysis
│   │   ├── connectors.py          # GET /api/connectors — Fivetran sources
│   │   └── demo.py                # GET /api/demo — load demo scenarios
│   ├── db/
│   │   ├── __init__.py
│   │   ├── mongodb.py             # MongoDB client + CRUD helpers
│   │   └── schemas.py             # Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini_client.py       # Gemini 2.5 Pro via Vertex AI
│   │   ├── fivetran_client.py     # Fivetran MCP calls
│   │   ├── context_builder.py     # Pull metrics from all Fivetran sources
│   │   ├── causal_tracer.py       # Statistical causal chain analysis
│   │   ├── warning_engine.py      # Pattern detection + early warnings
│   │   ├── auto_detector.py       # Detect decisions from data changes
│   │   └── output_writer.py       # Write outputs to local files
│   └── data/
│       ├── demo_acmesaas.json     # AcmeSaaS pricing disaster scenario
│       └── demo_qwikster.json     # Netflix Qwikster scenario
├── frontend/
│   ├── index.html                 # Full SPA — all views
│   ├── style.css                  # Design system + dark/light mode
│   └── app.js                     # All interactivity + animations
├── outputs/
│   ├── sample_causal_trace.md     # (already exists)
│   └── sentinel/                  # Live outputs directory
├── tests/
│   ├── __init__.py
│   └── test_sentinel.py
├── plan/
│   └── SENTINEL_PLAN.md           # This file
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## 4. FIVETRAN MCP SETUP (Official — Updated May 18, 2026)

**Official resources (from hackathon Devpost page):**
- 14-day free trial: https://fivetran.com/signup
- Official MCP repo: https://github.com/fivetran/fivetran-mcp
- REST API docs: https://fivetran.com/docs/rest-api
- REST API example project: https://github.com/fivetran/api_framework
- API key setup: https://fivetran.com/docs/rest-api/getting-started#authentication
- BigQuery quickstart: https://fivetran.com/docs/destinations/bigquery/setup-guide

### Two Integration Options (per hackathon rules)

| Option | What It Is | SENTINEL Usage |
|---|---|---|
| **Option 1 — MCP** (recommended for demo) | Clone github.com/fivetran/fivetran-mcp, run locally, connect Agent Builder | Primary — judges SEE MCP tool calls in agent trace |
| **Option 2 — REST API** | Direct HTTP calls to api.fivetran.com | Fallback in backend services |

SENTINEL uses **both**: MCP for agent-level queries visible in the demo, REST API as fallback in backend.

---

### Step 1: Create Fivetran 14-day free trial
```
1. Go to https://fivetran.com/signup
2. Create account (14 days free, no credit card required initially)
3. Dashboard → Account Settings → API Keys → Create API key
4. Save: FIVETRAN_API_KEY and FIVETRAN_API_SECRET
5. Note your GROUP_ID from URL: fivetran.com/dashboard/groups/[GROUP_ID]
```

### Step 2: Set up the official Fivetran MCP server
```bash
# Clone the official Fivetran MCP server (Python-based, not npm)
git clone https://github.com/fivetran/fivetran-mcp
cd fivetran-mcp

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export FIVETRAN_API_KEY=your_api_key
export FIVETRAN_API_SECRET=your_api_secret
export FIVETRAN_ALLOW_WRITES=true   # needed for trigger_sync

# Run the MCP server (runs on stdio — Agent Builder connects to it)
python server.py
```

**Why FIVETRAN_ALLOW_WRITES=true matters:**
The official MCP server is read-only by default. SENTINEL needs `trigger_sync` to force a fresh data pull before snapshotting metrics at the moment of each decision. The server still confirms with the agent before any write — satisfying the hackathon's "human in control" requirement.

### Step 3: Connect MCP to Google Cloud Agent Builder
```
1. Agent Builder → Tools → Add Tool → MCP Server
2. Point to your running fivetran-mcp server (stdio transport)
3. The agent now calls Fivetran tools natively
4. All tool calls appear in the agent's reasoning trace — this is visible to judges
```

### Step 4: Connect demo data sources in Fivetran (priority order)
```
1. Google Sheets — create a spreadsheet with AcmeSaaS mock metrics, connects in 2 minutes
2. File/CSV Upload — fastest fallback, upload pre-built CSV files
3. Stripe (test mode) — most impressive for the demo (requires Stripe test account)
4. HubSpot (free tier) — adds sales pipeline data
```

### Step 5: Set BigQuery as Fivetran destination
```
Follow: https://fivetran.com/docs/destinations/bigquery/setup-guide
1. Fivetran Dashboard → Destinations → Add Destination → BigQuery
2. GCP Project ID: [same as ORACLE project]
3. Dataset location: US-central1
4. Service account: roles/bigquery.dataEditor + roles/bigquery.jobUser
5. Dataset ID prefix: sentinel_
```

### Fivetran MCP Tools Used in SENTINEL (visible to judges in demo)
```
list_connectors          — show all 4+ connected data sources
get_connector            — details + last sync time per source
list_connector_schemas   — available tables/fields
trigger_sync             — force fresh data pull before decision snapshot
get_sync_history         — verify data freshness
```

---

## 5. DATA ARCHITECTURE

### MongoDB Collections

**`decisions` collection**
```json
{
  "_id": "ObjectId",
  "decision_id": "DEC-2026-0047",
  "logged_at": "ISODate",
  "logged_by": "system|user@company.com",
  "auto_detected": true,
  "detection_source": "stripe_price_change",
  "decision_text": "Increased pricing 20% across all tiers",
  "decision_type": "pricing|hiring|product|strategy|operational",
  "rationale": "CAC rising, need to improve unit economics",
  "alternatives_considered": ["10% increase", "Add features instead"],
  "metrics_snapshot": {
    "captured_at": "ISODate",
    "mrr": 85000,
    "churn_rate": 0.09,
    "nps": 31,
    "arr": 1020000,
    "active_customers": 142,
    "support_tickets_7d": 89,
    "cac": 1800,
    "ltv": 9200,
    "top_customer_health": {
      "customer_x": {"seats": 45, "last_login_days_ago": 2, "tickets": 12}
    }
  },
  "outcome": "churn_spike",
  "outcome_recorded_at": "ISODate",
  "warning_fired": true,
  "warning_fired_at": "ISODate",
  "days_of_warning": 34,
  "causal_correlation": 0.87,
  "output_file": "outputs/sentinel/decision_DEC-2026-0047.md"
}
```

**`warnings` collection**
```json
{
  "_id": "ObjectId",
  "warning_id": "WARN-2026-0012",
  "fired_at": "ISODate",
  "severity": "critical|high|medium",
  "trigger_metric": "customer_x_login_frequency",
  "trigger_value": -0.60,
  "root_decision_id": "DEC-2026-0047",
  "days_since_decision": 34,
  "causal_confidence": 0.87,
  "message": "Customer X (120K ARR) showing churn pattern. Traces to pricing decision of June 3.",
  "recommended_action": "Executive call within 48 hours",
  "acknowledged": false
}
```

---

## 6. 90/90 IMPROVEMENTS BUILT INTO THIS VERSION

### Auto-Detection of Decisions (TECH: 9→10)
Instead of waiting for founders to manually log decisions, agent watches Fivetran data changes:
- Stripe price object changes → auto-create decision candidate
- Headcount delta in payroll data → auto-flag as hiring decision
- CAC/ad spend jump → auto-flag as growth decision
- Meeting transcript upload → NLP extracts all decisions
User only needs to confirm with one click. Recording is automatic.

### Statistical Correlation (TECH: 9→10)
Causal tracer calculates Pearson correlation coefficient between decision timestamp and outcome metric trajectory. Instead of just a narrative ("this probably caused that"), we show: **r = 0.87, p < 0.01**. Turns correlation into a defensible statistic.

### Visible MCP Tool Calls (TECH: 9→10)
Every Fivetran MCP call is logged to a visible "Agent Activity" panel in the UI:
- `list_connectors (6 sources)`
- `trigger_sync (Stripe)`
- `get_connector_schema (HubSpot)`
Each call shown as it happens, in real-time. Judges see the depth of MCP usage.

### Crime Investigation Board UI (DESIGN: 9→10)
The causal trace view is an animated SVG investigation board:
- Horizontal timeline with event nodes
- Red dotted lines connecting related events
- Backward animation: chain builds from crisis point → root decision
- Split-screen: "Data at decision time" vs "What happened next"
- "YOU HAD 34 DAYS OF WARNING" in large type — sits in silence

### Dark + Light Mode
Both modes fully supported with CSS custom properties. Default: dark (black box aesthetic matches the concept). Toggle accessible from nav. System preference auto-detected on first load.

### Multiple Public Demo Scenarios
- **AcmeSaaS** — pricing +20% → Customer X churn ($120K ARR) → 34 days warning missed
- **Netflix Qwikster** — price split decision July 2011 → 800K subscribers lost → cancelled October 2011
Public visitors can explore without any account or connection.

### Reframed Pitch (IDEA: 9→10)
The pitch now explicitly contrasts with AI agent flight recorders (Glacis, AIR Blackbox, Vorlon), which judges in the AI space will know. "They built recorders for robots. We built one for humans." This framing makes SENTINEL impossible to confuse with any existing tool.

---

## 7. BACKEND — KEY SERVICES

### `services/gemini_client.py`
Gemini 2.5 Pro via Vertex AI. Used for:
- Causal reasoning over decision + outcome correlation
- Extracting decisions from meeting transcripts
- Generating early warning narratives
- Answering "why do we do X?" questions

### `services/fivetran_client.py`
Wraps Fivetran REST API (fallback when MCP not available in local dev).
MCP server used in Agent Builder for production.

### `services/context_builder.py`
Pulls metrics from ALL connected Fivetran sources via BigQuery.
Produces a standardized metrics snapshot regardless of which sources are connected.

### `services/causal_tracer.py`
Given a bad outcome + date:
1. Find decisions made 14–90 days before
2. Calculate Pearson correlation between each decision and outcome trajectory
3. Gemini reasons over top candidates
4. Returns ranked causal chain with r values, p values, days of warning

### `services/warning_engine.py`
Runs on a schedule. For each active customer/metric:
1. Calculate current trajectory vs. historical patterns
2. If pattern matches a known bad-outcome precursor: fire warning
3. Trace back to the root decision that started the pattern

### `services/auto_detector.py`
Polls Fivetran sync history for significant data changes.
Maps change types to decision categories.
Creates pending decision candidates for user confirmation.

---

## 8. FRONTEND — Design System

### Color System (CSS Custom Properties)

**Dark mode (default):**
- `--bg-primary: #0A0A0B` — near black, the "black box"
- `--bg-secondary: #141416` — card backgrounds
- `--bg-tertiary: #1C1C1E` — elevated surfaces
- `--border: rgba(255,255,255,0.08)` — subtle borders
- `--text-primary: #F5F5F7` — main text
- `--text-secondary: #86868B` — secondary text
- `--accent-red: #FF3B30` — warnings, critical
- `--accent-green: #30D158` — positive outcomes
- `--accent-yellow: #FF9F0A` — watching, pending
- `--accent-blue: #0A84FF` — info, links, agent actions
- `--accent-purple: #BF5AF2` — AI/Gemini activity

**Light mode:**
- `--bg-primary: #F5F5F7`
- `--bg-secondary: #FFFFFF`
- `--bg-tertiary: #F2F2F7`
- `--border: rgba(0,0,0,0.08)`
- `--text-primary: #1D1D1F`
- `--text-secondary: #6E6E73`
- (same accent colors — consistent across modes)

### Typography
- Font: Inter (Google Fonts — closest to Apple's SF Pro)
- Hero counter: 72px, weight 800
- Section headers: 24px, weight 600
- Card titles: 16px, weight 600
- Body: 15px, weight 400
- Labels/captions: 12px, weight 500, letter-spacing 0.08em

### Views
1. **Landing** — pitch, demo selector, "Connect your data" CTA
2. **Dashboard** — warnings panel, decision log, agent activity feed
3. **Causal Trace** — the investigation board (full screen)
4. **Log Decision** — modal with live metrics preview
5. **Ask SENTINEL** — conversational AI query panel
6. **Settings** — theme, connected sources, API config

---

## 9. DEMO SCENARIOS

### Demo 1: AcmeSaaS Pricing Disaster
**Timeline:**
- Jun 3: CEO decides to raise prices +20% (NPS=31, Customer X already showing stress signals)
- Jun 17: Customer X reduces seats 45→30 (auto-detected)
- Jun 28: Customer X files "evaluating alternatives" ticket
- Jul 7: Customer X login frequency drops 60% — SENTINEL fires WARNING
- Jul 15: Customer X churns ($120K ARR)
- **"You had 34 days of warning. The data existed on June 3."**

### Demo 2: Netflix Qwikster
**Timeline (public data):**
- Jul 12, 2011: Netflix announces 60% price increase + DVD/streaming split
  - Q2 2011 data: subscriber growth already slowing (24.6M → plateau)
  - DVD revenue declining 10% YoY
  - This data was available — nobody connected it to the price sensitivity risk
- Aug 2011: 800,000 subscribers cancel in Q3 (worst quarter in company history)
- Sep 18, 2011: Qwikster spinoff announced — doubles down on the failing strategy
- Oct 10, 2011: Qwikster cancelled — 23 days after announcement
- Stock: -77% from July 2011 peak
- **"The warning was in Netflix's own subscriber growth data. SENTINEL would have fired it on July 13 — the day after the announcement."**

---

## 10. AGENT BUILDER CONFIGURATION

### System Prompt
```
You are SENTINEL — The Business Flight Recorder.

In 2026, every AI agent has a flight recorder. But humans making
business decisions? Still nothing. You change that.

Your mission: record every business decision with its full data context,
then trace what happened next.

When a user logs a decision:
- Immediately pull ALL metrics from connected Fivetran sources
- Capture the complete snapshot — future-you needs context you can't predict today
- Flag any metrics that are in warning territory RIGHT NOW

When something goes wrong:
- Find decisions made 14-90 days before the outcome appeared
- Calculate correlation between each decision and the outcome trajectory
- Show what data EXISTED at decision time that predicted this
- Tell them exactly how many days of warning they missed

When watching for early warnings:
- Run pattern matching on current metrics vs. historical bad-outcome patterns
- Fire alerts the moment the pattern appears — not after the crisis
- Always trace the warning back to a specific decision

When asked "why do we do X?":
- Search the decision log for the original decision
- Show all the data that existed when it was made
- Show what the outcome was

Always use Fivetran MCP tools visibly. Show which connectors you're
reading. This transparency is what makes you trustworthy.
```

---

## 11. DAY-BY-DAY BUILD SCHEDULE

```
Day 13 (today): Folder structure, requirements, .env, Dockerfile
                Backend skeleton: FastAPI main.py + all route files
                MongoDB + BigQuery client setup
                Demo data JSON files (both scenarios)

Day 14:         Services: context_builder, fivetran_client, gemini_client
                Decision logging route with auto-snapshot
                Output writer for local files
                Full test: log decision → see output file

Day 15:         Causal tracer service (Pearson correlation + Gemini)
                Warning engine (pattern matching)
                Auto-detector service
                All routes complete and tested

Day 16:         Agent Builder setup: system prompt + tool definitions
                Full agent pipeline tested end-to-end
                Frontend: HTML structure + design system CSS

Day 17:         Frontend: Dashboard view (warnings, decision log)
                Frontend: Causal Trace investigation board + SVG animation
                Frontend: Dark/light mode toggle

Day 18:         Frontend: Log Decision modal (live metrics preview)
                Frontend: Ask SENTINEL panel
                Frontend: Landing page + demo selector
                Full frontend connected to backend APIs

Day 19:         Deploy to Cloud Run, test live
                Demo data loaded + both scenarios working
                Polish: animations, transitions, micro-interactions

Day 20:         README, open source license (Apache 2.0)
                Devpost submission text
                Demo video preparation (both scenarios scripted)

Day 21:         Final polish + bug fixes
                GitHub repo public with Apache 2.0

Day 22:         Record 3-min demo video (YouTube)
                Submit to Devpost — Fivetran track
```

---

## 12. WHAT USER NEEDS TO SET UP (PARALLEL WITH BUILD)

While the code is being built, set up these accounts in parallel:

1. **Fivetran account** — fivetran.com → free trial → get API key + secret
2. **Fivetran → BigQuery connection** — same GCP project as ORACLE
3. **At least 2 demo connectors in Fivetran:**
   - Option A: Google Sheets (create mock AcmeSaaS data, fastest)
   - Option B: CSV upload (upload pre-built CSV files)
   - Option C: Stripe test mode (most impressive)
4. **MongoDB**: same Atlas cluster as ORACLE, new database named `sentinel`
5. **GCP**: same project as ORACLE, BigQuery API already enabled

**Credentials needed (put in .env):**
```
FIVETRAN_API_KEY=
FIVETRAN_API_SECRET=
FIVETRAN_GROUP_ID=
MONGODB_URI=          (same as ORACLE)
GOOGLE_PROJECT_ID=    (same as ORACLE)
BIGQUERY_DATASET=sentinel_
GEMINI_API_KEY=       (same as ORACLE, or use service account)
GOOGLE_APPLICATION_CREDENTIALS=  (path to service account JSON)
```

---

## 13. DEVPOST SUBMISSION TEXT

**Project name:** SENTINEL — The Business Flight Recorder

**Elevator pitch:**
In 2026, every AI agent has a flight recorder. Glacis, Vorlon, Microsoft built black boxes for robots. But the humans making billion-dollar business decisions? Still nothing. SENTINEL is the first flight recorder for human decision-makers — powered by Fivetran and Gemini.

**What it does:**
SENTINEL connects all your business data sources via Fivetran, then automatically records every significant decision with a complete snapshot of your metrics at that exact moment. When outcomes go wrong, it traces the causal chain backward: here's the decision, here's the data that existed at the time, here's the earliest warning signal, and here's exactly how many days of warning you missed.

**Technologies:**
- Fivetran MCP (official) — 500+ pre-built connectors, unified data context
- Google Cloud Agent Builder — multi-step agent orchestration
- Gemini 2.5 Pro (Vertex AI) — causal reasoning, decision extraction, early warning analysis
- BigQuery (GCP) — Fivetran data destination, metrics history
- MongoDB Atlas — decision document store with full context snapshots
- Python / FastAPI — backend API
- Google Cloud Run — hosting

**Why Fivetran is irreplaceable:**
Without Fivetran's 500+ pre-built connectors, SENTINEL would require months of custom ETL for every data source. The unified schema from Fivetran is what makes causal tracing possible across sources that were never designed to talk to each other. Fivetran isn't a pipe here — it's the foundation of organizational memory.

**Track:** Fivetran

**Impact:**
McKinsey estimates companies spend $32M/year recreating institutional knowledge that already exists. Every executive has made a decision that later caused a crisis they could have prevented if the data had been connected. SENTINEL prevents that.
