"""Telegram channel adapter."""
from __future__ import annotations

import logging

import httpx

from ninetrix_channels.base import ChannelAdapter, InboundMessage

logger = logging.getLogger(__name__)

_API = "https://api.telegram.org/bot{token}"


class TelegramAdapter(ChannelAdapter):
    channel_type = "telegram"

    async def validate_config(self, config: dict) -> tuple[bool, str]:
        bot_token = config.get("bot_token", "").strip()
        if not bot_token:
            return False, "bot_token is required"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{_API.format(token=bot_token)}/getMe")
            if resp.status_code != 200:
                return False, "Invalid Telegram bot token"
        return True, ""

    async def parse_webhook(self, body: dict) -> InboundMessage | None:
        # We only handle regular text messages (not callback queries, edits, etc.)
        message = body.get("message")
        if not message:
            return None

        text = (message.get("text") or "").strip()
        if not text:
            return None

        # Skip bot commands that are part of the verification flow
        if text.startswith("/start"):
            return None

        chat_id = str(message["chat"]["id"])
        from_user = message.get("from", {})
        user_id = str(from_user.get("id", "")) if from_user.get("id") else None
        username = from_user.get("username") or from_user.get("first_name")

        return InboundMessage(
            channel_id="",  # filled by the router after channel lookup
            chat_id=chat_id,
            user_id=user_id,
            username=username,
            text=text,
            raw=body,
        )

    async def send_message(self, config: dict, chat_id: str, text: str) -> bool:
        bot_token = config.get("bot_token", "")
        if not bot_token:
            return False
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{_API.format(token=bot_token)}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            )
            if resp.status_code != 200:
                logger.error("Telegram sendMessage failed: %s", resp.text[:300])
                return False
        return True

    async def setup_webhook(self, config: dict, webhook_url: str) -> tuple[bool, str]:
        bot_token = config.get("bot_token", "")
        webhook_secret = config.get("webhook_secret", "")
        async with httpx.AsyncClient(timeout=10) as client:
            payload: dict = {"url": webhook_url}
            if webhook_secret:
                payload["secret_token"] = webhook_secret
            resp = await client.post(
                f"{_API.format(token=bot_token)}/setWebhook",
                json=payload,
            )
            if resp.status_code != 200:
                return False, f"Failed to set Telegram webhook: {resp.text[:300]}"
        return True, ""

    async def get_bot_info(self, config: dict) -> dict:
        bot_token = config.get("bot_token", "")
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{_API.format(token=bot_token)}/getMe")
            if resp.status_code == 200:
                return resp.json().get("result", {})
        return {}
