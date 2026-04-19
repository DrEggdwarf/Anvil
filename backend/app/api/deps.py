"""FastAPI dependency injection — access app state from route handlers."""

from __future__ import annotations

from backend.app.core.sanitization import validate_session_id
from backend.app.core.subprocess_manager import SubprocessManager
from backend.app.sessions.manager import SessionManager
from fastapi import Request


def get_session_manager(request: Request) -> SessionManager:
    return request.app.state.session_manager


def get_subprocess_manager(request: Request) -> SubprocessManager:
    return request.app.state.subprocess_manager


def validated_session_id(session_id: str) -> str:
    """Dependency to validate session_id format at API boundary."""
    return validate_session_id(session_id)
