"""Tests for compilation API routes — REST endpoints for compile, analyze, files."""

from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from backend.app.core.workspace import WorkspaceManager
from backend.app.main import app


# ── Fixtures ─────────────────────────────────────────────


@pytest_asyncio.fixture
async def client(tmp_path):
    """Client with lifespan + patched workspace to use tmp_path."""
    from backend.app.core.lifecycle import lifespan

    with patch(
        "backend.app.api.compile._get_workspace_mgr",
        return_value=WorkspaceManager(base_dir=str(tmp_path)),
    ):
        async with lifespan(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                yield c


async def _create_session(client: AsyncClient, bridge_type: str = "mock") -> str:
    """Helper: create a session and return its ID."""
    resp = await client.post("/api/sessions", json={"bridge_type": bridge_type})
    assert resp.status_code == 201
    return resp.json()["id"]


# ── File management routes ───────────────────────────────


class TestFileRoutes:
    @pytest.mark.asyncio
    async def test_write_and_read(self, client):
        sid = await _create_session(client)
        # Write
        resp = await client.post(
            f"/api/compile/{sid}/files",
            json={"filename": "test.asm", "content": "section .text"},
        )
        assert resp.status_code == 200
        assert resp.json()["filename"] == "test.asm"

        # Read back
        resp = await client.get(f"/api/compile/{sid}/files/test.asm")
        assert resp.status_code == 200
        assert resp.json()["content"] == "section .text"

    @pytest.mark.asyncio
    async def test_list_files(self, client):
        sid = await _create_session(client)
        await client.post(
            f"/api/compile/{sid}/files",
            json={"filename": "a.asm", "content": "code1"},
        )
        await client.post(
            f"/api/compile/{sid}/files",
            json={"filename": "b.c", "content": "code2"},
        )
        resp = await client.get(f"/api/compile/{sid}/files")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == sid
        assert len(data["files"]) == 2

    @pytest.mark.asyncio
    async def test_delete_file(self, client):
        sid = await _create_session(client)
        await client.post(
            f"/api/compile/{sid}/files",
            json={"filename": "del.asm", "content": "x"},
        )
        resp = await client.delete(f"/api/compile/{sid}/files/del.asm")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, client):
        sid = await _create_session(client)
        resp = await client.get(f"/api/compile/{sid}/files/nope.asm")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_session(self, client):
        resp = await client.get("/api/compile/deadbeef12345678/files")
        assert resp.status_code == 404


# ── ASM compilation routes ───────────────────────────────


