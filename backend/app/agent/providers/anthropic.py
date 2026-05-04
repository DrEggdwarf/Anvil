"""Anthropic Messages API streaming adapter."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from backend.app.agent.models import ChatMessage, ProviderConfig

from .base import ProviderError

logger = logging.getLogger(__name__)

API_URL = "https://api.anthropic.com/v1/messages"


def _to_anthropic_messages(
    messages: list[ChatMessage],
) -> tuple[str | None, list[dict[str, Any]]]:
    system: str | None = None
    out: list[dict[str, Any]] = []
    for m in messages:
        if m.role == "system":
            system = (system + "\n\n" + m.content) if system else m.content
            continue
        if m.role == "tool":
            out.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": m.tool_call_id or "",
                            "content": m.content,
                        }
                    ],
                }
            )
            continue
        if m.role == "assistant" and m.tool_calls:
            blocks: list[dict[str, Any]] = []
            if m.content:
                blocks.append({"type": "text", "text": m.content})
            for tc in m.tool_calls:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    }
                )
            out.append({"role": "assistant", "content": blocks})
            continue
        out.append({"role": m.role, "content": m.content})
    return system, out


class AnthropicProvider:
    name = "anthropic"

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
            raise ProviderError("Anthropic API key missing")
        system, msgs = _to_anthropic_messages(messages)
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "stream": True,
            "messages": msgs,
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = tools
        headers = {
            "x-api-key": config.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        url = (config.base_url or API_URL).rstrip("/")
        if not url.endswith("/messages"):
            url = url + "/v1/messages"
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            try:
                async with client.stream("POST", url, headers=headers, json=payload) as resp:
                    if resp.status_code >= 400:
                        body = (await resp.aread()).decode("utf-8", "replace")
                        raise ProviderError(f"Anthropic {resp.status_code}: {body[:500]}")
                    async for chunk in _parse_anthropic_sse(resp):
                        yield chunk
            except httpx.HTTPError as exc:
                raise ProviderError(f"Anthropic transport error: {exc}") from exc

    async def test(self, *, config: ProviderConfig, model: str) -> dict[str, Any]:
        if not config.api_key:
            raise ProviderError("API key required")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                (config.base_url or API_URL).rstrip("/"),
                headers={
                    "x-api-key": config.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "ping"}],
                },
            )
        return {"ok": resp.status_code < 400, "status": resp.status_code}


async def _parse_anthropic_sse(resp: httpx.Response) -> AsyncIterator[dict[str, Any]]:
    """Convert Anthropic SSE events into normalized chunks."""
    current_tool: dict[str, Any] | None = None
    buf_input = ""
    async for raw in resp.aiter_lines():
        if not raw or not raw.startswith("data:"):
            continue
        data = raw[5:].strip()
        if not data:
            continue
        try:
            evt = json.loads(data)
        except json.JSONDecodeError:
            continue
        et = evt.get("type")
        if et == "content_block_start":
            block = evt.get("content_block", {})
            if block.get("type") == "tool_use":
                current_tool = {
                    "id": block.get("id", ""),
                    "name": block.get("name", ""),
                }
                buf_input = ""
        elif et == "content_block_delta":
            delta = evt.get("delta", {})
            dt = delta.get("type")
            if dt == "text_delta":
                yield {"type": "text", "delta": delta.get("text", "")}
            elif dt == "input_json_delta" and current_tool is not None:
                buf_input += delta.get("partial_json", "")
        elif et == "content_block_stop":
            if current_tool is not None:
                args: dict[str, Any] = {}
                if buf_input:
                    try:
                        args = json.loads(buf_input)
                    except json.JSONDecodeError:
                        args = {}
                yield {
                    "type": "tool_call",
                    "id": current_tool["id"],
                    "name": current_tool["name"],
                    "arguments": args,
                }
                current_tool = None
                buf_input = ""
        elif et == "message_stop":
            yield {"type": "stop", "reason": "end"}
        elif et == "message_delta":
            stop = evt.get("delta", {}).get("stop_reason")
            if stop:
                yield {"type": "stop", "reason": stop}
