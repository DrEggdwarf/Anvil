"""Anvil exception hierarchy.

All exceptions inherit from AnvilError and carry:
- message: human-readable description
- code: machine-readable error code (used by error middleware)
- details: optional dict with structured context
"""

from __future__ import annotations


class AnvilError(Exception):
    """Base exception for all Anvil errors."""

    def __init__(
        self,
        message: str,
        code: str = "ANVIL_ERROR",
        details: dict | None = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


# ── Bridge errors ────────────────────────────────────────


class BridgeError(AnvilError):
    def __init__(self, message: str, code: str = "BRIDGE_ERROR", **kwargs):
        super().__init__(message, code, **kwargs)


class BridgeNotReady(BridgeError):
    def __init__(self, bridge_type: str):
        super().__init__(
            f"Bridge '{bridge_type}' is not ready",
            code="BRIDGE_NOT_READY",
            details={"bridge_type": bridge_type},
        )


class BridgeTimeout(BridgeError):
    def __init__(self, bridge_type: str, timeout: float):
        super().__init__(
            f"Bridge '{bridge_type}' timed out after {timeout}s",
            code="BRIDGE_TIMEOUT",
            details={"bridge_type": bridge_type, "timeout": timeout},
        )


class BridgeCrash(BridgeError):
    def __init__(self, bridge_type: str, exit_code: int | None = None):
        super().__init__(
            f"Bridge '{bridge_type}' crashed",
            code="BRIDGE_CRASH",
            details={"bridge_type": bridge_type, "exit_code": exit_code},
        )


# ── Session errors ───────────────────────────────────────


class SessionError(AnvilError):
    def __init__(self, message: str, code: str = "SESSION_ERROR", **kwargs):
        super().__init__(message, code, **kwargs)


class SessionNotFound(SessionError):
    def __init__(self, session_id: str):
        super().__init__(
            f"Session '{session_id}' not found",
            code="SESSION_NOT_FOUND",
            details={"session_id": session_id},
        )


class SessionLimitReached(SessionError):
    def __init__(self, max_sessions: int):
        super().__init__(
            f"Maximum sessions ({max_sessions}) reached",
            code="SESSION_LIMIT_REACHED",
            details={"max_sessions": max_sessions},
        )


class SessionExpired(SessionError):
    def __init__(self, session_id: str):
        super().__init__(
            f"Session '{session_id}' has expired",
            code="SESSION_EXPIRED",
            details={"session_id": session_id},
        )


# ── Validation errors ────────────────────────────────────


class ValidationError(AnvilError):
    def __init__(self, message: str, code: str = "VALIDATION_ERROR", **kwargs):
        super().__init__(message, code, **kwargs)


class InvalidFile(ValidationError):
    def __init__(self, reason: str):
        super().__init__(
            f"Invalid file: {reason}",
            code="INVALID_FILE",
            details={"reason": reason},
        )


class InvalidCommand(ValidationError):
    def __init__(self, command: str, reason: str):
        super().__init__(
            f"Invalid command '{command}': {reason}",
            code="INVALID_COMMAND",
            details={"command": command, "reason": reason},
        )


# ── Subprocess errors ────────────────────────────────────


class SubprocessError(AnvilError):
    def __init__(self, message: str, code: str = "SUBPROCESS_ERROR", **kwargs):
        super().__init__(message, code, **kwargs)


class SubprocessTimeout(SubprocessError):
    def __init__(self, command: str, timeout: float):
        super().__init__(
            f"Subprocess '{command}' timed out after {timeout}s",
            code="SUBPROCESS_TIMEOUT",
            details={"command": command, "timeout": timeout},
        )


class SubprocessCrash(SubprocessError):
    def __init__(self, command: str, exit_code: int, stderr: str = ""):
        super().__init__(
            f"Subprocess '{command}' exited with code {exit_code}",
            code="SUBPROCESS_CRASH",
            details={"command": command, "exit_code": exit_code, "stderr": stderr},
        )


# ── Tool errors ──────────────────────────────────────────


class ToolNotFound(AnvilError):
    def __init__(self, tool: str):
        super().__init__(
            f"Tool '{tool}' not found on system",
            code="TOOL_NOT_FOUND",
            details={"tool": tool},
        )
