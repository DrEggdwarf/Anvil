"""Ollama local-server adapter (NDJSON streaming)."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from backend.app.agent.models import ChatMessage, ProviderConfig

from .base import ProviderError
from .openai import to_openai_messages

logger = logging.getLogger(__name__)


class OllamaProvider:
    name = "ollama"
    _DEFAULT_URL = "http://127.0.0.1:11434"

    async def stream(
        self,
        *,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]],
        model: str,
        config: ProviderConfig,
        max_tokens: int = 4096,
    ) -> AsyncIterator[dict[str, Any]]:
        base = (config.base_url or self._DEFAULT_URL).rstrip("/")
        url = f"{base}/api/chat"
        # Ollama tools schema is OpenAI-compatible.
        payload: dict[str, Any] = {
            "model": model,
            "messages": to_openai_messages(messages),
            "stream": True,
            "options": {"num_predict": max_tokens},
        }
        if tools:
            payload["tools"] = tools

        try:
            async with (
                httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=5.0)) as client,
                client.stream("POST", url, json=payload) as resp,
            ):
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", "replace")
                    raise ProviderError(f"Ollama {resp.status_code}: {body[:500]}")
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        evt = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    msg = evt.get("message") or {}
                    if msg.get("content"):
                        yield {"type": "text", "delta": msg["content"]}
                    for i, tc in enumerate(msg.get("tool_calls") or []):
                        fn = tc.get("function") or {}
                        yield {
                            "type": "tool_call",
                            "id": f"ollama-{i}",
                            "name": fn.get("name", ""),
                            "arguments": fn.get("arguments") or {},
                        }
                    if evt.get("done"):
                        yield {"type": "stop", "reason": evt.get("done_reason", "end")}
        except httpx.HTTPError as exc:
            raise ProviderError(f"Ollama transport error: {exc}") from exc

    async def test(self, *, config: ProviderConfig, model: str) -> dict[str, Any]:
        base = (config.base_url or self._DEFAULT_URL).rstrip("/")
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base}/api/tags")
        return {"ok": resp.status_code < 400, "status": resp.status_code}
