"""Ninetrix Channels — pluggable inbound messaging adapters."""
from __future__ import annotations

from ninetrix_channels.base import ChannelAdapter, InboundMessage
from ninetrix_channels.registry import adapter_registry, get_adapter

__all__ = [
    "ChannelAdapter",
    "InboundMessage",
    "adapter_registry",
    "get_adapter",
]
