"""Pydantic models for the in-app agent (ADR-023)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# ── Provider catalog ─────────────────────────────────────
ProviderName = Literal["anthropic", "openai", "openrouter", "ollama"]
PROVIDERS: tuple[ProviderName, ...] = ("anthropic", "openai", "openrouter", "ollama")

# ── Roles & messages ─────────────────────────────────────
Role = Literal["system", "user", "assistant", "tool"]


class ToolCall(BaseModel):
    """A tool invocation requested by the model."""

    id: str = Field(..., max_length=128)
    name: str = Field(..., max_length=128)
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Any | None = None
    error: str | None = Field(default=None, max_length=4000)
    duration_ms: int | None = Field(default=None, ge=0)
    approved: bool | None = None
    destructive: bool = False


class ChatMessage(BaseModel):
    """A single message in the conversation."""

    role: Role
    content: str = Field(default="", max_length=200_000)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str | None = Field(default=None, max_length=128)


# ── Session ──────────────────────────────────────────────
class AgentSession(BaseModel):
    id: str = Field(..., max_length=64)
    title: str = Field(default="Nouvelle conversation", max_length=200)
    module: str = Field(default="asm", max_length=32)
    provider: ProviderName = "anthropic"
    model: str = Field(default="claude-3-5-sonnet-latest", max_length=128)
    created_at: datetime
    last_used: datetime
    messages: list[ChatMessage] = Field(default_factory=list)


# ── Settings (BYOK) ──────────────────────────────────────
class ProviderConfig(BaseModel):
    api_key: str = Field(default="", max_length=512)
    base_url: str | None = Field(default=None, max_length=512)
    default_model: str = Field(default="", max_length=128)


class AgentSettings(BaseModel):
    """Persisted in ``~/.anvil/config.json``."""

    active_provider: ProviderName = "anthropic"
    providers: dict[ProviderName, ProviderConfig] = Field(default_factory=dict)
    strict_mode: bool = False
    allow_write_exec: bool = False
    token_cap: int = Field(default=50_000, ge=100, le=1_000_000)
    language: Literal["fr", "en"] = "fr"


class AgentSettingsResponse(BaseModel):
    """Same as AgentSettings but with masked api_keys for the frontend."""

    active_provider: ProviderName
    providers: dict[ProviderName, dict[str, Any]]
    strict_mode: bool
    allow_write_exec: bool
    token_cap: int
    language: Literal["fr", "en"]


# ── Chat request / SSE chunks ────────────────────────────
class AgentChatRequest(BaseModel):
    session_id: str | None = Field(default=None, max_length=64)
    module: str = Field(default="asm", max_length=32)
    chips: list[str] = Field(default_factory=list, max_length=8)
    message: str = Field(..., min_length=1, max_length=20_000)
    anvil_session_ids: dict[str, str] = Field(default_factory=dict, max_length=8)
    """Map module → Anvil session_id (for context injection + tool dispatch)."""
    allow_write_exec: bool | None = None
    """Per-request override of safeguard."""


ChunkType = Literal[
    "session",  # session_id created/used
    "delta",  # token chunk
    "tool_call",  # tool invocation start
    "tool_result",  # tool invocation finished
    "tool_pending",  # destructive tool waiting for approval
    "done",  # end of turn
    "error",
]


class AgentChunk(BaseModel):
    type: ChunkType
    data: dict[str, Any] = Field(default_factory=dict)


class ToolApprovalRequest(BaseModel):
    session_id: str = Field(..., max_length=64)
    tool_call_id: str = Field(..., max_length=128)
    approved: bool


class ProviderTestRequest(BaseModel):
    provider: ProviderName
    api_key: str | None = Field(default=None, max_length=512)
    base_url: str | None = Field(default=None, max_length=512)
    model: str | None = Field(default=None, max_length=128)
