"""Tests for GDB REST API routes (api/gdb.py).

Uses mock GDB bridge — tests the full HTTP data flow:
Request → Route → SessionManager → GdbBridge (mock) → Response.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.app.bridges.base import BridgeState


def _gdb_result(payload=None):
    return {"type": "result", "message": "done", "payload": payload}


@pytest_asyncio.fixture
async def gdb_client():
    """Client with a mock GDB session already created."""
    from backend.app.bridges.gdb_bridge import GdbBridge
    from backend.app.core.lifecycle import lifespan
    from backend.app.main import app

    async with lifespan(app):
        # Patch GdbBridge.start to avoid spawning real GDB
        original_start = GdbBridge.start

        async def mock_start(self):
            self._controller = MagicMock()
            self._controller.gdb_process = MagicMock()
            self._controller.gdb_process.pid = 99999
            self._controller.gdb_process.poll.return_value = None
            self._controller.write.return_value = [_gdb_result()]
            self.state = BridgeState.READY

        GdbBridge.start = mock_start

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create a GDB session
            resp = await client.post("/api/sessions", json={"bridge_type": "gdb"})
            session_id = resp.json()["id"]
            # Stash for tests
            client.session_id = session_id  # type: ignore[attr-defined]
            client.app = app  # type: ignore[attr-defined]
            yield client

        GdbBridge.start = original_start


class TestGdbLoadBinary:
    @pytest.mark.asyncio
    async def test_load_binary(self, gdb_client):
        sid = gdb_client.session_id
        resp = await gdb_client.post(
            f"/api/gdb/{sid}/load",
            json={"binary_path": "/tmp/test_binary"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "responses" in data

    @pytest.mark.asyncio
    async def test_load_binary_wrong_session(self, gdb_client):
        resp = await gdb_client.post(
            "/api/gdb/deadbeef12345678/load",
            json={"binary_path": "/tmp/test"},
        )
        assert resp.status_code == 404


class TestGdbExecControl:
    @pytest.mark.asyncio
    async def test_run(self, gdb_client):
        sid = gdb_client.session_id
        resp = await gdb_client.post(f"/api/gdb/{sid}/run")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_continue(self, gdb_client):
        sid = gdb_client.session_id
        resp = await gdb_client.post(f"/api/gdb/{sid}/continue")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_step_into(self, gdb_client):
        sid = gdb_client.session_id
        resp = await gdb_client.post(f"/api/gdb/{sid}/step/into")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_step_over(self, gdb_client):
        sid = gdb_client.session_id
        resp = await gdb_client.post(f"/api/gdb/{sid}/step/over")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_step_out(self, gdb_client):
        sid = gdb_client.session_id
        resp = await gdb_client.post(f"/api/gdb/{sid}/step/out")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_enable_record(self, gdb_client):
        sid = gdb_client.session_id
        resp = await gdb_client.post(f"/api/gdb/{sid}/record")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_step_back(self, gdb_client):
        sid = gdb_client.session_id
        resp = await gdb_client.post(f"/api/gdb/{sid}/step/back")
        assert resp.status_code == 200


class TestGdbBreakpoints:
    @pytest.mark.asyncio
    async def test_set_breakpoint(self, gdb_client):
        sid = gdb_client.session_id
        resp = await gdb_client.post(
            f"/api/gdb/{sid}/breakpoints",
            json={"location": "main"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_breakpoints(self, gdb_client):
        sid = gdb_client.session_id
        resp = await gdb_client.get(f"/api/gdb/{sid}/breakpoints")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_remove_breakpoint(self, gdb_client):
        sid = gdb_client.session_id
        resp = await gdb_client.delete(f"/api/gdb/{sid}/breakpoints/1")
        assert resp.status_code == 200


class TestGdbInspection:
    @pytest.mark.asyncio
    async def test_get_registers(self, gdb_client):
        sid = gdb_client.session_id
        # Mock two sequential writes for register names + values
        session = gdb_client.app.state.session_manager.get(sid)
        session.bridge._controller.write.side_effect = [
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
                            {"number": "0", "value": "0x1"},
                            {"number": "1", "value": "0x2"},
                        ]
                    },
                }
            ],
        ]
        resp = await gdb_client.get(f"/api/gdb/{sid}/registers")
        assert resp.status_code == 200
        data = resp.json()
        assert "registers" in data
        assert len(data["registers"]) == 2
        assert data["registers"][0]["name"] == "rax"

    @pytest.mark.asyncio
    async def test_get_stack(self, gdb_client):
        sid = gdb_client.session_id
        resp = await gdb_client.get(f"/api/gdb/{sid}/stack")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_read_memory(self, gdb_client):
        sid = gdb_client.session_id
        resp = await gdb_client.post(
            f"/api/gdb/{sid}/memory",
            json={"address": "0x401000", "size": 64},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_read_memory_invalid_size(self, gdb_client):
        sid = gdb_client.session_id
        resp = await gdb_client.post(
            f"/api/gdb/{sid}/memory",
            json={"address": "0x401000", "size": 999999},
        )
        assert resp.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_disassemble(self, gdb_client):
        sid = gdb_client.session_id
        resp = await gdb_client.post(
            f"/api/gdb/{sid}/disassemble",
            json={"function": "main"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_evaluate(self, gdb_client):
        sid = gdb_client.session_id
        resp = await gdb_client.post(
            f"/api/gdb/{sid}/evaluate",
            json={"expression": "$rax"},
        )
        assert resp.status_code == 200


class TestGdbDataFlow:
    """Integration tests: full data flow through the GDB API."""

    @pytest.mark.asyncio
    async def test_full_debug_flow(self, gdb_client):
        """Load → Breakpoint → Run → Step → Registers → Stack → Delete."""
        sid = gdb_client.session_id

        # Load binary
        r = await gdb_client.post(
            f"/api/gdb/{sid}/load", json={"binary_path": "/tmp/test"}
        )
        assert r.status_code == 200

        # Set breakpoint
        r = await gdb_client.post(
            f"/api/gdb/{sid}/breakpoints", json={"location": "_start"}
        )
        assert r.status_code == 200

        # Run
        r = await gdb_client.post(f"/api/gdb/{sid}/run")
        assert r.status_code == 200

        # Step into
        r = await gdb_client.post(f"/api/gdb/{sid}/step/into")
        assert r.status_code == 200

        # Get registers (need mock for two calls)
        session = gdb_client.app.state.session_manager.get(sid)
        session.bridge._controller.write.side_effect = [
            [
                {
                    "type": "result",
                    "message": "done",
                    "payload": {"register-names": ["rax"]},
                }
            ],
            [
                {
                    "type": "result",
                    "message": "done",
                    "payload": {"register-values": [{"number": "0", "value": "0x0"}]},
                }
            ],
        ]
        r = await gdb_client.get(f"/api/gdb/{sid}/registers")
        assert r.status_code == 200

        # Reset mock for remaining calls
        session.bridge._controller.write.side_effect = None
        session.bridge._controller.write.return_value = [_gdb_result()]

        # Get stack
        r = await gdb_client.get(f"/api/gdb/{sid}/stack")
        assert r.status_code == 200

        # Delete session
        r = await gdb_client.delete(f"/api/sessions/{sid}")
        assert r.status_code == 204
