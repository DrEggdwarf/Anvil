"""OpenAI Chat Completions streaming adapter (also reused for OpenRouter)."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from backend.app.agent.models import ChatMessage, ProviderConfig

from .base import ProviderError

logger = logging.getLogger(__name__)


def to_openai_messages(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        if m.role == "tool":
            out.append({"role": "tool", "tool_call_id": m.tool_call_id or "", "content": m.content})
            continue
        if m.role == "assistant" and m.tool_calls:
            tc = [
                {
                    "id": t.id,
                    "type": "function",
                    "function": {"name": t.name, "arguments": json.dumps(t.arguments)},
                }
                for t in m.tool_calls
            ]
            out.append({"role": "assistant", "content": m.content or None, "tool_calls": tc})
            continue
        out.append({"role": m.role, "content": m.content})
    return out


async def stream_openai_compatible(
    *,
    url: str,
    api_key: str,
    extra_headers: dict[str, str] | None,
    model: str,
    messages: list[ChatMessage],
    tools: list[dict[str, Any]],
    max_tokens: int,
) -> AsyncIterator[dict[str, Any]]:
    payload: dict[str, Any] = {
        "model": model,
        "stream": True,
        "messages": to_openai_messages(messages),
        "max_tokens": max_tokens,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    headers: dict[str, str] = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    pending: dict[int, dict[str, Any]] = {}
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
        try:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", "replace")
                    raise ProviderError(f"{url} {resp.status_code}: {body[:500]}")
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        evt = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = evt.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    finish = choices[0].get("finish_reason")
                    if delta.get("content"):
                        yield {"type": "text", "delta": delta["content"]}
                    for tc in delta.get("tool_calls") or []:
                        idx = tc.get("index", 0)
                        slot = pending.setdefault(idx, {"id": "", "name": "", "args": ""})
                        if tc.get("id"):
                            slot["id"] = tc["id"]
                        fn = tc.get("function") or {}
                        if fn.get("name"):
                            slot["name"] = fn["name"]
                        if fn.get("arguments"):
                            slot["args"] += fn["arguments"]
                    if finish:
                        for slot in pending.values():
                            try:
                                args = json.loads(slot["args"]) if slot["args"] else {}
                            except json.JSONDecodeError:
                                args = {}
                            yield {
                                "type": "tool_call",
                                "id": slot["id"],
                                "name": slot["name"],
                                "arguments": args,
                            }
                        pending.clear()
                        yield {"type": "stop", "reason": finish}
        except httpx.HTTPError as exc:
            raise ProviderError(f"transport error: {exc}") from exc


class OpenAIProvider:
    name = "openai"
    _DEFAULT_URL = "https://api.openai.com/v1/chat/completions"

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
            raise ProviderError("OpenAI API key missing")
        url = (config.base_url or self._DEFAULT_URL).rstrip("/")
        if not url.endswith("/chat/completions"):
            url = url + "/v1/chat/completions"
        async for c in stream_openai_compatible(
            url=url,
            api_key=config.api_key,
            extra_headers=None,
            model=model,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
        ):
            yield c

    async def test(self, *, config: ProviderConfig, model: str) -> dict[str, Any]:
        if not config.api_key:
            raise ProviderError("API key required")
        url = (config.base_url or self._DEFAULT_URL).rstrip("/")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                url.replace("/chat/completions", "/models"),
                headers={"Authorization": f"Bearer {config.api_key}"},
            )
        return {"ok": resp.status_code < 400, "status": resp.status_code}