class TestAsmCompileRoute:
    @pytest.mark.asyncio
    async def test_compile_asm_success(self, client):
        sid = await _create_session(client)
        with patch(
            "backend.app.bridges.compilation.CompilationBridge.compile_asm",
            new_callable=AsyncMock,
            return_value={
                "success": True,
                "stage": "link",
                "binary_path": "/tmp/prog",
                "object_path": "/tmp/prog.o",
                "errors": [],
                "stdout": "",
                "stderr": "",
                "returncode": 0,
            },
        ):
            resp = await client.post(
                f"/api/compile/{sid}/asm",
                json={
                    "source_code": "section .text\nglobal _start\n_start: mov eax,1\nint 0x80\n"
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["binary_path"] is not None

    @pytest.mark.asyncio
    async def test_compile_asm_error(self, client):
        sid = await _create_session(client)
        with patch(
            "backend.app.bridges.compilation.CompilationBridge.compile_asm",
            new_callable=AsyncMock,
            return_value={
                "success": False,
                "stage": "assemble",
                "binary_path": None,
                "object_path": None,
                "errors": [{"file": "program.asm", "line": 5, "severity": "error", "message": "bad instruction"}],
                "stdout": "",
                "stderr": "program.asm:5: error: bad instruction",
                "returncode": 1,
            },
        ):
            resp = await client.post(
                f"/api/compile/{sid}/asm",
                json={"source_code": "bad code"},
            )
            assert resp.status_code == 200  # Compilation errors are not HTTP errors
            data = resp.json()
            assert data["success"] is False
            assert len(data["errors"]) == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize("assembler", ["gas", "fasm"])
    async def test_compile_asm_alternate_assemblers(self, client, assembler):
        """Sprint 14 fix #6: ensure GAS/FASM are wired through the route, not just the bridge."""
        sid = await _create_session(client)
        with patch(
            "backend.app.bridges.compilation.CompilationBridge.compile_asm",
            new_callable=AsyncMock,
            return_value={
                "success": True, "stage": "link", "binary_path": "/tmp/p",
                "object_path": "/tmp/p.o", "errors": [], "stdout": "",
                "stderr": "", "returncode": 0,
            },
        ) as mock_compile:
            resp = await client.post(
                f"/api/compile/{sid}/asm",
                json={"source_code": "nop", "assembler": assembler},
            )
            assert resp.status_code == 200
            assert mock_compile.await_args.kwargs.get("assembler") == assembler

    @pytest.mark.asyncio
    async def test_compile_asm_invalid_assembler_rejected(self, client):
        """Pydantic regex `^(nasm|gas|fasm)$` must reject unknown assemblers at the route boundary."""
        sid = await _create_session(client)
        resp = await client.post(
            f"/api/compile/{sid}/asm",
            json={"source_code": "nop", "assembler": "; rm -rf /"},
        )
        assert resp.status_code == 422


# ── C compilation routes ─────────────────────────────────


class TestCCompileRoute:
    @pytest.mark.asyncio
    async def test_compile_c_success(self, client):
        sid = await _create_session(client)
        with patch(
            "backend.app.bridges.compilation.CompilationBridge.compile_c",
            new_callable=AsyncMock,
            return_value={
                "success": True,
                "stage": "compile",
                "binary_path": "/tmp/prog",
                "errors": [],
                "warnings": [],
                "stdout": "",
                "stderr": "",
                "returncode": 0,
            },
        ):
            resp = await client.post(
                f"/api/compile/{sid}/c",
                json={"source_code": "int main() { return 0; }"},
            )
            assert resp.status_code == 200
            assert resp.json()["success"] is True

    @pytest.mark.asyncio
    async def test_compile_c_with_security_flags(self, client):
        sid = await _create_session(client)
        with patch(
            "backend.app.bridges.compilation.CompilationBridge.compile_c",
            new_callable=AsyncMock,
            return_value={
                "success": True,
                "stage": "compile",
                "binary_path": "/tmp/prog",
                "errors": [],
                "warnings": [],
                "stdout": "",
                "stderr": "",
                "returncode": 0,
            },
        ):
            resp = await client.post(
                f"/api/compile/{sid}/c",
                json={
                    "source_code": "int main() { return 0; }",
                    "security_flags": ["no_pie", "no_canary", "no_nx"],
                },
            )
            assert resp.status_code == 200
            assert resp.json()["success"] is True


# ── Binary analysis routes ───────────────────────────────


class TestBinaryAnalysisRoutes:
    @pytest.mark.asyncio
    async def test_checksec(self, client):
        sid = await _create_session(client)
        with patch(
            "backend.app.bridges.binary_analyzer.BinaryAnalyzer.checksec",
            new_callable=AsyncMock,
            return_value={
                "path": "/tmp/prog",
                "relro": "full",
                "canary": True,
                "nx": True,
                "pie": True,
                "rpath": False,
                "runpath": False,
                "symbols": True,
                "fortify": False,
            },
        ):
            resp = await client.get(f"/api/compile/{sid}/checksec/prog")
            assert resp.status_code == 200
            data = resp.json()
            assert data["relro"] == "full"
            assert data["canary"] is True

    @pytest.mark.asyncio
    async def test_fileinfo(self, client):
        sid = await _create_session(client)
        with patch(
            "backend.app.bridges.binary_analyzer.BinaryAnalyzer.file_info",
            new_callable=AsyncMock,
            return_value={
                "path": "/tmp/prog",
                "type": "ELF 64-bit LSB executable",
                "details": "ELF 64-bit LSB executable, x86-64",
                "success": True,
            },
        ):
            resp = await client.get(f"/api/compile/{sid}/fileinfo/prog")
            assert resp.status_code == 200
            assert "ELF" in resp.json()["type"]

    @pytest.mark.asyncio
    async def test_sections(self, client):
        sid = await _create_session(client)
        with patch(
            "backend.app.bridges.binary_analyzer.BinaryAnalyzer.sections",
            new_callable=AsyncMock,
            return_value=[
                {
                    "name": ".text",
                    "type": "PROGBITS",
                    "address": "0x401000",
                    "offset": "0x1000",
                    "size": 16,
                    "flags": "AX",
                },
            ],
        ):
            resp = await client.get(f"/api/compile/{sid}/sections/prog")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["sections"]) == 1
            assert data["sections"][0]["name"] == ".text"
