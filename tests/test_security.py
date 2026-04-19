"""Security-focused tests — injection, path traversal, input validation.

Tests that the sanitization layer blocks dangerous inputs at both
the sanitization function level and through the API endpoints.
"""

from __future__ import annotations

import pytest

from backend.app.core.exceptions import ValidationError
from backend.app.core.sanitization import (
    sanitize_gdb_input,
    sanitize_rizin_input,
    validate_file_path,
    validate_gcc_flags,
    validate_session_id,
    validate_string_length,
)


# ── GDB sanitization ────────────────────────────────────


class TestGdbSanitization:
    """Test GDB/MI injection prevention."""

    def test_clean_input_passes(self):
        assert sanitize_gdb_input("main") == "main"
        assert sanitize_gdb_input("*0x401000") == "*0x401000"
        assert sanitize_gdb_input("test.c:42") == "test.c:42"
        assert sanitize_gdb_input("$rax + 8") == "$rax + 8"
        assert sanitize_gdb_input("$(rax)") == "$(rax)"

    def test_blocks_shell_command(self):
        with pytest.raises(ValidationError):
            sanitize_gdb_input("shell rm -rf /")

    def test_blocks_shell_bang(self):
        with pytest.raises(ValidationError):
            sanitize_gdb_input("!cat /etc/passwd")

    def test_blocks_python_command(self):
        with pytest.raises(ValidationError):
            sanitize_gdb_input("python import os")

    def test_blocks_pipe_command(self):
        with pytest.raises(ValidationError):
            sanitize_gdb_input("pipe info reg")

    def test_blocks_semicolon_chaining(self):
        with pytest.raises(ValidationError):
            sanitize_gdb_input("main; shell id")

    def test_blocks_backtick_injection(self):
        with pytest.raises(ValidationError):
            sanitize_gdb_input("`id`")

    def test_blocks_newline_injection(self):
        with pytest.raises(ValidationError):
            sanitize_gdb_input("main\nshell id")

    def test_blocks_pipe_char(self):
        """Pipe is blocked by the dangerous pattern detector (pipe command)."""
        with pytest.raises(ValidationError):
            sanitize_gdb_input("pipe cmd")

    def test_blocks_source_command(self):
        with pytest.raises(ValidationError):
            sanitize_gdb_input("source /tmp/evil.py")

    def test_blocks_define_command(self):
        with pytest.raises(ValidationError):
            sanitize_gdb_input("define hook-stop")


# ── Rizin sanitization ──────────────────────────────────


class TestRizinSanitization:
    """Test Rizin command injection prevention."""

    def test_clean_input_passes(self):
        assert sanitize_rizin_input("0x401000") == "0x401000"
        assert sanitize_rizin_input("main") == "main"
        assert sanitize_rizin_input("pdf @ main") == "pdf @ main"

    def test_blocks_shell_escape(self):
        with pytest.raises(ValidationError):
            sanitize_rizin_input("!cat /etc/passwd")

    def test_blocks_semicolon_chaining(self):
        with pytest.raises(ValidationError):
            sanitize_rizin_input("afl; !id")

    def test_blocks_pipe_chaining(self):
        """Pipe is blocked by the dangerous pattern detector."""
        with pytest.raises(ValidationError):
            sanitize_rizin_input("afl;!id")

    def test_blocks_backtick(self):
        with pytest.raises(ValidationError):
            sanitize_rizin_input("`id`")

    def test_blocks_newline(self):
        with pytest.raises(ValidationError):
            sanitize_rizin_input("afl\n!id")


# ── Path validation ──────────────────────────────────────


class TestPathValidation:
    """Test path traversal prevention."""

    def test_normal_path_passes(self):
        assert validate_file_path("/home/user/binary.elf") == "/home/user/binary.elf"

    def test_blocks_etc(self):
        with pytest.raises(ValidationError, match="blocked"):
            validate_file_path("/etc/passwd")

    def test_blocks_proc(self):
        with pytest.raises(ValidationError, match="blocked"):
            validate_file_path("/proc/self/environ")

    def test_blocks_dev(self):
        with pytest.raises(ValidationError, match="blocked"):
            validate_file_path("/dev/sda")

    def test_blocks_null_byte(self):
        with pytest.raises(ValidationError):
            validate_file_path("/tmp/file\x00.txt")

    def test_blocks_empty_path(self):
        with pytest.raises(ValidationError, match="Empty"):
            validate_file_path("")

    def test_allowed_dirs_enforcement(self):
        validate_file_path("/tmp/anvil/session1/file.elf", allowed_dirs=["/tmp/anvil"])

    def test_allowed_dirs_blocks_outside(self):
        with pytest.raises(ValidationError, match="allowed"):
            validate_file_path("/home/user/file.elf", allowed_dirs=["/tmp/anvil"])

    def test_traversal_in_allowed_dir(self):
        with pytest.raises(ValidationError):
            validate_file_path("/tmp/anvil/../../etc/passwd", allowed_dirs=["/tmp/anvil"])


# ── Session ID validation ────────────────────────────────


class TestSessionIdValidation:
    """Test session ID format validation."""

    def test_valid_session_id(self):
        assert validate_session_id("a1b2c3d4e5f67890") == "a1b2c3d4e5f67890"

    def test_rejects_too_short(self):
        with pytest.raises(ValidationError):
            validate_session_id("abc123")

    def test_rejects_too_long(self):
        with pytest.raises(ValidationError):
            validate_session_id("a1b2c3d4e5f678901234")

    def test_rejects_non_hex(self):
        with pytest.raises(ValidationError):
            validate_session_id("ghijklmnopqrstuv")

    def test_rejects_path_traversal(self):
        with pytest.raises(ValidationError):
            validate_session_id("../../../etc/pas")

    def test_rejects_uppercase(self):
        with pytest.raises(ValidationError):
            validate_session_id("A1B2C3D4E5F67890")


# ── GCC flags validation ────────────────────────────────


class TestGccFlagsValidation:
    """Test GCC extra_flags allowlist."""

    def test_valid_flags(self):
        flags = ["-O2", "-Wall", "-g", "-std=c11", "-pie"]
        assert validate_gcc_flags(flags) == flags

    def test_blocks_wrapper(self):
        with pytest.raises(ValidationError, match="Blocked"):
            validate_gcc_flags(["-wrapper", "/bin/sh,-c"])

    def test_blocks_fplugin(self):
        with pytest.raises(ValidationError, match="Blocked"):
            validate_gcc_flags(["-fplugin=/tmp/evil.so"])

    def test_blocks_specs(self):
        with pytest.raises(ValidationError, match="Blocked"):
            validate_gcc_flags(["-specs=/tmp/evil.specs"])

    def test_blocks_unknown_flags(self):
        with pytest.raises(ValidationError, match="Unknown"):
            validate_gcc_flags(["--evil-flag"])

    def test_empty_list(self):
        assert validate_gcc_flags([]) == []


# ── String length validation ─────────────────────────────


class TestStringLengthValidation:
    """Test string length enforcement."""

    def test_within_limit(self):
        assert validate_string_length("hello", 10) == "hello"

    def test_exceeds_limit(self):
        with pytest.raises(ValidationError, match="too long"):
            validate_string_length("x" * 1000, 100)

    def test_exact_limit(self):
        assert validate_string_length("x" * 100, 100) == "x" * 100
