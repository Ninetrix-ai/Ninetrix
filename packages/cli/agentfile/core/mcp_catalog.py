"""Built-in catalog of well-known MCP servers for the gateway/worker architecture.

Each entry describes how to declare the server in mcp-worker.yaml and which
env vars are required.  The catalog is the single source of truth used by:

  ninetrix mcp add <name>     — looks up entry, writes to mcp-worker.yaml
  ninetrix mcp status         — checks required env vars
  ninetrix gateway doctor     — cross-references configured servers
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CatalogEntry:
    """Describes one MCP server that can be added to the gateway worker."""

    description: str
    type: str                              # npx | uvx | python | docker
    package: str
    args: list[str] = field(default_factory=list)
    # env vars the subprocess needs (key → human label)
    required_env: dict[str, str] = field(default_factory=dict)
    # aliases: if user has GITHUB_TOKEN, rewrite as GITHUB_PERSONAL_ACCESS_TOKEN
    env_aliases: dict[str, str] = field(default_factory=dict)

    def worker_yaml_block(self) -> dict:
        """Return the server block ready to be written into mcp-worker.yaml."""
        block: dict = {"type": self.type, "package": self.package}
        if self.args:
            block["args"] = self.args
        if self.required_env:
            # env: block uses the canonical var name pointing to the host env var
            # (resolved by the worker at startup via ${VAR} substitution)
            block["env"] = {}
            for var in self.required_env:
                # If there's an alias (e.g. GITHUB_TOKEN → GITHUB_PERSONAL_ACCESS_TOKEN)
                # use the alias as the source so the user only needs the friendly name
                source = next(
                    (alias for alias, canon in self.env_aliases.items() if canon == var),
                    var,
                )
                block["env"][var] = f"${{{source}}}"
        return block

    def missing_env(self) -> list[str]:
        """Return list of required env var names that are not set in the host."""
        import os
        missing = []
        for var in self.required_env:
            # Accept either the canonical name or any alias
            sources = [var] + [
                alias for alias, canon in self.env_aliases.items() if canon == var
            ]
            if not any(os.environ.get(s) for s in sources):
                missing.append(var)
        return missing

    def resolve_env_value(self, var: str) -> str | None:
        """Return the value of var (or its alias) from the host environment."""
        import os
        sources = [var] + [
            alias for alias, canon in self.env_aliases.items() if canon == var
        ]
        for s in sources:
            v = os.environ.get(s)
            if v:
                return v
        return None


# ── Built-in catalog ───────────────────────────────────────────────────────────

CATALOG: dict[str, CatalogEntry] = {
    "github": CatalogEntry(
        description="GitHub — repos, issues, PRs, code search, file contents",
        type="npx",
        package="@modelcontextprotocol/server-github",
        required_env={
            "GITHUB_PERSONAL_ACCESS_TOKEN": "GitHub personal access token (classic or fine-grained)",
        },
        env_aliases={"GITHUB_TOKEN": "GITHUB_PERSONAL_ACCESS_TOKEN"},
    ),
    "filesystem": CatalogEntry(
        description="Local filesystem — read and write files in /workspace",
        type="npx",
        package="@modelcontextprotocol/server-filesystem",
        args=["/workspace"],
    ),
    "slack": CatalogEntry(
        description="Slack — send messages, list channels, read threads",
        type="npx",
        package="@modelcontextprotocol/server-slack",
        required_env={
            "SLACK_BOT_TOKEN": "Slack bot token (xoxb-...)",
            "SLACK_TEAM_ID": "Slack workspace/team ID",
        },
    ),
    "notion": CatalogEntry(
        description="Notion — read/write pages, databases, blocks",
        type="npx",
        package="@notionhq/notion-mcp-server",
        required_env={
            "NOTION_API_KEY": "Notion integration token (secret_...)",
        },
    ),
    "linear": CatalogEntry(
        description="Linear — issues, projects, teams, cycles",
        type="npx",
        package="@linear/linear-mcp-server",
        required_env={
            "LINEAR_API_KEY": "Linear personal API key",
        },
    ),
    "brave-search": CatalogEntry(
        description="Brave Search — web search with privacy focus",
        type="npx",
        package="@modelcontextprotocol/server-brave-search",
        required_env={
            "BRAVE_API_KEY": "Brave Search API key",
        },
    ),
    "tavily": CatalogEntry(
        description="Tavily Search — AI-optimised web search, free tier available",
        type="npx",
        package="tavily-mcp",
        required_env={
            "TAVILY_API_KEY": "Tavily API key",
        },
    ),
    "postgres": CatalogEntry(
        description="PostgreSQL — read/write SQL queries",
        type="npx",
        package="@modelcontextprotocol/server-postgres",
        required_env={
            "POSTGRES_CONNECTION_STRING": "PostgreSQL connection string (postgresql://...)",
        },
        env_aliases={"DATABASE_URL": "POSTGRES_CONNECTION_STRING"},
    ),
    "sqlite": CatalogEntry(
        description="SQLite — read/write SQL queries on a local .db file",
        type="uvx",
        package="mcp-server-sqlite",
        args=["--db-path", "/data/db.sqlite"],
    ),
    "fetch": CatalogEntry(
        description="HTTP fetch — retrieve any URL as text or HTML",
        type="uvx",
        package="mcp-server-fetch",
    ),
    "memory": CatalogEntry(
        description="In-process key-value memory store — persists across turns",
        type="npx",
        package="@modelcontextprotocol/server-memory",
    ),
    "puppeteer": CatalogEntry(
        description="Browser automation with Puppeteer (headless Chrome)",
        type="npx",
        package="@modelcontextprotocol/server-puppeteer",
    ),
    "stripe": CatalogEntry(
        description="Stripe — payments, customers, invoices, subscriptions",
        type="npx",
        package="@stripe/agent-toolkit",
        required_env={
            "STRIPE_SECRET_KEY": "Stripe secret key (sk_live_... or sk_test_...)",
        },
    ),
    "google-drive": CatalogEntry(
        description="Google Drive — list, read, search files and folders",
        type="npx",
        package="@modelcontextprotocol/server-gdrive",
        required_env={
            "GOOGLE_DRIVE_ACCESS_TOKEN": "Google OAuth access token for Drive",
        },
    ),
}


def get(name: str) -> CatalogEntry | None:
    """Look up a catalog entry by name. Returns None if not found."""
    return CATALOG.get(name)


def list_all() -> dict[str, CatalogEntry]:
    """Return all catalog entries."""
    return dict(CATALOG)
