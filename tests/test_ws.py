"""Tests for WebSocket infrastructure (api/ws.py).

Uses Starlette's TestClient for synchronous WebSocket testing.
"""


import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.core.subprocess_manager import SubprocessManager
from backend.app.sessions.manager import SessionManager


@pytest.fixture
def ws_client():
    """Starlette TestClient for WebSocket tests — sets up app state."""
    app.state.subprocess_manager = SubprocessManager()
    app.state.session_manager = SessionManager()
    return TestClient(app)


class TestWSConnection:
    def test_connect_and_disconnect(self, ws_client):
        with ws_client.websocket_connect("/ws/mock/test-session"):
            # Connection should succeed
            pass  # disconnect on exit

    def test_ping_pong(self, ws_client):
        with ws_client.websocket_connect("/ws/mock/test-session") as ws:
            ws.send_json({
                "type": "ping",
                "request_id": "ping-1",
            })
            resp = ws.receive_json()
            assert resp["type"] == "pong"
            assert resp["request_id"] == "ping-1"


class TestWSMessageValidation:
    def test_invalid_json_returns_error(self, ws_client):
        with ws_client.websocket_connect("/ws/mock/test-session") as ws:
            ws.send_text("not json")
            resp = ws.receive_json()
            assert resp["type"] == "error"
            assert resp["payload"]["code"] == "INVALID_MESSAGE"

    def test_invalid_message_schema_returns_error(self, ws_client):
        with ws_client.websocket_connect("/ws/mock/test-session") as ws:
            ws.send_json({"type": "invalid_type"})
            resp = ws.receive_json()
            assert resp["type"] == "error"
            assert resp["payload"]["code"] == "INVALID_MESSAGE"


class TestWSCommandDispatch:
    def test_unknown_command_returns_error(self, ws_client):
        with ws_client.websocket_connect("/ws/mock/test-session") as ws:
            ws.send_json({
                "type": "command",
                "request_id": "cmd-1",
                "payload": {"command": "nonexistent"},
            })
            resp = ws.receive_json()
            assert resp["type"] == "error"
            assert resp["payload"]["code"] == "UNKNOWN_COMMAND"
            assert resp["request_id"] == "cmd-1"

    def test_registered_handler_called(self, ws_client):
        """Register a test handler and verify it's called."""
        from backend.app.api.ws import ws_dispatcher

        handler_called = False

        async def test_handler(ws, msg, session_id):
            nonlocal handler_called
            handler_called = True
            return {"echo": msg.payload.get("data", "")}

        ws_dispatcher.register("mock.echo", test_handler)
        try:
            with ws_client.websocket_connect("/ws/mock/test-session") as ws:
                ws.send_json({
                    "type": "command",
                    "request_id": "cmd-2",
                    "payload": {"command": "echo", "data": "hello"},
                })
                resp = ws.receive_json()
                assert resp["type"] == "result"
                assert resp["payload"]["echo"] == "hello"
                assert resp["request_id"] == "cmd-2"
                assert resp["session_id"] == "test-session"
        finally:
            ws_dispatcher._handlers.pop("mock.echo", None)

    def test_handler_error_returns_error_message(self, ws_client):
        """Handler that raises returns an error to the client."""
        from backend.app.api.ws import ws_dispatcher

        async def failing_handler(ws, msg, session_id):
            raise ValueError("something broke")

        ws_dispatcher.register("mock.fail", failing_handler)
        try:
            with ws_client.websocket_connect("/ws/mock/test-session") as ws:
                ws.send_json({
                    "type": "command",
                    "request_id": "cmd-3",
                    "payload": {"command": "fail"},
                })
                resp = ws.receive_json()
                assert resp["type"] == "error"
                assert resp["payload"]["code"] == "HANDLER_ERROR"
        finally:
            ws_dispatcher._handlers.pop("mock.fail", None)


class TestWSMultipleMessages:
    def test_multiple_messages_in_sequence(self, ws_client):
        """Send multiple messages and verify each gets a response."""
        with ws_client.websocket_connect("/ws/mock/test-session") as ws:
            # Ping 1
            ws.send_json({"type": "ping", "request_id": "p1"})
            r1 = ws.receive_json()
            assert r1["request_id"] == "p1"

            # Ping 2
            ws.send_json({"type": "ping", "request_id": "p2"})
            r2 = ws.receive_json()
            assert r2["request_id"] == "p2"

            # Unknown command
            ws.send_json({
                "type": "command",
                "request_id": "c1",
                "payload": {"command": "nope"},
            })
            r3 = ws.receive_json()
            assert r3["type"] == "error"
            assert r3["request_id"] == "c1"
