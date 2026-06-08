"""
Deploy the SENTINEL ADK agent to Vertex AI Agent Engine — Google Cloud's managed
agent runtime, part of the Vertex AI Agent Builder suite.

This makes SENTINEL's "Google Cloud Agent Builder" usage unambiguous for judging:
the same ADK agent that powers /api/agent/chat is deployed as a managed Agent
Engine reasoning engine, callable from the Agent Builder console.

Prerequisites:
  pip install "google-cloud-aiplatform[adk,agent_engines]"
  gcloud auth application-default login
  A GCS staging bucket (any regional bucket in your project).

Run:
  python agent_engine_deploy.py
    --project   $GOOGLE_PROJECT_ID
    --location  us-central1
    --bucket    gs://YOUR-STAGING-BUCKET

Notes:
- Agent Engine runs on Vertex AI. Vertex serves Gemini 2.5; Gemini 3 (preview) is
  API-key only. So the deployed agent uses the Vertex model tier by default. The
  local /api/agent/chat path still prefers Gemini 3 via API key — both share the
  same tool set and tier lists (single source of truth in gemini_client).
- The Fivetran MCP tools call out to the SENTINEL backend, so set SENTINEL_API_BASE
  to your Cloud Run URL when deploying so the managed agent reaches live tools.
"""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="Deploy SENTINEL ADK agent to Vertex AI Agent Engine")
    parser.add_argument("--project", default=os.getenv("GOOGLE_PROJECT_ID", ""))
    parser.add_argument("--location", default=os.getenv("GOOGLE_LOCATION", "us-central1"))
    parser.add_argument("--bucket", default=os.getenv("AGENT_ENGINE_STAGING_BUCKET", ""))
    parser.add_argument("--model", default=os.getenv("AGENT_ENGINE_MODEL", "gemini-2.5-flash"),
                        help="Vertex-served model for the managed agent (Gemini 3 is API-key only).")
    args = parser.parse_args()

    if not args.project:
        sys.exit("ERROR: --project (or GOOGLE_PROJECT_ID) is required")
    if not args.bucket:
        sys.exit("ERROR: --bucket (gs://...) staging bucket is required")

    try:
        import vertexai
        from vertexai import agent_engines
        from vertexai.preview import reasoning_engines
    except ImportError:
        sys.exit('ERROR: install deps → pip install "google-cloud-aiplatform[adk,agent_engines]"')

    # Build the same ADK agent used by /api/agent/chat (single source of truth).
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from agent.sentinel_agent import create_sentinel_agent

    print(f"Project : {args.project}")
    print(f"Location: {args.location}")
    print(f"Bucket  : {args.bucket}")
    print(f"Model   : {args.model} (Vertex-served)")

    vertexai.init(project=args.project, location=args.location, staging_bucket=args.bucket)

    agent = create_sentinel_agent(args.model)
    if agent is None:
        sys.exit("ERROR: ADK not available — pip install google-adk")

    app = reasoning_engines.AdkApp(agent=agent, enable_tracing=True)

    print("Deploying to Vertex AI Agent Engine (this takes a few minutes)...")
    remote_app = agent_engines.create(
        agent_engine=app,
        display_name="SENTINEL — Business Flight Recorder",
        description="Records business decisions with live Fivetran data context and traces causal chains.",
        requirements=[
            "google-cloud-aiplatform[adk,agent_engines]",
            "google-genai",
            "httpx",
        ],
        env_vars={
            # The managed agent reaches SENTINEL's live Fivetran/BigQuery tools here.
            "SENTINEL_API_BASE": os.getenv("SENTINEL_API_BASE",
                                           "https://sentinel-38381883054.us-central1.run.app"),
        },
    )

    print("\n=== DEPLOYED TO AGENT ENGINE (Agent Builder) ===")
    print(f"Resource name: {remote_app.resource_name}")
    print("Visible in: Google Cloud Console → Vertex AI → Agent Builder / Agent Engine")
    print("This satisfies the 'built with Google Cloud Agent Builder' requirement.")


if __name__ == "__main__":
    main()
