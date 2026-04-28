"""Session management REST routes."""

from __future__ import annotations

from backend.app.api.deps import get_session_manager
from backend.app.models.sessions import (
    SessionCreate,
    SessionCreated,
    SessionInfo,
    SessionListResponse,
)
from backend.app.sessions.manager import Session, SessionManager
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _session_to_info(s: Session) -> SessionInfo:
    return SessionInfo(
        id=s.id,
        bridge_type=s.bridge_type,
        state=s.bridge.state.value,
        created_at=s.created_at.isoformat(),
        last_activity=s.last_activity.isoformat(),
    )


@router.post("", response_model=SessionCreated, status_code=201)
async def create_session(
    body: SessionCreate,
    sm: SessionManager = Depends(get_session_manager),
):
    """Create a new session for a given bridge type.

    ADR-016: returns the WebSocket auth `token` ONCE; client must store it to open `/ws/...`.
    """
    session = await sm.create(body.bridge_type, body.config)
    return SessionCreated(
        id=session.id,
        bridge_type=session.bridge_type,
        state=session.bridge.state.value,
        created_at=session.created_at.isoformat(),
        last_activity=session.last_activity.isoformat(),
        token=session.token,
    )


@router.get("", response_model=SessionListResponse)
async def list_sessions(sm: SessionManager = Depends(get_session_manager)):
    """List all active sessions."""
    sessions = sm.list_sessions()
    return SessionListResponse(
        sessions=[_session_to_info(s) for s in sessions],
        count=len(sessions),
    )


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Get info about a specific session."""
    session = sm.get(session_id)
    return _session_to_info(session)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Destroy a session and release its resources."""
    await sm.destroy(session_id)
