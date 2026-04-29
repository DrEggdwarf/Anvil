"""Tests for GDB WebSocket handlers (api/gdb_ws.py).

Tests the WS data flow: Client → WS message → Dispatcher → GDB handler → Bridge → Response.
All with mock GDB controller — no real GDB needed.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

from backend.app.bridges.base import BridgeState
from backend.app.bridges.gdb_bridge import GdbBridge
from backend.app.core.subprocess_manager import SubprocessManager
from backend.app.main import app
from backend.app.sessions.manager import SessionManager


def _gdb_result(payload=None):
    return {"type": "result", "message": "done", "payload": payload}


@pytest.fixture
def gdb_ws_env():
    """Set up app state + a mock GDB session, return (TestClient, session_id)."""
    sm = SessionManager()
    app.state.subprocess_manager = SubprocessManager()
    app.state.session_manager = sm

    # Init GDB WS handlers
    from backend.app.api.gdb_ws import init_gdb_ws_handlers

    init_gdb_ws_handlers(sm)

    # Create a mock GDB session manually
    from backend.app.sessions.manager import Session

    bridge = GdbBridge()
    bridge._controller = MagicMock()
    bridge._controller.gdb_process = MagicMock()
    bridge._controller.gdb_process.pid = 88888
    bridge._controller.gdb_process.poll.return_value = None
    bridge._controller.write.return_value = [_gdb_result()]
    bridge.state = BridgeState.READY

    # Sprint 14 fix #4 (ADR-016): Session generates a token automatically;
    # tests must include it as `?token=...` when opening the WS.
    session = Session(
        id="aabbccdd11223344",
        bridge_type="gdb",
        bridge=bridge,
        token="deadbeefcafe1234",
    )
    sm._sessions["aabbccdd11223344"] = session

    client = TestClient(app)
    return client, "aabbccdd11223344", bridge, session.token


class TestGdbWSStepCommands:
    def test_step_into(self, gdb_ws_env):
        client, sid, bridge, token = gdb_ws_env
        with client.websocket_connect(f"/ws/gdb/{sid}?token={token}") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "r1",
                    "payload": {"command": "step_into"},
                }
            )
            resp = ws.receive_json()
            assert resp["type"] == "result"
            assert resp["payload"]["action"] == "step_into"
            assert "gdb_responses" in resp["payload"]

    def test_step_over(self, gdb_ws_env):
        client, sid, bridge, token = gdb_ws_env
        with client.websocket_connect(f"/ws/gdb/{sid}?token={token}") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "r2",
                    "payload": {"command": "step_over"},
                }
            )
            resp = ws.receive_json()
            assert resp["payload"]["action"] == "step_over"

    def test_step_out(self, gdb_ws_env):
        client, sid, bridge, token = gdb_ws_env
        with client.websocket_connect(f"/ws/gdb/{sid}?token={token}") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "r3",
                    "payload": {"command": "step_out"},
                }
            )
            resp = ws.receive_json()
            assert resp["payload"]["action"] == "step_out"


class TestGdbWSExecControl:
    def test_continue(self, gdb_ws_env):
        client, sid, bridge, token = gdb_ws_env
        with client.websocket_connect(f"/ws/gdb/{sid}?token={token}") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "r4",
                    "payload": {"command": "continue"},
                }
            )
            resp = ws.receive_json()
            assert resp["payload"]["action"] == "continue"

    def test_run(self, gdb_ws_env):
        client, sid, bridge, token = gdb_ws_env
        with client.websocket_connect(f"/ws/gdb/{sid}?token={token}") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "r5",
                    "payload": {"command": "run", "args": "input.txt"},
                }
            )
            resp = ws.receive_json()
            assert resp["payload"]["action"] == "run"


class TestGdbWSLoad:
    def test_load_binary(self, gdb_ws_env):
        client, sid, bridge, token = gdb_ws_env
        with client.websocket_connect(f"/ws/gdb/{sid}?token={token}") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "r6",
                    "payload": {"command": "load", "binary_path": "/tmp/test_bin"},
                }
            )
            resp = ws.receive_json()
            assert resp["type"] == "result"
            assert resp["payload"]["binary_path"] == "/tmp/test_bin"

    def test_load_binary_missing_path(self, gdb_ws_env):
        client, sid, bridge, token = gdb_ws_env
        with client.websocket_connect(f"/ws/gdb/{sid}?token={token}") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "r7",
                    "payload": {"command": "load"},
                }
            )
            resp = ws.receive_json()
            assert resp["type"] == "error"


class TestGdbWSBreakpoints:
    def test_set_breakpoint(self, gdb_ws_env):
        client, sid, bridge, token = gdb_ws_env
        with client.websocket_connect(f"/ws/gdb/{sid}?token={token}") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "bp1",
                    "payload": {"command": "breakpoint_set", "location": "main"},
                }
            )
            resp = ws.receive_json()
            assert resp["payload"]["location"] == "main"

    def test_remove_breakpoint(self, gdb_ws_env):
        client, sid, bridge, token = gdb_ws_env
        with client.websocket_connect(f"/ws/gdb/{sid}?token={token}") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "bp2",
                    "payload": {"command": "breakpoint_remove", "bp_number": 1},
                }
            )
            resp = ws.receive_json()
            assert resp["payload"]["bp_number"] == 1


class TestGdbWSInspection:
    def test_registers(self, gdb_ws_env):
        client, sid, bridge, token = gdb_ws_env
        bridge._controller.write.side_effect = [
            [
                {
                    "type": "result",
                    "message": "done",
                    "payload": {"register-names": ["rax", "rbx"]},
                }
            ],
            [
                {
                    "type": "result",
                    "message": "done",
                    "payload": {
                        "register-values": [
                            {"number": "0", "value": "0x42"},
                            {"number": "1", "value": "0xff"},
                        ]
                    },
                }
            ],
        ]
        with client.websocket_connect(f"/ws/gdb/{sid}?token={token}") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "reg1",
                    "payload": {"command": "registers"},
                }
            )
            resp = ws.receive_json()
            assert resp["payload"]["action"] == "registers"
            regs = resp["payload"]["registers"]
            assert len(regs) == 2
            assert regs[0]["name"] == "rax"
            assert regs[0]["value"] == "0x42"

    def test_stack(self, gdb_ws_env):
        client, sid, bridge, token = gdb_ws_env
        with client.websocket_connect(f"/ws/gdb/{sid}?token={token}") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "stk1",
                    "payload": {"command": "stack"},
                }
            )
            resp = ws.receive_json()
            assert resp["payload"]["action"] == "stack"

    def test_memory(self, gdb_ws_env):
        client, sid, bridge, token = gdb_ws_env
        with client.websocket_connect(f"/ws/gdb/{sid}?token={token}") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "mem1",
                    "payload": {
                        "command": "memory",
                        "address": "0x7fff0000",
                        "size": 64,
                    },
                }
            )
            resp = ws.receive_json()
            assert resp["payload"]["address"] == "0x7fff0000"
            assert resp["payload"]["size"] == 64

    def test_memory_missing_address(self, gdb_ws_env):
        client, sid, bridge, token = gdb_ws_env
        with client.websocket_connect(f"/ws/gdb/{sid}?token={token}") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "mem2",
                    "payload": {"command": "memory"},
                }
            )
            resp = ws.receive_json()
            assert resp["type"] == "error"


class TestGdbWSDisassemble:
    def test_disassemble(self, gdb_ws_env):
        client, sid, bridge, token = gdb_ws_env
        with client.websocket_connect(f"/ws/gdb/{sid}?token={token}") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "dis1",
                    "payload": {"command": "disassemble", "function": "_start"},
                }
            )
            resp = ws.receive_json()
            assert resp["payload"]["action"] == "disassemble"


class TestGdbWSEvaluate:
    def test_evaluate(self, gdb_ws_env):
        client, sid, bridge, token = gdb_ws_env
        with client.websocket_connect(f"/ws/gdb/{sid}?token={token}") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "eval1",
                    "payload": {"command": "evaluate", "expression": "$rax"},
                }
            )
            resp = ws.receive_json()
            assert resp["payload"]["expression"] == "$rax"

    def test_evaluate_missing_expression(self, gdb_ws_env):
        client, sid, bridge, token = gdb_ws_env
        with client.websocket_connect(f"/ws/gdb/{sid}?token={token}") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "eval2",
                    "payload": {"command": "evaluate"},
                }
            )
            resp = ws.receive_json()
            assert resp["type"] == "error"


class TestGdbWSRawExecute:
    def test_raw_execute(self, gdb_ws_env):
        client, sid, bridge, token = gdb_ws_env
        with client.websocket_connect(f"/ws/gdb/{sid}?token={token}") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "raw1",
                    "payload": {"command": "execute", "command_str": "-exec-run"},
                }
            )
            resp = ws.receive_json()
            assert resp["payload"]["command"] == "-exec-run"

    def test_raw_execute_missing_cmd(self, gdb_ws_env):
        client, sid, bridge, token = gdb_ws_env
        with client.websocket_connect(f"/ws/gdb/{sid}?token={token}") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "raw2",
                    "payload": {"command": "execute"},
                }
            )
            resp = ws.receive_json()
            assert resp["type"] == "error"


class TestGdbWSDataFlow:
    """Full data flow test: load → breakpoint → run → step → registers via WS."""

    def test_full_debug_flow_ws(self, gdb_ws_env):
        client, sid, bridge, token = gdb_ws_env
        with client.websocket_connect(f"/ws/gdb/{sid}?token={token}") as ws:
            # Load
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "f1",
                    "payload": {"command": "load", "binary_path": "/tmp/test"},
                }
            )
            r = ws.receive_json()
            assert r["type"] == "result"
            assert r["payload"]["action"] == "load"

            # Breakpoint
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "f2",
                    "payload": {"command": "breakpoint_set", "location": "_start"},
                }
            )
            r = ws.receive_json()
            assert r["type"] == "result"

            # Run
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "f3",
                    "payload": {"command": "run"},
                }
            )
            r = ws.receive_json()
            assert r["type"] == "result"

            # Step
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "f4",
                    "payload": {"command": "step_into"},
                }
            )
            r = ws.receive_json()
            assert r["type"] == "result"

            # Registers
            bridge._controller.write.side_effect = [
                [
                    {
                        "type": "result",
                        "message": "done",
                        "payload": {"register-names": ["rip"]},
                    }
                ],
                [
                    {
                        "type": "result",
                        "message": "done",
                        "payload": {
                            "register-values": [
                                {"number": "0", "value": "0x401001"},
                            ]
                        },
                    }
                ],
            ]
            ws.send_json(
                {
                    "type": "command",
                    "request_id": "f5",
                    "payload": {"command": "registers"},
                }
            )
            r = ws.receive_json()
            assert r["type"] == "result"
            assert r["payload"]["registers"][0]["name"] == "rip"
            assert r["payload"]["registers"][0]["value"] == "0x401001"
