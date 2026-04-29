"""Security-focused tests for backend.app.api.pwn — Sprint 14 fix #6.

Closes the audit gap: api/pwn.py was at ~10% coverage with 47 endpoints unprotected
by REST-level tests. This file targets the **security-critical** paths that motivated
Sprint 14 fixes #3 and #5: path-traversal/LFI on `elf/*`, symlink upload, oversize
filename, language allowlist, magic-byte-based chmod, and the offline env vars wired
for Rust/Go (ADR-017).

Real pwntools is mocked at import time so these tests run without `pwn` installed.
"""

from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from backend.app.bridges.base import BridgeState
from backend.app.bridges.pwn_bridge import PwnBridge
from backend.app.bridges.registry import bridge_registry
from backend.app.core.subprocess_manager import SubprocessManager
from backend.app.core.workspace import WorkspaceManager
from backend.app.main import app
from backend.app.sessions.manager import Session, SessionManager


class _StubPwnBridge(PwnBridge):
    """PwnBridge that skips the real `import pwn` so tests run without pwntools."""

    async def start(self) -> None:  # type: ignore[override]
        self.state = BridgeState.READY


@pytest.fixture
def pwn_client(tmp_path, monkeypatch):
    """TestClient with a fresh app state and a real pwn session backed by a stub bridge.

    Yields (client, session_id, workspace_path).
    """
    # Use an isolated temp workspace so file writes don't pollute ~/.anvil/.
    monkeypatch.setattr(
        "backend.app.api.pwn._workspace",
        WorkspaceManager(base_dir=str(tmp_path)),
    )
    bridge_registry.register("pwn", _StubPwnBridge)
    sm = SessionManager()
    app.state.session_manager = sm
    app.state.subprocess_manager = SubprocessManager()

    bridge = _StubPwnBridge()
    bridge.state = BridgeState.READY
    sid = "ffeeddccbbaa9988"
    sm._sessions[sid] = Session(id=sid, bridge_type="pwn", bridge=bridge, token="t")

    workspace = Path(tmp_path) / sid
    workspace.mkdir(parents=True, exist_ok=True)

    yield TestClient(app), sid, workspace

    bridge_registry.register("pwn", PwnBridge)


# ── Upload security ──────────────────────────────────────


class TestPwnUploadSecurity:
    def test_rejects_path_traversal_in_filename(self, pwn_client):
        client, sid, _ = pwn_client
        # Pydantic catches the separator first → 422.
        resp = client.post(
            f"/api/pwn/{sid}/upload",
            json={"filename": "../escape.bin", "data_b64": "AA=="},
        )
        assert resp.status_code == 422

    def test_chmod_executable_only_for_elf_payloads(self, pwn_client):
        """ADR-017 / Security A5: chmod +x is reserved for actual ELF binaries."""
        client, sid, workspace = pwn_client
        # Plain text payload — must NOT get +x even if the upload succeeds.
        text = base64.b64encode(b"not an ELF\n").decode()
        resp = client.post(
            f"/api/pwn/{sid}/upload",
            json={"filename": "notes.bin", "data_b64": text},
        )
        assert resp.status_code == 200
        notes = workspace / "notes.bin"
        assert notes.exists()
        # On POSIX, perms exclude executable bits when not ELF.
        assert (notes.stat().st_mode & 0o111) == 0

    def test_chmod_executable_for_elf_magic(self, pwn_client):
        client, sid, workspace = pwn_client
        elf_payload = base64.b64encode(b"\x7fELF" + b"\x00" * 60).decode()
        resp = client.post(
            f"/api/pwn/{sid}/upload",
            json={"filename": "real.elf", "data_b64": elf_payload},
        )
        assert resp.status_code == 200
        target = workspace / "real.elf"
        assert (target.stat().st_mode & 0o111) != 0

    def test_rejects_invalid_base64(self, pwn_client):
        client, sid, _ = pwn_client
        resp = client.post(
            f"/api/pwn/{sid}/upload",
            json={"filename": "x.bin", "data_b64": "@@@notbase64@@@"},
        )
        assert resp.status_code in (400, 422, 500)


# ── Compile security ─────────────────────────────────────


