# CLAUDE.md — mcp-worker

## What is this?

The MCP Worker is a bridge process that **runs MCP server subprocesses and connects outbound to the MCP Gateway**. Agents never talk to the worker directly — they call the gateway, which routes tool calls to the right worker over a persistent WebSocket.

The key insight: the WebSocket connection is **worker → gateway** (outbound), not inbound. This lets workers run behind NAT, firewalls, or inside private customer networks without any port-forwarding.

```
Agent container
  POST /v1/mcp/{workspace_id}
        │
        ▼
  mcp-gateway (public endpoint)
        │  WebSocket (worker initiates)
        ▼
  mcp-worker  ← THIS REPO
    spawns: npx/uvx/python MCP server subprocesses
    communicates via stdio (MCP protocol)
```

## Two Operating Modes

### Dev / Enterprise Mode (default)
No `MCP_SAAS_API_URL` set. All MCP servers are declared in `mcp-worker.yaml` with their credentials in `env:` blocks. Servers start **eagerly** at boot.

```yaml
servers:
  - name: github
    type: npx
    package: "@modelcontextprotocol/server-github"
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_TOKEN}"
```

The `${VAR}` syntax is resolved at boot from the container's environment. Credentials come from host env vars forwarded via docker-compose.

### SaaS Mode (prod)
When `MCP_SAAS_API_URL` + `MCP_GATEWAY_TOKEN` are both set:
- Static yaml servers still start eagerly as above.
- **Managed integration servers** (github, slack, google-drive, etc.) start **lazily** — on first tool call, the worker calls saas-api to fetch credentials for just that integration, then starts the subprocess.
- Credentials are never stored in worker memory beyond the subprocess spawn.
- Google token expiry (401) triggers an automatic refresh + subprocess restart.

## File Structure

```
main.py          Entry point — wires config → ServerPool → GatewayClient → run
config.py        WorkerConfig + ServerConfig dataclasses; load_config() parses mcp-worker.yaml
                   Env vars always override yaml fields
                   server_to_command() converts ServerConfig → (executable, args)
mcp_bridge.py    MCPServer class — wraps one MCP server subprocess:
                   start()     — spawns subprocess, runs MCP init, lists tools (prefixed name__tool)
                   call_tool() — invokes tool with 30s timeout
                   stop()      — tears down stdio + session context managers
                   tools       — list[dict] with {name, description, inputSchema}
gateway_client.py GatewayClient — persistent WebSocket to the gateway:
                   connect()   — connects, sends worker.register, handles tool.call messages
                   ping_loop() — sends keepalive pings every 30s
                   Reconnects with exponential back-off (5s → 60s cap) on disconnect
runtime.py       ServerPool — manages all MCPServer instances:
                   start_static_servers() — eager start from yaml at boot
                   get_server(name)       — returns running server or starts lazily
                   call_tool(...)         — executes tool, handles Google 401 refresh
                   _start_managed_server() — fetches creds from saas-api, starts subprocess
                   _restart_server()      — stops + restarts with refreshed credentials
saas_client.py   HTTP client for worker → saas-api credential fetching (SaaS mode only):
                   get_tool_credential(integration_id) → env_vars dict
                   refresh_credential(integration_id) → re-fetches after Google token refresh
                   is_saas_mode()         — returns True only when SAAS_API_URL + TOKEN are set
mcp-worker.yaml.example  Reference config with examples for all supported server types
```

## mcp-worker.yaml Format

```yaml
# Gateway connection (all fields override-able via env vars)
gateway_url: "ws://localhost:8080"   # env: MCP_GATEWAY_URL
workspace_id: "default"             # env: MCP_WORKSPACE_ID
worker_name: "my-worker"            # env: MCP_WORKER_NAME
worker_id: "my-worker"              # env: MCP_WORKER_ID (defaults to worker_name)
token: "dev-secret"                 # env: MCP_GATEWAY_TOKEN

servers:
  - name: filesystem                # must be unique; used as tool prefix
    type: npx                       # npx | uvx | python | docker
    package: "@modelcontextprotocol/server-filesystem"
    args: ["/data"]                 # passed to the server process

  - name: github
    type: npx
    package: "@modelcontextprotocol/server-github"
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_TOKEN}"  # resolved from container env

  - name: internal-api
    command: "python /opt/my_mcp_server.py"  # full command override (bypasses type+package)
    env:
      INTERNAL_API_KEY: "${INTERNAL_API_KEY}"
```

