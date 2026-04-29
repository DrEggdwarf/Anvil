"""WebSocket message schemas — typed protocol for all WS communication."""

from __future__ import annotations

import uuid
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class WSMessageType(StrEnum):
    # Client → Server
    COMMAND = "command"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    PING = "ping"

    # Server → Client
    RESULT = "result"
    EVENT = "event"
    ERROR = "error"
    PONG = "pong"


class WSMessage(BaseModel):
    """Typed WebSocket message — every WS frame follows this schema."""

    type: WSMessageType
    session_id: str | None = Field(default=None, max_length=64)
    request_id: str = Field(default_factory=lambda: uuid.uuid4().hex, max_length=64)
    payload: dict = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _limit_payload_size(cls, values: dict) -> dict:
        pl = values.get("payload") or {}
        if len(str(pl)) > 65_536:
            msg = "payload too large (max 64 KB serialized)"
            raise ValueError(msg)
        return values
