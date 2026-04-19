"""Base bridge — abstract contract for all tool bridges.

Every bridge (GDB, rizin, pwntools, binwalk, pymodbus) inherits BaseBridge
and implements the same lifecycle: start → execute → stop.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from backend.app.core.exceptions import BridgeNotReady


class BridgeState(StrEnum):
    CREATED = "created"
    STARTING = "starting"
    READY = "ready"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class BaseBridge(ABC):
    """Abstract base for all tool bridges."""

    bridge_type: str = "base"

    def __init__(self) -> None:
        self._state = BridgeState.CREATED

    @property
    def state(self) -> BridgeState:
        return self._state

    @state.setter
    def state(self, value: BridgeState) -> None:
        self._state = value

    def _require_ready(self) -> None:
        """Raise BridgeNotReady if the bridge isn't in READY state."""
        if self._state != BridgeState.READY:
            raise BridgeNotReady(self.bridge_type)

    @abstractmethod
    async def start(self) -> None:
        """Initialize the bridge (spawn subprocess, connect, etc.)."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Cleanup (kill subprocess, disconnect, release resources)."""
        ...

    @abstractmethod
    async def health(self) -> bool:
        """Return True if the bridge is healthy and responsive."""
        ...

    @abstractmethod
    async def execute(self, command: str, **kwargs: Any) -> Any:
        """Execute a command on the underlying tool. Returns tool-specific result."""
        ...
