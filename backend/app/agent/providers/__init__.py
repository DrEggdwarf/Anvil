"""Provider adapters — translate Anvil ChatMessages into provider streams.

Each provider exposes ``stream(messages, tools, model, **opts)`` returning an
async iterator of normalized chunks:

* ``{"type": "text", "delta": "..."}``                — token delta
* ``{"type": "tool_call", "id": ..., "name": ..., "arguments": ...}``
* ``{"type": "stop", "reason": ...}``

The runtime handles tool execution + history continuation, so providers only
need to surface raw events.
"""

from __future__ import annotations

from .base import Provider, ProviderError, get_provider

__all__ = ["Provider", "ProviderError", "get_provider"]
