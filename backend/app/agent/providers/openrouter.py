"""OpenRouter — same API shape as OpenAI Chat Completions."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
from backend.app.agent.models import ChatMessage, ProviderConfig

from .base import ProviderError
from .openai import stream_openai_compatible


class OpenRouterProvider:
    name = "openrouter"
    _DEFAULT_URL = "https://openrouter.ai/api/v1/chat/completions"

    async def stream(
        self,
        *,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]],
        model: str,
        config: ProviderConfig,
        max_tokens: int = 4096,
    ) -> AsyncIterator[dict[str, Any]]:
        if not config.api_key:
            raise ProviderError("OpenRouter API key missing")
        url = (config.base_url or self._DEFAULT_URL).rstrip("/")
        if not url.endswith("/chat/completions"):
            url = url + "/api/v1/chat/completions"
        async for c in stream_openai_compatible(
            url=url,
            api_key=config.api_key,
            extra_headers={
                "HTTP-Referer": "https://anvil.local",
                "X-Title": "Anvil",
            },
            model=model,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
        ):
            yield c

    async def test(self, *, config: ProviderConfig, model: str) -> dict[str, Any]:
        if not config.api_key:
            raise ProviderError("API key required")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {config.api_key}"},
            )
        return {"ok": resp.status_code < 400, "status": resp.status_code}
