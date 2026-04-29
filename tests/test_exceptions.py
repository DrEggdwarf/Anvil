"""Tests for Anvil exception hierarchy (core/exceptions.py)."""

from backend.app.core.exceptions import (
    AnvilError,
    BridgeCrash,
    BridgeError,
    BridgeNotReady,
    BridgeTimeout,
    InvalidCommand,
    InvalidFile,
    SessionError,
    SessionExpired,
    SessionLimitReached,
    SessionNotFound,
    SubprocessCrash,
    SubprocessError,
    SubprocessTimeout,
    ToolNotFound,
    ValidationError,
)


class TestExceptionHierarchy:
    """Verify all exceptions inherit from AnvilError."""

    def test_bridge_errors_are_anvil_errors(self):
        assert issubclass(BridgeError, AnvilError)
        assert issubclass(BridgeNotReady, BridgeError)
        assert issubclass(BridgeTimeout, BridgeError)
        assert issubclass(BridgeCrash, BridgeError)

    def test_session_errors_are_anvil_errors(self):
        assert issubclass(SessionError, AnvilError)
        assert issubclass(SessionNotFound, SessionError)
        assert issubclass(SessionLimitReached, SessionError)
        assert issubclass(SessionExpired, SessionError)

    def test_validation_errors_are_anvil_errors(self):
        assert issubclass(ValidationError, AnvilError)
        assert issubclass(InvalidFile, ValidationError)
        assert issubclass(InvalidCommand, ValidationError)

    def test_subprocess_errors_are_anvil_errors(self):
        assert issubclass(SubprocessError, AnvilError)
        assert issubclass(SubprocessTimeout, SubprocessError)
        assert issubclass(SubprocessCrash, SubprocessError)

    def test_tool_not_found_is_anvil_error(self):
        assert issubclass(ToolNotFound, AnvilError)


class TestExceptionAttributes:
    """Verify exception attributes (message, code, details)."""

    def test_anvil_error_defaults(self):
        err = AnvilError("test")
        assert err.message == "test"
        assert err.code == "ANVIL_ERROR"
        assert err.details == {}
        assert str(err) == "test"

    def test_bridge_not_ready(self):
        err = BridgeNotReady("gdb")
        assert "gdb" in err.message
        assert err.code == "BRIDGE_NOT_READY"
        assert err.details["bridge_type"] == "gdb"

    def test_bridge_timeout(self):
        err = BridgeTimeout("rizin", 30.0)
        assert "rizin" in err.message
        assert "30" in err.message
        assert err.code == "BRIDGE_TIMEOUT"
        assert err.details["timeout"] == 30.0

    def test_bridge_crash(self):
        err = BridgeCrash("gdb", exit_code=139)
        assert err.code == "BRIDGE_CRASH"
        assert err.details["exit_code"] == 139

    def test_session_not_found(self):
        err = SessionNotFound("abc123")
        assert "abc123" in err.message
        assert err.code == "SESSION_NOT_FOUND"
        assert err.details["session_id"] == "abc123"

    def test_session_limit_reached(self):
        err = SessionLimitReached(10)
        assert "10" in err.message
        assert err.code == "SESSION_LIMIT_REACHED"
        assert err.details["max_sessions"] == 10

    def test_session_expired(self):
        err = SessionExpired("abc123")
        assert err.code == "SESSION_EXPIRED"

    def test_invalid_file(self):
        err = InvalidFile("too large")
        assert "too large" in err.message
        assert err.code == "INVALID_FILE"

    def test_invalid_command(self):
        err = InvalidCommand("rm -rf /", "dangerous")
        assert err.code == "INVALID_COMMAND"
        assert err.details["command"] == "rm -rf /"

    def test_subprocess_timeout(self):
        err = SubprocessTimeout("gcc", 30.0)
        assert err.code == "SUBPROCESS_TIMEOUT"
        assert err.details["timeout"] == 30.0

    def test_subprocess_crash(self):
        err = SubprocessCrash("nasm", 1, stderr="error: invalid instruction")
        assert err.code == "SUBPROCESS_CRASH"
        assert err.details["exit_code"] == 1
        assert err.details["stderr"] == "error: invalid instruction"

    def test_tool_not_found(self):
        err = ToolNotFound("rizin")
        assert "rizin" in err.message
        assert err.code == "TOOL_NOT_FOUND"
