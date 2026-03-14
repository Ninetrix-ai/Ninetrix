# Ninetrix

**The open standard for building and running AI agents as containers.**

`agentfile.yaml` is to AI agents what `Dockerfile` is to containers — a portable, version-controlled definition that works anywhere.

---

## Install

```bash
pip install ninetrix
# or
brew install ninetrix
# or
uv tool install ninetrix
```

## Quick Start

```bash
# Start the local stack (API, MCP gateway, dashboard)
ninetrix dev

# Scaffold a new agent
ninetrix init --name my-agent --provider anthropic

# Build and run
ninetrix build
ninetrix run
```

The dashboard opens at **http://localhost:8000/dashboard** — visualise runs, approvals, and agent traces.

---

## What's in the box

After `pip install ninetrix`, running `ninetrix dev` starts:

| Service | Port | What it does |
|---------|------|-------------|
| PostgreSQL | 5432 | Stores agent checkpoints and run history |
| API server | 8000 | REST API + local dashboard |
| MCP gateway | 8080 | Routes tool calls to MCP workers |
| MCP worker | — | Runs MCP server subprocesses |

Everything runs in Docker. No setup beyond Docker Desktop required.

---

## agentfile.yaml

```yaml
agents:
  my-agent:
    metadata:
      name: my-agent
      role: Research assistant
      goal: Answer questions using web search

    runtime:
      provider: anthropic
      model: claude-sonnet-4-6
      temperature: 0.3

    tools:
      - name: web_search
        source: mcp://brave-search
```

See [examples/](./examples/) for more patterns: multi-agent crews, scheduled triggers, MCP tools, persistent memory, and self-hosted deployments.

---

## Multi-Agent

```yaml
agents:
  orchestrator:
    runtime: { provider: anthropic, model: claude-sonnet-4-6 }
    collaborators: [researcher, writer]

  researcher:
    tools:
      - { name: web_search, source: mcp://brave-search }

  writer:
    runtime: { provider: anthropic, model: claude-haiku-4-5-20251001 }
```

```bash
ninetrix up     # starts all agents on a Docker bridge network
ninetrix invoke # send a message to any running agent
ninetrix down   # clean shutdown
```

---

## MCP Tools

Enable any MCP server by editing `~/.agentfile/mcp-worker.yaml`:

```yaml
servers:
  - name: filesystem
    type: npx
    package: "@modelcontextprotocol/server-filesystem"
    args: ["${HOME}"]

  - name: github
    type: npx
    package: "@modelcontextprotocol/server-github"
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_TOKEN}"
```

Then reference tools in your agentfile:

```yaml
tools:
  - name: filesystem
    source: mcp://filesystem
  - name: github
    source: mcp://github
```

---

## Self-Hosting (Enterprise)

```bash
curl -O https://raw.githubusercontent.com/Ninetrix-ai/ninetrix/main/infra/compose/docker-compose.self-host.yml
curl -O https://raw.githubusercontent.com/Ninetrix-ai/ninetrix/main/infra/compose/.env.example
cp .env.example .env   # set your domain + secrets
docker compose -f docker-compose.self-host.yml up -d
```

Includes Caddy for automatic HTTPS. All images are public on GHCR — no build step required.

---

## Repo Structure

```
packages/cli/          The CLI — pip/brew/uv installable
packages/api/          Local API server + dashboard backend
packages/mcp-gateway/  MCP tool routing hub
packages/mcp-worker/   MCP server subprocess bridge
packages/dashboard/    Local Next.js dashboard
infra/compose/         Docker Compose (dev + self-host)
examples/              Ready-to-run agentfile.yaml examples
schema/v1/             JSON Schema for agentfile.yaml
```

---

## Contributing

See [CONTRIBUTING.md](./.github/CONTRIBUTING.md).

Schema proposals, new examples, and CLI improvements are all welcome.

---

## License

Apache 2.0
