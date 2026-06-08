# SENTINEL × Google Cloud Agent Builder

SENTINEL connects to Google Cloud Agent Builder two different ways. You only
need one, but both are wired up and ready to go.

> Google Cloud Agent Builder is the umbrella for Google's agent stack — it
> includes the **Agent Development Kit (ADK)**, **Agent Engine** (the managed
> runtime), and **Agent Studio** (the console). SENTINEL is built on **ADK**
> and also exposes a standards-compliant **MCP Streamable HTTP server**, so its
> Fivetran tools can be plugged straight into Agent Studio.

---

## Path A — ADK agent deployed to Vertex AI Agent Engine (strongest)

The same ADK agent that powers `/api/agent/chat` deploys to **Vertex AI Agent
Engine**, Agent Builder's managed runtime.

```bash
pip install "google-cloud-aiplatform[adk,agent_engines]"
gcloud auth application-default login

python agent_engine_deploy.py \
  --project  $GOOGLE_PROJECT_ID \
  --location us-central1 \
  --bucket   gs://YOUR-STAGING-BUCKET
```

After deploy, the agent shows up live in **Google Cloud Console → Vertex AI →
Agent Builder / Agent Engine** — running on Google's managed infrastructure,
not just calling an API from a script.

> Agent Engine runs on Vertex AI, which serves Gemini 2.5; Gemini 3 (preview) is
> API-key only, so the managed agent uses the Vertex tier. The local API path still
> prefers Gemini 3 — both share the same tools and model tiers (single source of
> truth in `gemini_client`).

---

## Path B — Connect SENTINEL's MCP server in Agent Studio (no-code)

SENTINEL exposes an **MCP Streamable HTTP server** (spec `2025-03-26`) so Agent
Studio can consume its Fivetran tools directly.

1. **Endpoint:** `https://<your-cloud-run-url>/api/mcp`
   - `GET /api/mcp` → discovery (server info + tool catalogue)
   - `POST /api/mcp` → JSON-RPC (`initialize`, `tools/list`, `tools/call`)
2. In **Agent Studio** (Vertex AI Agent Builder console), create an agent →
   **Tools → Add MCP server** → paste the URL above.
3. The 9 SENTINEL tools become available to the Agent Builder agent:
   `list_fivetran_connectors`, `trigger_fivetran_sync`, `get_fivetran_schema`,
   `get_metrics_snapshot`, `check_early_warnings`, `log_decision`,
   `trace_causal_chain`, `ask_sentinel`, `run_monitoring_cycle`.

---

## Verify the MCP endpoint (works before any console step)

```bash
BASE=https://<your-cloud-run-url>   # or http://127.0.0.1:8101 locally

# 1. Discovery (GET)
curl $BASE/api/mcp

# 2. Initialize (POST)
curl -X POST $BASE/api/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'

# 3. List tools (expect 9)
curl -X POST $BASE/api/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

# 4. Call a tool
curl -X POST $BASE/api/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_fivetran_connectors","arguments":{}}}'
```

Automated check: `python -m pytest tests/test_new_features.py -k McpHttp -v`

---

## How it all fits together

| Piece | What SENTINEL does |
|---|---|
| Model | `gemini-3-flash-preview` by API key, with an automatic fallback to `gemini-2.5` on Vertex AI |
| Agent framework | Built on **ADK**, deployable to **Agent Engine** (Path A) and reachable from **Agent Studio** over MCP (Path B) |
| Partner MCP server | Talks to `fivetran-mcp` (stdio) for its own tools, and re-exposes those same tools over MCP HTTP for other agents to use |
| Multi-step reasoning | The agent returns a visible `tool_trace` — you can watch it go list → sync → snapshot → trace, not just a single answer |
