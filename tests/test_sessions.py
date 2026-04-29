"""Tests for SessionManager (sessions/manager.py).

Uses MockBridge from conftest — no real tools needed.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from backend.app.core.exceptions import (
    SessionExpired,
    SessionLimitReached,
    SessionNotFound,
    ValidationError,
)
from backend.app.sessions.manager import SessionManager


class TestSessionCreate:
    @pytest.mark.asyncio
    async def test_create_session(self, session_manager: SessionManager):
        session = await session_manager.create("mock")
        assert session.id is not None
        assert len(session.id) == 16
        assert session.bridge_type == "mock"
        assert session.bridge.state.value == "ready"

    @pytest.mark.asyncio
    async def test_create_increments_count(self, session_manager: SessionManager):
        assert session_manager.active_count == 0
        await session_manager.create("mock")
        assert session_manager.active_count == 1
        await session_manager.create("mock")
        assert session_manager.active_count == 2

    @pytest.mark.asyncio
    async def test_create_unknown_type_raises(self, session_manager: SessionManager):
        with pytest.raises(ValidationError) as exc_info:
            await session_manager.create("nonexistent")
        assert exc_info.value.code == "UNKNOWN_BRIDGE_TYPE"

    @pytest.mark.asyncio
    async def test_create_respects_limit(self, session_manager: SessionManager):
        with patch("backend.app.sessions.manager.settings") as mock_settings:
            mock_settings.max_sessions = 2
            mock_settings.session_timeout_seconds = 3600
            await session_manager.create("mock")
            await session_manager.create("mock")
            with pytest.raises(SessionLimitReached):
                await session_manager.create("mock")


class TestSessionGet:
    @pytest.mark.asyncio
    async def test_get_existing_session(self, session_manager: SessionManager):
        created = await session_manager.create("mock")
        fetched = session_manager.get(created.id)
        assert fetched.id == created.id

    @pytest.mark.asyncio
    async def test_get_updates_last_activity(self, session_manager: SessionManager):
        session = await session_manager.create("mock")
        old_activity = session.last_activity
        # Small sleep to ensure timestamp difference
        import asyncio

        await asyncio.sleep(0.01)
        session_manager.get(session.id)
        assert session.last_activity > old_activity

    @pytest.mark.asyncio
    async def test_get_nonexistent_raises(self, session_manager: SessionManager):
        with pytest.raises(SessionNotFound):
            session_manager.get("deadbeef12345678")

    @pytest.mark.asyncio
    async def test_get_expired_raises(self, session_manager: SessionManager):
        session = await session_manager.create("mock")
        # Force expiration
        session.last_activity = datetime.now(timezone.utc) - timedelta(hours=2)
        with pytest.raises(SessionExpired):
            session_manager.get(session.id)


class TestSessionDestroy:
    @pytest.mark.asyncio
    async def test_destroy_session(self, session_manager: SessionManager):
        session = await session_manager.create("mock")
        sid = session.id
        await session_manager.destroy(sid)
        assert session_manager.active_count == 0
        with pytest.raises(SessionNotFound):
            session_manager.get(sid)

    @pytest.mark.asyncio
    async def test_destroy_stops_bridge(self, session_manager: SessionManager):
        session = await session_manager.create("mock")
        bridge = session.bridge
        await session_manager.destroy(session.id)
        assert bridge.stop_called

    @pytest.mark.asyncio
    async def test_destroy_nonexistent_raises(self, session_manager: SessionManager):
        with pytest.raises(SessionNotFound):
            await session_manager.destroy("deadbeef12345678")


class TestSessionCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_expired(self, session_manager: SessionManager):
        s1 = await session_manager.create("mock")
        s2 = await session_manager.create("mock")
        # Expire only s1
        s1.last_activity = datetime.now(timezone.utc) - timedelta(hours=2)
        cleaned = await session_manager.cleanup_expired()
        assert cleaned == 1
        assert session_manager.active_count == 1
        # s2 should still be alive
        session_manager.get(s2.id)

    @pytest.mark.asyncio
    async def test_cleanup_all(self, session_manager: SessionManager):
        await session_manager.create("mock")
        await session_manager.create("mock")
        await session_manager.create("mock")
        count = await session_manager.cleanup_all()
        assert count == 3
        assert session_manager.active_count == 0


class TestSessionList:
    @pytest.mark.asyncio
    async def test_list_sessions(self, session_manager: SessionManager):
        await session_manager.create("mock")
        await session_manager.create("mock")
        sessions = session_manager.list_sessions()
        assert len(sessions) == 2
        assert all(s.bridge_type == "mock" for s in sessions)
