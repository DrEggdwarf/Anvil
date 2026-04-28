"""Session manager — multi-concurrent session lifecycle.

Each session owns a bridge instance. Sessions are tracked, timed out,
and cleaned up automatically. No leaked resources.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from backend.app.bridges.base import BaseBridge, BridgeState
from backend.app.bridges.registry import bridge_registry
from backend.app.core.config import settings
from backend.app.core.exceptions import (
    SessionExpired,
    SessionLimitReached,
    SessionNotFound,
)
from backend.app.core.sanitization import validate_session_id

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """A live session — owns a bridge instance."""

    id: str
    bridge_type: str
    bridge: BaseBridge
    # ADR-016: per-session secret required to open the WebSocket. Constant-time
    # compared against ?token=... in /ws/{type}/{id}. Returned ONCE at create.
    token: str = field(default_factory=lambda: secrets.token_hex(16))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now(UTC)

    @property
    def is_expired(self) -> bool:
        timeout = timedelta(seconds=settings.session_timeout_seconds)
        return datetime.now(UTC) - self.last_activity > timeout


class SessionManager:
    """Manages concurrent sessions with timeout and cleanup."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None

    async def create(self, bridge_type: str, config: dict | None = None) -> Session:
        """Create a new session with its bridge. Raises on limit or unknown type."""
        async with self._lock:
            if len(self._sessions) >= settings.max_sessions:
                raise SessionLimitReached(settings.max_sessions)

            bridge_class = bridge_registry.get(bridge_type)
            if bridge_class is None:
                from backend.app.core.exceptions import ValidationError
                raise ValidationError(
                    f"Unknown bridge type: {bridge_type}",
                    code="UNKNOWN_BRIDGE_TYPE",
                    details={"bridge_type": bridge_type, "available": bridge_registry.list_types()},
                )

            bridge = bridge_class()
            await bridge.start()

            session_id = uuid.uuid4().hex[:16]
            session = Session(
                id=session_id,
                bridge_type=bridge_type,
                bridge=bridge,
            )
            self._sessions[session_id] = session
            logger.info("Created session %s (type=%s)", session_id, bridge_type)
            return session

    def get(self, session_id: str) -> Session:
        """Get a session by ID. Raises SessionNotFound or SessionExpired."""
        validate_session_id(session_id)
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFound(session_id)
        if session.is_expired:
            raise SessionExpired(session_id)
        session.touch()
        return session

    async def destroy(self, session_id: str) -> None:
        """Destroy a session and stop its bridge."""
        validate_session_id(session_id)
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session is None:
                raise SessionNotFound(session_id)
            if session.bridge.state not in (BridgeState.STOPPED, BridgeState.ERROR):
                try:
                    await session.bridge.stop()
                except Exception:
                    logger.exception("Error stopping bridge for session %s", session_id)
            logger.info("Destroyed session %s", session_id)

    async def cleanup_expired(self) -> int:
        """Remove all expired sessions. Returns count cleaned."""
        expired_ids = [sid for sid, s in self._sessions.items() if s.is_expired]
        for sid in expired_ids:
            try:
                await self.destroy(sid)
            except Exception:
                logger.exception("Error cleaning up session %s", sid)
        return len(expired_ids)

    async def cleanup_all(self) -> int:
        """Destroy all sessions (shutdown). Returns count cleaned."""
        count = len(self._sessions)
        for sid in list(self._sessions.keys()):
            with contextlib.suppress(Exception):
                await self.destroy(sid)
        return count

    @property
    def active_count(self) -> int:
        return len(self._sessions)

    def list_sessions(self) -> list[Session]:
        return list(self._sessions.values())

    async def start_cleanup_loop(self) -> None:
        """Start the periodic cleanup of expired sessions."""
        async def _loop() -> None:
            while True:
                await asyncio.sleep(settings.session_cleanup_interval_seconds)
                cleaned = await self.cleanup_expired()
                if cleaned:
                    logger.info("Cleaned up %d expired sessions", cleaned)

        self._cleanup_task = asyncio.create_task(_loop())

    async def stop_cleanup_loop(self) -> None:
        """Stop the periodic cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
