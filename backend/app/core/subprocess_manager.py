"""Subprocess manager — spawn, monitor, kill with timeout and cleanup.

No orphaned processes, ever. Every spawned process is tracked and cleaned up
on shutdown or when its parent session is destroyed.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime

from backend.app.core.config import settings
from backend.app.core.exceptions import SubprocessTimeout

logger = logging.getLogger(__name__)

# Maximum concurrent subprocesses to prevent resource exhaustion
_MAX_CONCURRENT_PROCESSES = 20


@dataclass
class ProcessHandle:
    """Handle to a tracked subprocess."""

    pid: int
    process: asyncio.subprocess.Process
    command: list[str]
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    timeout: float | None = None

    @property
    def is_alive(self) -> bool:
        return self.process.returncode is None


class SubprocessManager:
    """Manages subprocess lifecycle: spawn, execute, kill, cleanup."""

    def __init__(self) -> None:
        self._processes: dict[int, ProcessHandle] = {}
        self._semaphore = asyncio.Semaphore(_MAX_CONCURRENT_PROCESSES)

    async def spawn(
        self,
        command: list[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> ProcessHandle:
        """Spawn a subprocess and track it. Returns a handle."""
        await self._semaphore.acquire()
        try:
            merged_env = {**os.environ, **(env or {})}

            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=merged_env,
            )

            handle = ProcessHandle(
                pid=process.pid,
                process=process,
                command=command,
                timeout=timeout or settings.subprocess_default_timeout_seconds,
            )
            self._processes[process.pid] = handle
            logger.info("Spawned process %d: %s", process.pid, " ".join(command))
            return handle
        except Exception:
            self._semaphore.release()
            raise

    async def kill(
        self,
        handle: ProcessHandle,
        grace_period: float | None = None,
    ) -> None:
        """Kill a subprocess: SIGTERM → grace period → SIGKILL."""
        if not handle.is_alive:
            self._processes.pop(handle.pid, None)
            return

        grace = grace_period or settings.subprocess_kill_grace_seconds

        try:
            handle.process.terminate()
            try:
                await asyncio.wait_for(handle.process.wait(), timeout=grace)
            except TimeoutError:
                handle.process.kill()
                await handle.process.wait()
        except ProcessLookupError:
            pass  # Already dead
        finally:
            self._processes.pop(handle.pid, None)
            self._semaphore.release()
            logger.info("Killed process %d", handle.pid)

    async def execute(
        self,
        command: list[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> tuple[str, str, int]:
        """Spawn, wait for completion, return (stdout, stderr, returncode).

        Raises SubprocessTimeout if the process doesn't finish in time.
        """
        handle = await self.spawn(command, timeout=timeout, cwd=cwd, env=env)
        effective_timeout = handle.timeout

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                handle.process.communicate(),
                timeout=effective_timeout,
            )
        except TimeoutError:
            await self.kill(handle)
            raise SubprocessTimeout(command[0], effective_timeout) from None
        else:
            # Only release here — kill() already releases in timeout path
            self._processes.pop(handle.pid, None)
            self._semaphore.release()

        # Enforce output size limit to prevent OOM
        max_bytes = settings.subprocess_max_output_bytes
        stdout_bytes = (stdout_bytes or b"")[:max_bytes]
        stderr_bytes = (stderr_bytes or b"")[:max_bytes]

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        returncode = handle.process.returncode or 0

        return stdout, stderr, returncode

    async def cleanup_all(self) -> int:
        """Kill all tracked processes. Returns count of processes killed."""
        count = 0
        for handle in list(self._processes.values()):
            await self.kill(handle)
            count += 1
        return count

    @property
    def active_count(self) -> int:
        return sum(1 for h in self._processes.values() if h.is_alive)

    @property
    def tracked_count(self) -> int:
        return len(self._processes)
