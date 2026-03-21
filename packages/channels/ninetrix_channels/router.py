"""Channel routing — resolves inbound messages to the correct agent + thread."""
from __future__ import annotations

import logging
import uuid
from typing import Any, Protocol

from ninetrix_channels.base import InboundMessage, DispatchResult

logger = logging.getLogger(__name__)


class DBPool(Protocol):
    """Minimal async DB interface (works with asyncpg pools)."""
    async def fetchrow(self, query: str, *args: Any) -> Any: ...
    async def fetch(self, query: str, *args: Any) -> list[Any]: ...
    async def execute(self, query: str, *args: Any) -> str: ...
    async def fetchval(self, query: str, *args: Any) -> Any: ...


async def find_channel_by_bot_token(pool: DBPool, bot_token: str) -> dict | None:
    """Look up a channel by its bot_token stored in config JSONB."""
    row = await pool.fetchrow(
        """
        SELECT id, org_id, channel_type, name, config, session_mode, routing_mode,
               verified, enabled
        FROM channels
        WHERE config->>'bot_token' = $1 AND verified = TRUE AND enabled = TRUE
        """,
        bot_token,
    )
    return dict(row) if row else None


async def resolve_agent(
    pool: DBPool,
    channel: dict,
    command: str | None,
) -> dict | None:
    """Resolve the target agent for this channel + optional command.

    Returns a channel_agent_bindings row dict, or None if no match.
    """
    channel_id = channel["id"]

    if channel["routing_mode"] == "command" and command:
        # Try exact command match first
        row = await pool.fetchrow(
            """
            SELECT id, agent_name, agent_id, is_default, command
            FROM channel_agent_bindings
            WHERE channel_id = $1 AND command = $2
            """,
            channel_id, f"/{command}",
        )
        if row:
            return dict(row)

    # Fall back to default binding (or single binding)
    row = await pool.fetchrow(
        """
        SELECT id, agent_name, agent_id, is_default, command
        FROM channel_agent_bindings
        WHERE channel_id = $1
        ORDER BY is_default DESC, created_at ASC
        LIMIT 1
        """,
        channel_id,
    )
    return dict(row) if row else None


async def resolve_or_create_session(
    pool: DBPool,
    channel: dict,
    msg: InboundMessage,
    agent_name: str,
) -> str:
    """Resolve an existing session or create a new one.

    Returns the thread_id to use for this dispatch.
    """
    if channel["session_mode"] == "per_message":
        return f"ch-{uuid.uuid4().hex[:16]}"

    # per_chat: look up existing session
    row = await pool.fetchrow(
        """
        SELECT thread_id FROM channel_sessions
        WHERE channel_id = $1 AND external_chat_id = $2 AND agent_name = $3
        """,
        channel["id"], msg.chat_id, agent_name,
    )
    if row:
        # Bump last_message_at
        await pool.execute(
            "UPDATE channel_sessions SET last_message_at = NOW() WHERE channel_id = $1 AND external_chat_id = $2 AND agent_name = $3",
            channel["id"], msg.chat_id, agent_name,
        )
        return row["thread_id"]

    # Create new session
    thread_id = f"ch-{uuid.uuid4().hex[:16]}"
    await pool.execute(
        """
        INSERT INTO channel_sessions
            (channel_id, external_chat_id, external_user_id, agent_name, thread_id)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (channel_id, external_chat_id, agent_name) DO UPDATE
            SET last_message_at = NOW()
        """,
        channel["id"], msg.chat_id, msg.user_id, agent_name, thread_id,
    )
    return thread_id


async def route_message(
    pool: DBPool,
    msg: InboundMessage,
    channel: dict,
    adapter: Any,
) -> tuple[str, str, str] | None:
    """Route an inbound message to an agent.

    Returns (agent_name, thread_id, run_id) or None if no valid binding found.
    """
    command, clean_text = adapter.parse_command(msg.text)
    msg.text = clean_text or msg.text  # keep original if no command

    binding = await resolve_agent(pool, channel, command)
    if not binding:
        logger.warning("No agent binding for channel %s (command=%s)", channel["id"], command)
        return None

    agent_name = binding["agent_name"]
    thread_id = await resolve_or_create_session(pool, channel, msg, agent_name)
    run_id = uuid.uuid4().hex

    return agent_name, thread_id, run_id
