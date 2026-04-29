"""Tests for Sprint 6 bug fixes — workspace, subprocess, GDB lock."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.core.subprocess_manager import SubprocessManager


class TestWorkspaceExpanduser:
    """BUG FIX: workspace_base_dir with ~ must be expanded."""

    def test_tilde_expanded(self):
        from backend.app.core.workspace import WorkspaceManager

        with patch.object(Path, "mkdir"):
            wm = WorkspaceManager(base_dir="~/test_workspace")
        # Should NOT contain literal ~
        assert "~" not in str(wm.base_dir)
        assert str(wm.base_dir).startswith("/")

    def test_absolute_path_unchanged(self):
        from backend.app.core.workspace import WorkspaceManager

        with patch.object(Path, "mkdir"):
            wm = WorkspaceManager(base_dir="/tmp/test_anvil")
        assert str(wm.base_dir) == "/tmp/test_anvil"


class TestSubprocessSemaphoreLeak:
    """BUG FIX: semaphore must be released if spawn() fails."""

    @pytest.mark.asyncio
    async def test_semaphore_released_on_spawn_failure(self):
        spm = SubprocessManager()
        initial_value = spm._semaphore._value

        # Mock create_subprocess_exec to fail
        with patch("asyncio.create_subprocess_exec", side_effect=OSError("command not found")):
            with pytest.raises(OSError):
                await spm.spawn(["nonexistent_binary"])

        # Semaphore should be back to initial value (not leaked)
        assert spm._semaphore._value == initial_value

    @pytest.mark.asyncio
    async def test_semaphore_released_after_successful_execute(self):
        spm = SubprocessManager()
        initial_value = spm._semaphore._value

        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"ok", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await spm.execute(["echo", "test"])

        assert spm._semaphore._value == initial_value


class TestGdbBridgeLock:
    """FIX: GDB bridge must serialize concurrent requests."""

    @pytest.mark.asyncio
    async def test_gdb_bridge_has_lock(self):
        from backend.app.bridges.gdb_bridge import GdbBridge

        bridge = GdbBridge()
        assert hasattr(bridge, "_lock")
        assert isinstance(bridge._lock, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_concurrent_execute_serialized(self):
        from backend.app.bridges.base import BridgeState
        from backend.app.bridges.gdb_bridge import GdbBridge

        bridge = GdbBridge()
        bridge.state = BridgeState.READY

        call_order = []
        call_count = 0

        def mock_write(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            order = call_count
            call_order.append(f"start_{order}")
            call_order.append(f"end_{order}")
            return [{"type": "result", "payload": None}]

        bridge._controller = MagicMock()
        bridge._controller.write = mock_write
        bridge.health = AsyncMock(return_value=True)

        # Execute two commands concurrently — they should be serialized
        await asyncio.gather(
            bridge.execute("-exec-run"),
            bridge.execute("-exec-continue"),
        )

        assert call_count == 2
        # Due to lock, calls must be sequential (start_1, end_1, start_2, end_2)
        assert call_order[0] == "start_1"
        assert call_order[1] == "end_1"
