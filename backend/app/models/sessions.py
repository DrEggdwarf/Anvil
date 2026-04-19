"""Session management schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class SessionCreate(BaseModel):
    bridge_type: str = Field(..., max_length=64)
    config: dict = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _limit_config_size(cls, values: dict) -> dict:
        cfg = values.get("config") or {}
        if len(str(cfg)) > 4096:
            msg = "config payload too large (max 4 KB serialized)"
            raise ValueError(msg)
        return values


class SessionInfo(BaseModel):
    id: str
    bridge_type: str
    state: str
    created_at: str
    last_activity: str


class SessionListResponse(BaseModel):
    sessions: list[SessionInfo]
    count: int
