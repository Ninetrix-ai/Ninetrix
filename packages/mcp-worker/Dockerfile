FROM python:3.12-slim

# Node.js is needed for npx-based MCP servers (the majority of the ecosystem)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY . .

# Default config path — mount or override with MCP_WORKER_CONFIG
ENV MCP_WORKER_CONFIG=/app/mcp-worker.yaml

CMD ["python", "main.py"]