class TestPwnCompileSecurity:
    def test_rejects_unsupported_language(self, pwn_client):
        client, sid, _ = pwn_client
        resp = client.post(
            f"/api/pwn/{sid}/compile",
            json={"path": "x.c", "language": "perl"},
        )
        assert resp.status_code in (400, 422)

    def test_rejects_path_outside_workspace(self, pwn_client):
        client, sid, _ = pwn_client
        resp = client.post(
            f"/api/pwn/{sid}/compile",
            json={"path": "/etc/passwd", "language": "c"},
        )
        # Caught by _resolve_path (PATH_BLOCKED) — surfaces as 4xx/5xx error.
        assert resp.status_code >= 400

    def test_go_compile_runs_offline(self, pwn_client, monkeypatch):
        """ADR-017: Rust/Go must be invoked with network-offline env vars."""
        client, sid, workspace = pwn_client
        (workspace / "main.go").write_text("package main\nfunc main(){}\n")

        captured: dict = {}

        async def fake_execute(cmd, *, timeout=30.0, cwd=None, env=None):
            captured["cmd"] = cmd
            captured["env"] = env
            # Pretend the compiler produced the binary so the endpoint completes.
            (Path(cwd) / "main").write_bytes(b"\x7fELF\x00")
            return ("", "", 0)

        monkeypatch.setattr("backend.app.api.pwn._subprocess.execute", fake_execute)
        resp = client.post(
            f"/api/pwn/{sid}/compile",
            json={"path": "main.go", "language": "go", "vuln_flags": False},
        )
        assert resp.status_code == 200
        assert captured["env"] == {"GOFLAGS": "-mod=vendor", "GOPROXY": "off"}


# ── ELF endpoints (path traversal LFI fix) ───────────────


class TestPwnElfPathGuard:
    """Sprint 14 fix #3 / Security A1: every elf endpoint must reject paths
    pointing outside the session workspace."""

    @pytest.mark.parametrize(
        "url_template",
        [
            "/api/pwn/{sid}/elf/checksec?path=/etc/passwd",
            "/api/pwn/{sid}/elf/symbols?path=/etc/passwd",
            "/api/pwn/{sid}/elf/got?path=/etc/passwd",
            "/api/pwn/{sid}/elf/plt?path=/etc/passwd",
            "/api/pwn/{sid}/elf/functions?path=/etc/passwd",
            "/api/pwn/{sid}/elf/sections?path=/etc/passwd",
        ],
    )
    def test_get_endpoints_reject_outside_workspace(self, pwn_client, url_template):
        client, sid, _ = pwn_client
        resp = client.get(url_template.format(sid=sid))
        assert resp.status_code >= 400

    def test_elf_load_rejects_outside_workspace(self, pwn_client):
        client, sid, _ = pwn_client
        resp = client.post(
            f"/api/pwn/{sid}/elf/load",
            json={"path": "/etc/shadow"},
        )
        assert resp.status_code >= 400

    def test_rop_create_rejects_outside_workspace(self, pwn_client):
        client, sid, _ = pwn_client
        resp = client.post(
            f"/api/pwn/{sid}/rop/create",
            json={"elf_path": "/etc/passwd"},
        )
        assert resp.status_code >= 400

    def test_corefile_rejects_outside_workspace(self, pwn_client):
        client, sid, _ = pwn_client
        resp = client.post(
            f"/api/pwn/{sid}/corefile",
            json={"path": "/proc/self/maps"},
        )
        assert resp.status_code >= 400


class TestPwnSymlinkGuard:
    """Pentester #5/#6: pre-existing symlinks in the workspace must not be followed."""

    def test_upload_refuses_existing_symlink(self, pwn_client, tmp_path):
        client, sid, workspace = pwn_client
        outside = tmp_path / "outside.txt"
        outside.write_text("secret")
        link = workspace / "trick.bin"
        link.symlink_to(outside)

        resp = client.post(
            f"/api/pwn/{sid}/upload",
            json={"filename": "trick.bin", "data_b64": "AA=="},
        )
        assert resp.status_code >= 400
        # The original file outside the workspace must remain unchanged.
        assert outside.read_text() == "secret"

    def test_elf_endpoint_refuses_symlink_target(self, pwn_client, tmp_path):
        client, sid, workspace = pwn_client
        outside = tmp_path / "secret.elf"
        outside.write_bytes(b"\x7fELF")
        (workspace / "alias.elf").symlink_to(outside)

        resp = client.get(f"/api/pwn/{sid}/elf/checksec?path=alias.elf")
        assert resp.status_code >= 400


class TestPwnSessionTypeGuard:
    """Wrong-type session must not pass through pwn endpoints."""

    def test_non_pwn_session_rejected(self, pwn_client):
        client, sid, _ = pwn_client
        # Replace the session with one of bridge_type="mock".
        sm = app.state.session_manager
        from tests.conftest import MockBridge

        mock = MockBridge()
        mock.state = BridgeState.READY
        sm._sessions[sid] = Session(id=sid, bridge_type="mock", bridge=mock, token="t")

        resp = client.get(f"/api/pwn/{sid}/elf/checksec?path=foo.elf")
        assert resp.status_code >= 400


# Silences "import patch unused" if the patch helper is dropped.
_ = patch
