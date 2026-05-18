# SENTINEL — Google Cloud Agent Builder Setup

## Step 1: Open Agent Builder
Go to: https://console.cloud.google.com/agent-builder?project=orace-agent

## Step 2: Create a new Agent
1. Click **Create Agent**
2. Agent type: **Conversational agent**
3. Display name: `SENTINEL - Business Flight Recorder`
4. Region: `us-central1`
5. Click **Create**

## Step 3: Set the System Prompt
Paste the full contents of `agent/system_prompt.txt` into the **Agent instructions** field.

## Step 4: Connect Fivetran MCP
1. In Agent Builder → **Tools** → **Add Tool**
2. Select **OpenAPI** tool type
3. Point to your running SENTINEL backend: `https://your-cloud-run-url/api`
4. Or for local testing: use the MCP server directly

For the official Fivetran MCP:
1. Clone: `git clone https://github.com/fivetran/fivetran-mcp`
2. Run: `FIVETRAN_API_KEY=xxx FIVETRAN_API_SECRET=xxx FIVETRAN_ALLOW_WRITES=true python server.py`
3. In Agent Builder → Tools → Add MCP Tool → point to the running server

## Step 5: Add SENTINEL API as a tool
1. Agent Builder → **Tools** → **Add Tool** → **OpenAPI**
2. Upload or paste `agent/tools.json`
3. Set the server URL to your Cloud Run deployment URL

## Step 6: Test in Agent Builder playground
Try these prompts:
- "List my connected data sources"
- "What are my current business metrics?"
- "Log a decision: we are increasing prices by 20%"
- "Why did we raise prices?"
- "Check for any early warnings"
- "Trace the causal chain for the churn spike"

## Step 7: Verify MCP tool calls are visible
In the Agent Builder playground, expand the **reasoning trace** to see each tool call.
This is what judges see — make sure `list_fivetran_connectors` and `trigger_fivetran_sync` 
appear in the trace before every answer.

## Connector IDs (from your Fivetran account)
- Google Sheets connector: `humble_currently` (from URL: connections/humble_currently)
- Group ID: `about_legislation`
