"""Tests for WebSocket infrastructure (api/ws.py).

Uses Starlette's TestClient for synchronous WebSocket testing.

Sprint 14 fix #4 (ADR-016): every WS connection now requires a valid `?token=...`
matching `Session.token`, plus the URL `session_type` matching `Session.bridge_type`.
The `mock_session` fixture creates a real session via POST /api/sessions and yields
the session_id + token used by all tests.
"""

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.app.core.subprocess_manager import SubprocessManager
from backend.app.main import app
from backend.app.sessions.manager import SessionManager


@pytest.fixture
def ws_client():
    """Starlette TestClient for WebSocket tests — sets up app state."""
    app.state.subprocess_manager = SubprocessManager()
    app.state.session_manager = SessionManager()
    return TestClient(app)


@pytest.fixture
def mock_session(ws_client):
    """Create a real mock session via the REST API, return (session_id, token)."""
    resp = ws_client.post("/api/sessions", json={"bridge_type": "mock"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body["id"], body["token"]


def _ws_url(session_id: str, token: str, session_type: str = "mock") -> str:
    return f"/ws/{session_type}/{session_id}?token={token}"


class TestWSConnection:
    def test_connect_and_disconnect(self, ws_client, mock_session):
        sid, token = mock_session
        with ws_client.websocket_connect(_ws_url(sid, token)):
            pass

    def test_ping_pong(self, ws_client, mock_session):
        sid, token = mock_session
        with ws_client.websocket_connect(_ws_url(sid, token)) as ws:
            ws.send_json({"type": "ping", "request_id": "ping-1"})
            resp = ws.receive_json()
            assert resp["type"] == "pong"
            assert resp["request_id"] == "ping-1"


class TestWSAuthentication:
    """ADR-016: token + session_type + Origin gates."""

    def test_missing_token_rejected(self, ws_client, mock_session):
        sid, _ = mock_session
        with pytest.raises(WebSocketDisconnect):
            with ws_client.websocket_connect(f"/ws/mock/{sid}"):
                pass

    def test_wrong_token_rejected(self, ws_client, mock_session):
        sid, _ = mock_session
        with pytest.raises(WebSocketDisconnect):
            with ws_client.websocket_connect(f"/ws/mock/{sid}?token=" + "0" * 32):
                pass

    def test_unknown_session_id_rejected(self, ws_client):
        with pytest.raises(WebSocketDisconnect):
            with ws_client.websocket_connect("/ws/mock/" + "a" * 16 + "?token=x"):
                pass

    def test_invalid_session_id_format_rejected(self, ws_client):
        with pytest.raises(WebSocketDisconnect):
            with ws_client.websocket_connect("/ws/mock/not-hex?token=x"):
                pass

    def test_session_type_mismatch_rejected(self, ws_client, mock_session):
        sid, token = mock_session
        with pytest.raises(WebSocketDisconnect):
            with ws_client.websocket_connect(_ws_url(sid, token, session_type="gdb")):
                pass


class TestWSMessageValidation:
    def test_invalid_json_returns_error(self, ws_client, mock_session):
        sid, token = mock_session
        with ws_client.websocket_connect(_ws_url(sid, token)) as ws:
            ws.send_text("not json")
            resp = ws.receive_json()
            assert resp["type"] == "error"
            assert resp["payload"]["code"] == "INVALID_MESSAGE"

    def test_invalid_message_schema_returns_error(self, ws_client, mock_session):
        sid, token = mock_session
        with ws_client.websocket_connect(_ws_url(sid, token)) as ws:
            ws.send_json({"type": "invalid_type"})
            resp = ws.receive_json()
            assert resp["type"] == "error"
            assert resp["payload"]["code"] == "INVALID_MESSAGE"


class TestWSCommandDispatch:
    def test_unknown_command_returns_error(self, ws_client, mock_session):
        sid, token = mock_session
        with ws_client.websocket_connect(_ws_url(sid, token)) as ws:
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "cmd-1",
                    "payload": {"command": "nonexistent"},
                }
            )
            resp = ws.receive_json()
            assert resp["type"] == "error"
            assert resp["payload"]["code"] == "UNKNOWN_COMMAND"
            assert resp["request_id"] == "cmd-1"

    def test_registered_handler_called(self, ws_client, mock_session):
        """Register a test handler and verify it's called."""
        from backend.app.api.ws import ws_dispatcher

        async def test_handler(ws, msg, session_id):
            return {"echo": msg.payload.get("data", "")}

        ws_dispatcher.register("mock.echo", test_handler)
        try:
            sid, token = mock_session
            with ws_client.websocket_connect(_ws_url(sid, token)) as ws:
                ws.send_json(
                    {
                        "type": "command",
                        "request_id": "cmd-2",
                        "payload": {"command": "echo", "data": "hello"},
                    }
                )
                resp = ws.receive_json()
                assert resp["type"] == "result"
                assert resp["payload"]["echo"] == "hello"
                assert resp["request_id"] == "cmd-2"
                assert resp["session_id"] == sid
        finally:
            ws_dispatcher._handlers.pop("mock.echo", None)

    def test_handler_error_returns_error_message(self, ws_client, mock_session):
        """Handler that raises returns an error to the client."""
        from backend.app.api.ws import ws_dispatcher

        async def failing_handler(ws, msg, session_id):
            raise ValueError("something broke")

        ws_dispatcher.register("mock.fail", failing_handler)
        try:
            sid, token = mock_session
            with ws_client.websocket_connect(_ws_url(sid, token)) as ws:
                ws.send_json(
                    {
                        "type": "command",
                        "request_id": "cmd-3",
                        "payload": {"command": "fail"},
                    }
                )
                resp = ws.receive_json()
                assert resp["type"] == "error"
                assert resp["payload"]["code"] == "HANDLER_ERROR"
        finally:
            ws_dispatcher._handlers.pop("mock.fail", None)


class TestWSMultipleMessages:
    def test_multiple_messages_in_sequence(self, ws_client, mock_session):
        """Send multiple messages and verify each gets a response."""
        sid, token = mock_session
        with ws_client.websocket_connect(_ws_url(sid, token)) as ws:
            ws.send_json({"type": "ping", "request_id": "p1"})
            r1 = ws.receive_json()
            assert r1["request_id"] == "p1"

            ws.send_json({"type": "ping", "request_id": "p2"})
            r2 = ws.receive_json()
            assert r2["request_id"] == "p2"

            ws.send_json(
                {
                    "type": "command",
                    "request_id": "c1",
                    "payload": {"command": "nope"},
                }
            )
            r3 = ws.receive_json()
            assert r3["type"] == "error"
            assert r3["request_id"] == "c1"
