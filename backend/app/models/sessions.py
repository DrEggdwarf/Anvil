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


class SessionCreated(SessionInfo):
    """Same as SessionInfo plus the WS auth token — returned ONCE at creation only.

    ADR-016: the token is required to open `/ws/{session_type}/{session_id}` and
    must be kept by the client (not re-fetchable via GET /api/sessions/{id}).
    """

    token: str


class SessionListResponse(BaseModel):
    sessions: list[SessionInfo]
    count: int
