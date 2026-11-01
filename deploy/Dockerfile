# AgentPub — production image
#
# Single-file FastAPI app + SQLite. No build step, no bundler, no Node.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    AGENTPUB_HOST=0.0.0.0 \
    AGENTPUB_PORT=7701 \
    AGENTPUB_DATA_DIR=/data

WORKDIR /app

# curl is used by the healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py mcp_server.py server.json ./
COPY tests/ ./tests/

# SQLite lives on a volume, never in the image
RUN mkdir -p /data && useradd --system --uid 10001 agentpub && chown -R agentpub:agentpub /app /data
USER agentpub

VOLUME ["/data"]
EXPOSE 7701

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:7701/healthz || exit 1

CMD ["python", "app.py"]
