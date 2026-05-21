FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Fivetran MCP server — bundled so the repo is self-contained
COPY fivetran-mcp/server.py ./fivetran-mcp/server.py
COPY fivetran-mcp/open-api-definitions/ ./fivetran-mcp/open-api-definitions/

# SENTINEL app
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY agent/ ./agent/

# Path to the Fivetran MCP subprocess
ENV FIVETRAN_MCP_PATH=fivetran-mcp/server.py
ENV APP_PORT=8080
EXPOSE 8080

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
