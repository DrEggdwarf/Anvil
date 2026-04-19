"""Tests for Session API endpoints (api/sessions.py).

Integration tests: hit API → SessionManager → MockBridge → response.
Validates the full data flow through the session lifecycle.
"""

import pytest


class TestSessionAPI:
    @pytest.mark.asyncio
    async def test_create_session(self, async_client):
        resp = await async_client.post(
            "/api/sessions",
            json={"bridge_type": "mock"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["bridge_type"] == "mock"
        assert data["state"] == "ready"
        assert "created_at" in data
        assert "last_activity" in data

    @pytest.mark.asyncio
    async def test_create_unknown_bridge_type(self, async_client):
        resp = await async_client.post(
            "/api/sessions",
            json={"bridge_type": "nonexistent"},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["code"] == "UNKNOWN_BRIDGE_TYPE"

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, async_client):
        resp = await async_client.get("/api/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["sessions"] == []
        assert data["count"] == 0

    @pytest.mark.asyncio
    async def test_list_sessions_after_create(self, async_client):
        # Create 2 sessions
        await async_client.post("/api/sessions", json={"bridge_type": "mock"})
        await async_client.post("/api/sessions", json={"bridge_type": "mock"})

        resp = await async_client.get("/api/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert len(data["sessions"]) == 2

    @pytest.mark.asyncio
    async def test_get_session_by_id(self, async_client):
        create_resp = await async_client.post(
            "/api/sessions",
            json={"bridge_type": "mock"},
        )
        session_id = create_resp.json()["id"]

        resp = await async_client.get(f"/api/sessions/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == session_id
        assert data["bridge_type"] == "mock"

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, async_client):
        resp = await async_client.get("/api/sessions/deadbeef12345678")
        assert resp.status_code == 404
        data = resp.json()
        assert data["code"] == "SESSION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_delete_session(self, async_client):
        create_resp = await async_client.post(
            "/api/sessions",
            json={"bridge_type": "mock"},
        )
        session_id = create_resp.json()["id"]

        resp = await async_client.delete(f"/api/sessions/{session_id}")
        assert resp.status_code == 204

        # Verify it's gone
        resp = await async_client.get(f"/api/sessions/{session_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, async_client):
        resp = await async_client.delete("/api/sessions/deadbeef12345678")
        assert resp.status_code == 404


class TestSessionDataFlow:
    """End-to-end data flow tests: API → SessionManager → Bridge → Response."""

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self, async_client):
        """Create → Get → List → Delete — full lifecycle."""
        # Create
        r1 = await async_client.post("/api/sessions", json={"bridge_type": "mock"})
        assert r1.status_code == 201
        sid = r1.json()["id"]

        # Get
        r2 = await async_client.get(f"/api/sessions/{sid}")
        assert r2.status_code == 200
        assert r2.json()["state"] == "ready"

        # List
        r3 = await async_client.get("/api/sessions")
        assert r3.json()["count"] == 1

        # Delete
        r4 = await async_client.delete(f"/api/sessions/{sid}")
        assert r4.status_code == 204

        # Verify gone
        r5 = await async_client.get("/api/sessions")
        assert r5.json()["count"] == 0

    @pytest.mark.asyncio
    async def test_multiple_sessions_concurrent(self, async_client):
        """Create multiple sessions, verify isolation, destroy all."""
        ids = []
        for _ in range(5):
            r = await async_client.post("/api/sessions", json={"bridge_type": "mock"})
            assert r.status_code == 201
            ids.append(r.json()["id"])

        # All unique IDs
        assert len(set(ids)) == 5

        # List shows all
        r = await async_client.get("/api/sessions")
        assert r.json()["count"] == 5

        # Destroy one by one
        for sid in ids:
            r = await async_client.delete(f"/api/sessions/{sid}")
            assert r.status_code == 204

        # All gone
        r = await async_client.get("/api/sessions")
        assert r.json()["count"] == 0
