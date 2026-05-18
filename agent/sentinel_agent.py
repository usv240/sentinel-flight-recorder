"""
SENTINEL ADK Agent — deployable to Gemini Enterprise Agent Platform (Agent Engine).

Deploy:
    pip install google-cloud-aiplatform[agent_engines,langchain]
    adk deploy --project=orace-agent --region=us-central1

This agent orchestrates:
  1. Fivetran MCP tools (list_connections, trigger_sync, get_connector_schema)
  2. SENTINEL API tools (log_decision, check_warnings, trace_causal_chain, ask_sentinel)
  3. Gemini 3 reasoning to connect data signals to business decisions
"""

import os

SENTINEL_URL = os.getenv("SENTINEL_URL", "https://sentinel-38381883054.us-central1.run.app")

SYSTEM_PROMPT = """You are SENTINEL — The Business Flight Recorder.

Your mission: record every business decision with its full Fivetran data context,
then trace what happened next. You are an autonomous agent, not a chatbot.

ALWAYS follow this order for any task:
1. Call list_fivetran_connectors to see all connected data sources
2. Call trigger_fivetran_sync to get fresh data from each active connector
3. Check the current metrics snapshot for warning flags
4. Then perform the requested action (log decision, trace outcome, answer question)
5. End with a specific recommended action and time window

WHEN LOGGING A DECISION:
- Always trigger a sync before snapshotting metrics
- Flag any metrics currently in warning territory
- Calculate: what historical patterns predict about this decision

WHEN ASKED ABOUT AN OUTCOME:
- Find all decisions made 14-90 days before the outcome appeared
- State the Pearson r correlation score and what it means
- Trace the exact causal chain: decision → signal → escalation → outcome
- State how many days of warning were available

WHEN ASKED "WHY DO WE DO X?":
- Search the decision log for the original decision
- Show all Fivetran-sourced data that existed when it was made
- Show the outcome — did it work?

TONE: Direct, urgent, specific. Cite exact metrics and dates.
Never say "I think" or "possibly" — say "the data shows" or "the pattern indicates".
Always show which Fivetran MCP tool you called. Transparency builds trust."""


def create_sentinel_agent():
    """Create and return the SENTINEL ADK agent."""
    try:
        import vertexai
        from vertexai.preview.reasoning_engines import AdkApp
        from google.adk.agents import Agent
        from google.adk.tools import OpenAPITool

        vertexai.init(
            project=os.getenv("GOOGLE_PROJECT_ID", "orace-agent"),
            location=os.getenv("GOOGLE_LOCATION", "us-central1"),
        )

        # Load SENTINEL OpenAPI spec as a tool
        import yaml
        spec_path = os.path.join(os.path.dirname(__file__), "openapi_spec.yaml")
        with open(spec_path) as f:
            spec = yaml.safe_load(f)

        sentinel_tool = OpenAPITool(
            name="sentinel_api",
            description="SENTINEL Business Flight Recorder API — log decisions, trace outcomes, check warnings, ask questions",
            spec=spec,
        )

        agent = Agent(
            name="SENTINEL",
            model=os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"),
            description="Business Flight Recorder — records decisions with Fivetran data context and traces causal chains",
            instruction=SYSTEM_PROMPT,
            tools=[sentinel_tool],
        )

        return AdkApp(agent=agent)

    except ImportError as e:
        print(f"ADK not installed: {e}")
        print("Install: pip install google-cloud-aiplatform[agent_engines]")
        return None


if __name__ == "__main__":
    app = create_sentinel_agent()
    if app:
        print("SENTINEL ADK agent created successfully.")
        print("Deploy with: adk deploy --project=orace-agent --region=us-central1")
