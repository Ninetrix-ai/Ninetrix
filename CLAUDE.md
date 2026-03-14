# CLAUDE.md — ninetrix (open-source monorepo)

This is the public open-source monorepo for the Ninetrix agent platform.

---

## Repo Structure

```
packages/
  cli/           pip install ninetrix  — the main CLI tool
  api/           ghcr.io/ninetrix-ai/ninetrix-api  — checkpoint API + dashboard
  mcp-gateway/   ghcr.io/ninetrix-ai/ninetrix-mcp-gateway — MCP tool routing hub
  mcp-worker/    ghcr.io/ninetrix-ai/ninetrix-mcp-worker  — MCP subprocess bridge
  dashboard/     Next.js local dashboard (built into api image)

infra/compose/
  docker-compose.dev.yml        used by `ninetrix dev`
  docker-compose.self-host.yml  enterprise self-hosting

examples/        6 ready-to-run agentfile.yaml examples
schema/v1/       agentfile.yaml JSON Schema (symlink → packages/cli/agentfile/core/schema.json)
.github/         CI workflows + CONTRIBUTING.md + issue templates
```

---

## Development Setup

```bash
# JS packages
pnpm install

# Python packages (editable)
pip install -e packages/cli
pip install -e packages/api
pip install -e packages/mcp-gateway
pip install -e packages/mcp-worker

# Start the full local stack
ninetrix dev
```

---

## Key Commands

```bash
make build          # build all packages (turbo + copy dashboard into api/static)
make dev            # alias for ninetrix dev
make release-cli    # publish CLI to PyPI
make release-api    # push api Docker image to ghcr.io
make release-mcp-gateway   # push mcp-gateway image
make release-mcp-worker    # push mcp-worker image
```

---

## Release Tags

| Package | Tag format | Publishes to |
|---------|-----------|-------------|
| `packages/cli` | `cli/v1.2.3` | PyPI |
| `packages/api` | `api/v1.2.3` | ghcr.io/ninetrix-ai/ninetrix-api |
| `packages/mcp-gateway` | `mcp-gateway/v1.2.3` | ghcr.io/ninetrix-ai/ninetrix-mcp-gateway |
| `packages/mcp-worker` | `mcp-worker/v1.2.3` | ghcr.io/ninetrix-ai/ninetrix-mcp-worker |

---

## Working Rules

- **No test suite** — manual smoke tests with `ninetrix build/run/dev`
- **Schema changes** need an example update + maintainer review (see CODEOWNERS)
- **Max 5 files per action** unless explicitly approved
- **Show a PLAN before non-trivial changes** — wait for APPROVE

---

## Component CLAUDE.md Files

Each package has its own CLAUDE.md with detailed guidance:

- `packages/cli/CLAUDE.md` — agentfile.yaml schema, templates, providers, persistence, triggers, HITL, multi-agent
- `packages/api/CLAUDE.md` — endpoints, DB schema, asyncpg patterns
- `packages/mcp-gateway/CLAUDE.md` — WorkerRegistry, auth modes, JSON-RPC protocol
- `packages/mcp-worker/CLAUDE.md` — server types, YAML config, credential flow
