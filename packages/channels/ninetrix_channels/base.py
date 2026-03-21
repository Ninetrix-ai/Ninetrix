"""Channel adapter interface and shared models."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class InboundMessage:
    """Structured message extracted from a platform webhook payload."""
    channel_id: str                  # our internal channel UUID
    chat_id: str                     # platform-specific (Telegram chat_id, WhatsApp number)
    user_id: str | None = None       # platform-specific user identifier
    username: str | None = None
    text: str = ""
    raw: dict = field(default_factory=dict)


@dataclass
class DispatchResult:
    """Result of dispatching a message to an agent."""
    run_id: str
    thread_id: str
    agent_name: str
    status: str = "queued"


class ChannelAdapter(ABC):
    """Abstract base for all channel adapters (Telegram, WhatsApp, etc.)."""

    channel_type: str

    @abstractmethod
    async def validate_config(self, config: dict) -> tuple[bool, str]:
        """Validate bot token / API credentials.

        Returns (ok, error_message). error_message is empty on success.
        """

    @abstractmethod
    async def parse_webhook(self, body: dict) -> InboundMessage | None:
        """Extract a structured message from a platform webhook payload.

        Returns None if the payload is not a user message (e.g. bot status
        update, message edit, delivery receipt).
        """

    @abstractmethod
    async def send_message(self, config: dict, chat_id: str, text: str) -> bool:
        """Send a text message to a chat. Returns True on success."""

    @abstractmethod
    async def setup_webhook(self, config: dict, webhook_url: str) -> tuple[bool, str]:
        """Register the webhook URL with the platform.

        Returns (ok, error_message).
        """

    @abstractmethod
    async def get_bot_info(self, config: dict) -> dict:
        """Fetch bot profile info (username, display name, etc.)."""

    def parse_command(self, text: str) -> tuple[str | None, str]:
        """Extract /command prefix from message text.

        Returns (command_name, remaining_text). command_name is None if no
        command prefix is present.
        """
        text = text.strip()
        if text.startswith("/"):
            parts = text.split(maxsplit=1)
            cmd = parts[0][1:]  # strip leading /
            # Strip @botname suffix (Telegram sends /cmd@botname in groups)
            cmd = cmd.split("@")[0]
            remaining = parts[1] if len(parts) > 1 else ""
            return cmd, remaining
        return None, text
