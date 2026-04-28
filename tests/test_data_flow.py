"""End-to-end data flow tests.

These tests validate the complete data pipeline:
API Request → FastAPI Route → SessionManager → Bridge → Response

Every test triggers actual API calls and verifies the data flows correctly
through all layers. This is NOT unit testing — this is integration testing
of the full backend stack.
"""


import pytest
from starlette.testclient import TestClient

from backend.app.api.ws import ws_dispatcher
from backend.app.main import app
from backend.app.core.subprocess_manager import SubprocessManager
from backend.app.sessions.manager import SessionManager


@pytest.fixture
def ws_client():
    app.state.subprocess_manager = SubprocessManager()
    app.state.session_manager = SessionManager()
    return TestClient(app)


@pytest.fixture
def authed_ws(ws_client):
    """Sprint 14 fix #4: WS endpoint requires a real session + token; create one."""
    resp = ws_client.post("/api/sessions", json={"bridge_type": "mock"})
    assert resp.status_code == 201
    body = resp.json()
    return ws_client, body["id"], body["token"]


class TestErrorMiddlewareDataFlow:
    """Verify that AnvilError exceptions become structured JSON responses."""

    @pytest.mark.asyncio
    async def test_session_not_found_returns_404(self, async_client):
        resp = await async_client.get("/api/sessions/deadbeef12345678")
        assert resp.status_code == 404
        data = resp.json()
        assert data["code"] == "SESSION_NOT_FOUND"
        assert "error" in data
        assert "details" in data
        assert data["details"]["session_id"] == "deadbeef12345678"

    @pytest.mark.asyncio
    async def test_unknown_bridge_returns_400(self, async_client):
        resp = await async_client.post(
            "/api/sessions",
            json={"bridge_type": "does_not_exist"},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["code"] == "UNKNOWN_BRIDGE_TYPE"

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(self, async_client):
        resp = await async_client.delete("/api/sessions/deadbeef12345679")
        assert resp.status_code == 404
        data = resp.json()
        assert data["code"] == "SESSION_NOT_FOUND"


class TestWSDataFlow:
    """Verify data flows correctly through the WebSocket pipeline."""

    def test_ws_ping_pong_data_integrity(self, authed_ws):
        """Ping → Pong: verify request_id is preserved."""
        client, sid, token = authed_ws
        with client.websocket_connect(f"/ws/mock/{sid}?token={token}") as ws:
            ws.send_json({
                "type": "ping",
                "request_id": "my-unique-id-123",
            })
            resp = ws.receive_json()
            assert resp["type"] == "pong"
            assert resp["request_id"] == "my-unique-id-123"

    def test_ws_command_result_data_flow(self, authed_ws):
        """Command → Handler → Result: verify payload flows through."""
        client, sid, token = authed_ws

        async def echo_handler(ws, msg, session_id):
            return {
                "echoed_session": session_id,
                "echoed_data": msg.payload.get("data"),
            }

        ws_dispatcher.register("mock.echo", echo_handler)
        try:
            with client.websocket_connect(f"/ws/mock/{sid}?token={token}") as ws:
                ws.send_json({
                    "type": "command",
                    "request_id": "req-42",
                    "session_id": sid,
                    "payload": {"command": "echo", "data": {"key": "value"}},
                })
                resp = ws.receive_json()
                assert resp["type"] == "result"
                assert resp["session_id"] == sid
                assert resp["request_id"] == "req-42"
                assert resp["payload"]["echoed_session"] == sid
                assert resp["payload"]["echoed_data"] == {"key": "value"}
        finally:
            ws_dispatcher._handlers.pop("mock.echo", None)

    def test_ws_error_data_flow(self, authed_ws):
        """Unknown command → Error: verify error structure."""
        client, sid, token = authed_ws
        with client.websocket_connect(f"/ws/mock/{sid}?token={token}") as ws:
            ws.send_json({
                "type": "command",
                "request_id": "req-err",
                "payload": {"command": "nonexistent"},
            })
            resp = ws.receive_json()
            assert resp["type"] == "error"
            assert resp["request_id"] == "req-err"
            assert "code" in resp["payload"]
            assert "message" in resp["payload"]


class TestSessionBridgeDataFlow:
    """Verify session → bridge data flow via REST API."""

    @pytest.mark.asyncio
    async def test_session_create_starts_bridge(self, async_client):
        """Creating a session should start its bridge (state=ready)."""
        resp = await async_client.post(
            "/api/sessions",
            json={"bridge_type": "mock"},
        )
        assert resp.status_code == 201
        assert resp.json()["state"] == "ready"

    @pytest.mark.asyncio
    async def test_session_delete_stops_bridge(self, async_client):
        """Deleting a session should stop its bridge."""
        r1 = await async_client.post("/api/sessions", json={"bridge_type": "mock"})
        sid = r1.json()["id"]
        r2 = await async_client.delete(f"/api/sessions/{sid}")
        assert r2.status_code == 204
        # Session is gone
        r3 = await async_client.get(f"/api/sessions/{sid}")
        assert r3.status_code == 404


class TestToolDataFlow:
    """Verify tool checking data flow."""

    @pytest.mark.asyncio
    async def test_health_detailed_checks_all_tools(self, async_client):
        """Detailed health should check every defined tool."""
        from backend.app.models.tools import TOOL_DEFINITIONS

        resp = await async_client.get("/api/health/detailed")
        data = resp.json()
        # Every tool definition should appear in the response
        for tool_def in TOOL_DEFINITIONS:
            assert tool_def.name in data["tools"], f"Missing tool: {tool_def.name}"

    @pytest.mark.asyncio
    async def test_tools_by_mode_filters_correctly(self, async_client):
        """Tools for a mode should only include tools relevant to that mode."""
        resp = await async_client.get("/api/tools/firmware")
        data = resp.json()
        for tool in data["tools"]:
            assert "firmware" in tool["modes"], (
                f"Tool {tool['name']} shouldn't be in firmware mode"
            )

    @pytest.mark.asyncio
    async def test_tool_availability_shape(self, async_client):
        """Each tool in /api/tools should have availability info."""
        resp = await async_client.get("/api/tools")
        data = resp.json()
        for category, tools in data["tools"].items():
            for tool in tools:
                assert "name" in tool
                assert "available" in tool
                assert "required" in tool
                assert "modes" in tool
                assert isinstance(tool["available"], bool)
