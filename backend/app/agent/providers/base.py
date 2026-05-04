"""Provider base interface and registry."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any, Protocol

from backend.app.agent.models import ChatMessage, ProviderConfig

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Raised when a provider fails (network, auth, quota)."""


class Provider(Protocol):
    name: str

    async def stream(
        self,
        *,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]],
        model: str,
        config: ProviderConfig,
        max_tokens: int = 4096,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield normalized chunks (see module doc)."""
        ...

    async def test(self, *, config: ProviderConfig, model: str) -> dict[str, Any]:
        """Cheap connectivity check."""
        ...


def get_provider(name: str) -> Provider:
    if name == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider()
    if name == "openai":
        from .openai import OpenAIProvider

        return OpenAIProvider()
    if name == "openrouter":
        from .openrouter import OpenRouterProvider

        return OpenRouterProvider()
    if name == "ollama":
        from .ollama import OllamaProvider

        return OllamaProvider()
    raise ProviderError(f"Unknown provider {name!r}")
