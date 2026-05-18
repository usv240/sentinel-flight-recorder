# SENTINEL — Gemini Enterprise Agent Platform Setup

**Platform:** Gemini Enterprise Agent Platform (formerly Vertex AI Agent Builder)  
**Console:** https://console.cloud.google.com/agent-builder?project=orace-agent  
**Model:** Gemini 3 Flash Preview (`gemini-3-flash-preview`)

---

## Option A: Agent Studio (Visual — Fastest for Demo)

### Step 1: Open Agent Studio
1. Go to https://console.cloud.google.com/agent-builder?project=orace-agent
2. Click **Create Agent** → **Conversational agent**
3. Display name: `SENTINEL - Business Flight Recorder`
4. Model: `gemini-3-flash-preview`
5. Region: `us-central1`
6. Click **Create**

### Step 2: Paste System Prompt
Copy the full contents of `agent/system_prompt.txt` into the **Agent instructions** field.

### Step 3: Add SENTINEL API as an OpenAPI Tool
1. Agent Studio → **Tools** → **Add Tool** → **OpenAPI**
2. Upload `agent/openapi_spec.yaml`
3. Server URL: `https://sentinel-38381883054.us-central1.run.app`

### Step 4: Add Fivetran MCP as a Tool
1. Agent Studio → **Tools** → **Add Tool** → **OpenAPI**
2. The SENTINEL backend proxies MCP calls — use the `/api/connectors/*` endpoints
3. Or: run the Fivetran MCP server locally and connect via ngrok for testing

### Step 5: Test in the Playground
Try these prompts to verify the reasoning trace shows tool calls:
- `"List my connected data sources"`  
- `"What are the current business metrics?"`
- `"Log a decision: we are increasing prices by 20%"`
- `"Why did we raise prices?"`
- `"Check for early warnings"`
- `"Trace the causal chain for the churn spike"`

**Verify:** Expand the reasoning trace. You must see `list_fivetran_connectors` and 
`trigger_fivetran_sync` called before every answer. Judges check this.

---

## Option B: ADK Deploy (Code-first — Full Control)

```bash
# Install ADK
pip install google-cloud-aiplatform[agent_engines] google-adk

# Set project
gcloud config set project orace-agent

# Deploy SENTINEL agent to Agent Engine
cd sentinel/
adk deploy agent/sentinel_agent.py \
  --project=orace-agent \
  --region=us-central1 \
  --display_name="SENTINEL Business Flight Recorder"
```

The `adk deploy` command uploads `sentinel_agent.py` to Agent Engine (managed runtime).
Once deployed, the agent URL appears in the console.

---

## Connector IDs (from your Fivetran account)
- Google Sheets connector: `humble_currently`
- Group ID: `about_legislation`
- BigQuery dataset: `google_sheets.acmesaas_metrics`

---

## What Judges Will Check

1. Open Agent Studio → Playground
2. Type: `"What are the current warnings?"`
3. **Expand the reasoning trace** — must show:
   - `list_fivetran_connectors()` called first
   - `trigger_fivetran_sync()` called second  
   - `check_early_warnings()` called third
   - Gemini reasoning synthesizing the results
4. The answer must cite specific metrics and dates

If the tool calls are visible in the trace, the Technological Implementation score is high.