**Server types:**
| type | Runs |
|------|------|
| `npx` | `npx -y <package> [args...]` |
| `uvx` | `uvx <package> [args...]` |
| `python` | `python -m <package> [args...]` |
| `docker` | `docker run --rm -i <package> [args...]` |
| (command) | splits on spaces, appends args |

## Tool Namespacing

Every tool exposed by a server is prefixed with `{server_name}__`:

```
github__create_issue
github__list_repos
filesystem__read_file
slack__send_message
```

This prevents collisions when multiple servers expose tools with the same short name. The gateway indexes all tools under this namespace.

## WebSocket Protocol (Worker → Gateway)

```
// Connect:
ws://gateway:8080/ws/workers/{worker_id}?token=...&workspace_id=...&worker_name=...

// On connect, worker immediately sends:
{"type": "worker.register", "tools": [...], "servers": ["github", "filesystem"]}

// Gateway confirms:
{"type": "worker.registered", "tool_count": 42}

// Gateway sends tool calls:
{"type": "tool.call", "call_id": "uuid", "server": "github", "tool": "list_repos", "args": {...}}

// Worker responds:
{"type": "tool.result", "call_id": "uuid", "result": {"content": [...], "isError": false}}
// or on error:
{"type": "tool.result", "call_id": "uuid", "error": "some error message"}

// Keepalive:
{"type": "ping"} → {"type": "pong"}
```

## Credential Flow (SaaS Mode)

```
1. Tool call arrives from gateway: server="github", tool="list_repos"
2. ServerPool.call_tool() checks if github server is running
3. If not running: calls saas_client.get_tool_credential("github")
4. saas-api validates worker token → returns {GITHUB_PERSONAL_ACCESS_TOKEN: "..."}
5. Worker spawns: npx -y @modelcontextprotocol/server-github
   with GITHUB_PERSONAL_ACCESS_TOKEN injected as env var
6. Tool executes; result returned to gateway
7. On Google 401: saas_client.refresh_credential() → restart subprocess with new token
```

Credentials are **never stored** beyond the subprocess spawn. The worker process itself holds no secrets at rest.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_GATEWAY_URL` | `ws://localhost:8080` | WebSocket URL of the gateway |
| `MCP_WORKSPACE_ID` | `default` | Workspace this worker belongs to |
| `MCP_WORKER_NAME` | `worker-1` | Human-readable worker name |
| `MCP_WORKER_ID` | `{worker_name}` | Unique worker identifier |
| `MCP_GATEWAY_TOKEN` | `dev-secret` | Auth token for gateway connection |
| `MCP_WORKER_CONFIG` | `mcp-worker.yaml` | Path to yaml config file |
| `MCP_SAAS_API_URL` | `` | Enables SaaS mode; saas-api URL for credential fetching |
| `MCP_GATEWAY_SERVICE_SECRET` | `dev-gateway-secret` | Shared secret for worker → saas-api internal calls |

Credential env vars (forwarded automatically by `ninetrix gateway start`):
`GITHUB_TOKEN`, `SLACK_BOT_TOKEN`, `SLACK_TEAM_ID`, `NOTION_API_KEY`, `LINEAR_API_KEY`, `BRAVE_API_KEY`, `STRIPE_SECRET_KEY`, `GOOGLE_*_ACCESS_TOKEN`, `POSTGRES_CONNECTION_STRING`

## Running Locally

```bash
# Via docker-compose (recommended — starts gateway + worker together)
cd cli/
ninetrix gateway start

# Direct (for development)
cd mcp-worker/
pip install -e .
MCP_GATEWAY_URL=ws://localhost:8080 \
MCP_GATEWAY_TOKEN=dev-secret \
MCP_WORKER_CONFIG=mcp-worker.yaml.example \
python main.py
```

## Key Invariants

- **Outbound only** — workers connect to the gateway; the gateway never connects to workers.
- **Credential isolation** — in SaaS mode, credentials are fetched per-integration, passed to the subprocess env, and not retained in worker memory.
- **Eager + lazy coexist** — yaml-declared servers start at boot; managed servers start on first tool call. Both are valid simultaneously.
- **Tool prefix is stable** — `{server_name}__` prefix is set at `MCPServer.start()` and never changes. Renaming a server in yaml changes all its tool names.
- **Reconnect is automatic** — `GatewayClient.connect()` loops forever with exponential back-off. Workers survive gateway restarts.
- **30s tool timeout** — `mcp_bridge.MCPServer.call_tool()` uses `asyncio.wait_for(..., timeout=30.0)`. Hanging subprocess tools are cancelled.
