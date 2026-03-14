# Contributing to Ninetrix

Thanks for helping build the open standard for AI agents. Here's how to get started.

## Repo Structure

```
packages/cli/          Python CLI — the main developer tool
packages/api/          Local API server (checkpoint reader + dashboard backend)
packages/mcp-gateway/  MCP tool routing hub
packages/mcp-worker/   MCP server subprocess bridge
packages/dashboard/    Local Next.js dashboard
infra/compose/         Docker Compose files (dev + self-host)
examples/              Example agentfile.yaml files
schema/v1/             JSON Schema for agentfile.yaml
```

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 20+ and pnpm
- Docker Desktop (or Docker Engine on Linux)

### Install everything
```bash
# JS packages
pnpm install

# Python packages (editable installs)
pip install -e packages/cli
pip install -e packages/api
pip install -e packages/mcp-gateway
pip install -e packages/mcp-worker
```

### Run the local stack
```bash
ninetrix dev
```

This starts PostgreSQL, the API, MCP gateway, and MCP worker via Docker Compose.

### Run individual services (for development)
```bash
# API
cd packages/api && uvicorn main:app --reload --port 8000

# MCP Gateway
cd packages/mcp-gateway && uvicorn main:app --reload --port 8080

# Dashboard (hot reload)
cd packages/dashboard && pnpm dev
```

## Making Changes

### CLI (`packages/cli`)
- Core models: `agentfile/core/models.py`
- Add a new command: create `agentfile/commands/your_cmd.py`, register in `agentfile/cli.py`
- The generated agent runtime lives in `agentfile/templates/entrypoint.py.j2` — it's Jinja2, not plain Python

### agentfile.yaml schema (`schema/v1/`)
- Edit `agentfile.schema.json` directly
- The schema is symlinked from `packages/cli/agentfile/core/schema.json` — edit either, they're the same file

### Examples (`examples/`)
- Every example must be a valid `agentfile.yaml` that passes schema validation
- Run `make validate-examples` to check before submitting a PR

## Pull Request Guidelines

1. **One concern per PR.** Bug fix, feature, or docs — not all three.
2. **Test manually.** There's no automated test suite yet. Show the output of your manual test in the PR description.
3. **Update examples** if you change the schema.
4. **Keep the schema backwards compatible** unless the change is in a major version.

## Commit Style

```
verb(scope): short description

Examples:
  feat(cli): add ninetrix status command
  fix(mcp-gateway): handle worker disconnect during in-flight call
  docs(examples): add scheduled agent example
  chore(ci): cache pip dependencies in release workflow
```

## Reporting Issues

Use the GitHub issue templates:
- **Bug report** — include CLI version (`ninetrix --version`), OS, and Docker version
- **Feature request** — describe the use case, not just the solution

## Schema Contributions

The `agentfile.yaml` schema is community-maintained. Proposals to extend it:
1. Open an issue describing the new field and use case
2. Get a maintainer to label it `schema-proposal`
3. Implement in a PR with a new example

This keeps the schema stable and intentional.
