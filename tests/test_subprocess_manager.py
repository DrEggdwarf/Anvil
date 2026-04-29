"""Tests for SubprocessManager (core/subprocess_manager.py).

Tests use real subprocesses (echo, sleep, false) — no mocks needed
since these are basic POSIX commands available everywhere.
"""

import pytest
import pytest_asyncio

from backend.app.core.exceptions import SubprocessTimeout
from backend.app.core.subprocess_manager import SubprocessManager


@pytest_asyncio.fixture
async def spm() -> SubprocessManager:
    manager = SubprocessManager()
    yield manager
    await manager.cleanup_all()


class TestSpawn:
    @pytest.mark.asyncio
    async def test_spawn_returns_handle(self, spm: SubprocessManager):
        handle = await spm.spawn(["echo", "hello"])
        assert handle.pid > 0
        assert handle.command == ["echo", "hello"]
        # echo finishes immediately
        await handle.process.wait()

    @pytest.mark.asyncio
    async def test_spawn_tracks_process(self, spm: SubprocessManager):
        handle = await spm.spawn(["sleep", "10"])
        assert spm.tracked_count == 1
        assert handle.is_alive
        await spm.kill(handle)
        assert spm.tracked_count == 0


class TestExecute:
    @pytest.mark.asyncio
    async def test_execute_returns_stdout(self, spm: SubprocessManager):
        stdout, stderr, rc = await spm.execute(["echo", "hello world"])
        assert stdout.strip() == "hello world"
        assert rc == 0

    @pytest.mark.asyncio
    async def test_execute_returns_stderr(self, spm: SubprocessManager):
        stdout, stderr, rc = await spm.execute(["sh", "-c", "echo error >&2; exit 1"])
        assert "error" in stderr
        assert rc == 1

    @pytest.mark.asyncio
    async def test_execute_timeout_raises(self, spm: SubprocessManager):
        with pytest.raises(SubprocessTimeout):
            await spm.execute(["sleep", "60"], timeout=0.1)

    @pytest.mark.asyncio
    async def test_execute_with_cwd(self, spm: SubprocessManager, tmp_path):
        stdout, _, rc = await spm.execute(["pwd"], cwd=str(tmp_path))
        assert stdout.strip() == str(tmp_path)
        assert rc == 0


class TestKill:
    @pytest.mark.asyncio
    async def test_kill_running_process(self, spm: SubprocessManager):
        handle = await spm.spawn(["sleep", "60"])
        assert handle.is_alive
        await spm.kill(handle)
        assert not handle.is_alive
        assert spm.tracked_count == 0

    @pytest.mark.asyncio
    async def test_kill_already_dead(self, spm: SubprocessManager):
        handle = await spm.spawn(["echo", "done"])
        await handle.process.wait()
        # Should not raise
        await spm.kill(handle)

    @pytest.mark.asyncio
    async def test_kill_with_grace_period(self, spm: SubprocessManager):
        handle = await spm.spawn(["sleep", "60"])
        await spm.kill(handle, grace_period=0.1)
        assert not handle.is_alive


class TestCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_all_kills_everything(self, spm: SubprocessManager):
        await spm.spawn(["sleep", "60"])
        await spm.spawn(["sleep", "60"])
        assert spm.tracked_count == 2
        count = await spm.cleanup_all()
        assert count == 2
        assert spm.tracked_count == 0

    @pytest.mark.asyncio
    async def test_active_count(self, spm: SubprocessManager):
        h1 = await spm.spawn(["sleep", "60"])
        h2 = await spm.spawn(["echo", "done"])
        await h2.process.wait()
        assert spm.active_count == 1
        await spm.kill(h1)
