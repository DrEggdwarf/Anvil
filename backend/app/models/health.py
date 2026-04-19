"""Health check response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str


class DetailedHealthResponse(BaseModel):
    status: str
    version: str
    tools: dict
