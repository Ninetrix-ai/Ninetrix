# CLAUDE.md — mcp-gateway

## What is this?

The MCP Gateway is a central hub that aggregates tools from multiple MCP workers and exposes them to AI agents via a single HTTP endpoint. It solves a fundamental problem: agents running in Docker containers (or in the cloud) can't spawn local MCP server processes. Instead, workers connect outbound to the gateway, and agents call the gateway — which routes tool calls to the right worker.

Think of it as a **tool router**: workers register their capabilities, agents discover and call tools, the gateway handles all the routing in between.

## Architecture

```
Agent container
  POST /v1/mcp/{workspace_id}     ← HTTP JSON-RPC 2.0
        │
        ▼
  mcp-gateway (this repo)
  ┌─────────────────────────────────────────┐
  │  WorkerRegistry (in-memory)             │
  │  workspace_id → [WorkerConnection, ...] │
  │  tool_name    → WorkerConnection        │
  └──────────────────┬──────────────────────┘
                     │ WebSocket (persistent)
        ▼
  mcp-worker (outbound connection from worker)
    runs npx/uvx MCP server subprocesses
```

The WebSocket direction is critical: **workers connect outbound** to the gateway. This means workers behind NAT, firewalls, or inside private cloud networks work without any inbound port configuration.

## File Structure

```
main.py          FastAPI app — mounts all routers, configures CORS
models.py        Pydantic models: ToolSchema, WorkerStatus, MCPRequest/Response
pyproject.toml   deps: fastapi, uvicorn[standard], websockets>=13, pydantic>=2, httpx>=0.27
Dockerfile       FROM python:3.12-slim; pip install -e .; uvicorn on port 8080

core/
  __init__.py
  registry.py    WorkerRegistry singleton — the heart of the gateway:
                   connect() / disconnect() — manages WorkerConnection objects
                   register_tools() — indexes tools by workspace + prefix
                   get_tools(workspace_id) — returns all tools for a workspace
                   get_worker_for_tool(workspace_id, tool_name) — lookup for routing
                   send_call(conn, server, tool, args) — routes call over WS, 60s timeout
                   resolve_result(call_id, result/error) — resolves pending futures
  auth.py        Token verification (two modes):
                   Dev mode  (no SAAS_API_URL): validates against MCP_GATEWAY_SECRET env var
                   Prod mode (SAAS_API_URL set): delegates to saas-api via saas_client.py
                   verify_token(authorization) — for HTTP agent requests (returns workspace_id)
                   verify_worker_token(token)  — for WS worker connections
  saas_client.py HTTP client for gateway → saas-api internal calls (prod mode only):
                   verify_token(token) → workspace_id  (5-min in-memory cache)
                   get_tool_credential(worker_token, integration_id) → env_vars dict
                   get_integration_auth_url(workspace_id, integration_id) → OAuth URL | None

routers/
  workers.py     WS /ws/workers/{worker_id}
                   Accepts worker connections; validates token → resolves workspace
                   Handles: worker.register, tool.result, ping messages
                   The resolved workspace from token ALWAYS overrides any query param
  mcp.py         POST /v1/mcp/{workspace_id}  — agent-facing JSON-RPC 2.0 endpoint
                   initialize / tools/list / tools/call / ping
                   Token workspace always wins over URL param (security: prevents cross-workspace access)
                   On tool-not-found: checks saas-api for disconnected integration → returns -32010
                   with auth_url in error.data so agents can prompt user to connect
  admin.py       GET /health  — {status, connected_workers}
                 GET /admin/workers  — full worker list with tool counts
                 GET /admin/tools    — all available tools for a workspace
```

## Tool Namespacing

Tools are prefixed: `{server_name}__{tool_name}` (double underscore).

Example: `filesystem__read_file`, `slack__send_message`, `github__create_pr`

This prevents collisions when multiple workers expose different MCP servers into the same workspace.

## Auth Modes

### Dev mode (local docker-compose)
Set `MCP_GATEWAY_SECRET=dev-secret` (or leave default). Workers and agents authenticate with this single shared secret. `MCP_GATEWAY_REQUIRE_AUTH=false` allows unauthenticated access for local development.

Token format accepted: `Bearer {workspace_id}:{secret}` → returns workspace_id
Token format accepted: `Bearer {secret}` → returns "default"

### Prod mode (SaaS)
Set `MCP_GATEWAY_SAAS_API_URL=https://api.ninetrix.io` and `MCP_GATEWAY_SERVICE_SECRET=...`.
All tokens are validated via `POST /internal/v1/gateway/verify-token` on saas-api.
Results cached in-memory for 5 minutes.

## JSON-RPC Protocol (Agent → Gateway)

```
POST /v1/mcp/{workspace_id}
Authorization: Bearer <token>

{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
{"jsonrpc": "2.0", "id": 2, "method": "tools/list",  "params": {}}
{"jsonrpc": "2.0", "id": 3, "method": "tools/call",
  "params": {"name": "slack__send_message", "arguments": {...}}}
```

## WebSocket Protocol (Worker → Gateway)

```
// Worker connects:
ws://gateway:8080/ws/workers/{worker_id}?token=...&worker_name=...

// Worker registers tools on connect:
{"type": "worker.register", "tools": [...], "servers": ["slack", "github"]}

// Gateway routes tool call to worker:
{"type": "tool.call", "call_id": "uuid", "server": "slack", "tool": "send_message", "args": {...}}

// Worker returns result:
{"type": "tool.result", "call_id": "uuid", "result": {...}}

// Keepalive:
{"type": "ping"} / {"type": "pong"}
```

## Error Codes

| Code | Meaning |
|------|---------|
| -32601 | Tool or method not found |
| -32603 | Internal error (tool call exception) |
| -32010 | Integration not connected — `error.data.auth_url` has the OAuth URL |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_GATEWAY_SECRET` | `dev-secret` | Shared secret for dev mode auth |
| `MCP_GATEWAY_REQUIRE_AUTH` | `false` | Set `true` to require auth in dev mode |
| `MCP_GATEWAY_SAAS_API_URL` | `` | Enables prod mode; saas-api URL for token verification |
| `MCP_GATEWAY_SERVICE_SECRET` | `dev-gateway-secret` | Shared secret for gateway↔saas-api internal calls |

## Running Locally

```bash
# Via docker-compose (recommended — starts gateway + worker together)
cd cli/
ninetrix gateway start

# Direct
cd mcp-gateway/
pip install -e .
uvicorn main:app --port 8080 --reload
```

## Key Invariants

- **Token workspace always wins** — the workspace resolved from the Bearer token is used for all routing. The `{workspace_id}` URL parameter is ignored as an authority.
- **WorkerConnection.workspace_id is immutable** — set at connect time from the verified token, never updated.
- **All tool lookups are workspace-scoped** — a tool from workspace-A is invisible to workspace-B agents.
- **Pending calls are futures** — `send_call()` creates an asyncio.Future per call_id; `resolve_result()` fulfills it when the worker responds. Disconnect cancels all pending futures for that worker.
