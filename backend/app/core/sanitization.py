"""Input sanitization — defense against injection attacks.

Provides validators for user input that reaches subprocess commands,
file paths, and tool-specific command languages (GDB/MI, Rizin).
"""

from __future__ import annotations

import re
from pathlib import Path

from backend.app.core.exceptions import ValidationError

# ── GDB/MI sanitization ─────────────────────────────────

# GDB commands that could escape to host shell
_GDB_DANGEROUS_PATTERNS = re.compile(
    r"""
    (?:^|\s|;)            # Start of string, whitespace, or semicolon
    (?:
        shell\b           # shell command
        |!                # ! prefix = shell
        |python\b         # python command
        |pipe\b           # pipe to shell
        |source\b         # source arbitrary file
        |define\b         # define custom command
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Characters that could enable command chaining or quote-escape in GDB
# `"` is blocked because GDB f-strings wrap user input in `-interpreter-exec console "{cmd}"`,
# and an injected `"` would close the quote and allow appending arbitrary commands.
_GDB_INJECTION_CHARS = re.compile(r'[;`\n\r"]')


def sanitize_gdb_input(value: str, field_name: str = "input") -> str:
    """Sanitize user input destined for GDB/MI commands.

    Blocks shell escape sequences, command chaining, and dangerous commands.
    """
    if _GDB_INJECTION_CHARS.search(value):
        raise ValidationError(
            f"Invalid characters in {field_name}: command injection blocked",
            code="INJECTION_BLOCKED",
            details={"field": field_name},
        )
    if _GDB_DANGEROUS_PATTERNS.search(value):
        raise ValidationError(
            f"Dangerous command pattern in {field_name}",
            code="INJECTION_BLOCKED",
            details={"field": field_name},
        )
    return value


# ── Rizin sanitization ──────────────────────────────────

# Rizin's shell escape is ! prefix
_RIZIN_DANGEROUS_PATTERNS = re.compile(
    r"""
    (?:^|\s|;)
    (?:
        !                 # ! prefix = shell command
        |\.\.             # .. command navigation
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

_RIZIN_INJECTION_CHARS = re.compile(r"[;`\n\r]")


def sanitize_rizin_input(value: str, field_name: str = "input") -> str:
    """Sanitize user input destined for Rizin commands.

    Blocks shell escape, command chaining, and ! prefix.
    """
    if _RIZIN_INJECTION_CHARS.search(value):
        raise ValidationError(
            f"Invalid characters in {field_name}: command injection blocked",
            code="INJECTION_BLOCKED",
            details={"field": field_name},
        )
    if _RIZIN_DANGEROUS_PATTERNS.search(value):
        raise ValidationError(
            f"Dangerous command pattern in {field_name}",
            code="INJECTION_BLOCKED",
            details={"field": field_name},
        )
    return value


# ── Path validation ──────────────────────────────────────

# Directories that must never be accessed
_BLOCKED_PATHS = frozenset({
    "/etc", "/proc", "/sys", "/dev", "/root", "/boot",
    "/var/run", "/var/log", "/run",
})


def validate_file_path(
    path: str,
    *,
    allowed_dirs: list[str] | None = None,
    field_name: str = "path",
) -> str:
    """Validate a file path — block traversal and sensitive directories.

    If allowed_dirs is provided, path must be under one of them.
    """
    if not path or not path.strip():
        raise ValidationError(
            f"Empty {field_name}",
            code="VALIDATION_ERROR",
        )

    # Block null bytes
    if "\x00" in path:
        raise ValidationError(
            f"Null byte in {field_name}",
            code="INJECTION_BLOCKED",
        )

    try:
        resolved = Path(path).resolve()
    except (ValueError, OSError):
        raise ValidationError(
            f"Invalid {field_name}",
            code="VALIDATION_ERROR",
        ) from None

    # Block sensitive system directories
    for blocked in _BLOCKED_PATHS:
        if str(resolved).startswith(blocked):
            raise ValidationError(
                f"Access to {blocked} is blocked",
                code="PATH_BLOCKED",
                details={"field": field_name, "path": str(resolved)},
            )

    # If allowed dirs specified, enforce containment
    if allowed_dirs and not any(
        resolved.is_relative_to(Path(d).resolve())
        for d in allowed_dirs
    ):
        raise ValidationError(
            f"{field_name} must be within allowed directories",
            code="PATH_BLOCKED",
            details={"field": field_name},
        )

    return path


# ── Session ID validation ────────────────────────────────

_SESSION_ID_PATTERN = re.compile(r"^[a-f0-9]{16}$")


def validate_session_id(session_id: str) -> str:
    """Validate session ID format — must be 16 hex chars."""
    if not _SESSION_ID_PATTERN.match(session_id):
        raise ValidationError(
            "Invalid session ID format",
            code="VALIDATION_ERROR",
            details={"session_id": session_id},
        )
    return session_id


# ── GCC flags allowlist ──────────────────────────────────

_ALLOWED_GCC_FLAG_PREFIXES = frozenset({
    "-O", "-g", "-W", "-w", "-f", "-m", "-std=",
    "-D", "-U", "-I", "-L", "-l", "-s", "-c",
    "-pie", "-no-pie", "-static", "-shared",
    "-pthread", "-rdynamic",
})

# Explicitly dangerous flags that bypass the allowlist via known-safe prefixes.
# `-Wl,`/`-Wa,`/`-Wp,` slip past `-W` (warnings) and pass arbitrary args to linker/assembler/preprocessor.
# `-l/path` and `-L/path` can pull libraries from anywhere on disk.
_BLOCKED_GCC_FLAGS = frozenset({
    "-wrapper", "-fplugin", "-fplugin-arg",
    "-fprofile-generate", "-fprofile-use",
    "--sysroot", "-isysroot", "-isystem",
    "-specs", "-dumpspecs",
    "-Wl,", "-Wa,", "-Wp,",
    "-Xlinker", "-Xassembler", "-Xpreprocessor",
    "-rpath",
})

def _validate_gcc_path_flag(flag: str, prefix: str) -> None:
    """Reject path-bearing flags (`-I/etc`, `-L/proc`, `-l/abs/path`) that escape the workspace."""
    payload = flag[len(prefix):]
    if not payload:
        return
    # Reject library specs containing path separators (`-l/abs/path` or `-l../foo`).
    if prefix == "-l" and ("/" in payload or "\\" in payload):
        raise ValidationError(
            f"Library path traversal blocked in flag: {flag}",
            code="INJECTION_BLOCKED",
            details={"flag": flag},
        )
    # Reject -I/-L pointing at sensitive system dirs.
    if prefix in ("-I", "-L") and (payload.startswith("/") or ".." in payload):
        for blocked in _BLOCKED_PATHS:
            if payload.startswith(blocked):
                raise ValidationError(
                    f"Sensitive path blocked in flag: {flag}",
                    code="PATH_BLOCKED",
                    details={"flag": flag, "path": payload},
                )


def validate_gcc_flags(flags: list[str]) -> list[str]:
    """Validate GCC extra flags — block dangerous flags, allow known-safe prefixes."""
    validated = []
    for flag in flags:
        flag_lower = flag.lower()
        # Block explicitly dangerous flags (case-insensitive prefix match)
        if any(flag_lower.startswith(b.lower()) for b in _BLOCKED_GCC_FLAGS):
            raise ValidationError(
                f"Blocked GCC flag: {flag}",
                code="INJECTION_BLOCKED",
                details={"flag": flag},
            )
        # Path-bearing flags get extra validation (no `/etc`, no `../`, no `-l/abs/path`)
        for path_prefix in ("-I", "-L", "-l"):
            if flag.startswith(path_prefix) and len(flag) > len(path_prefix):
                _validate_gcc_path_flag(flag, path_prefix)
        # Allow known-safe prefixes
        if any(flag.startswith(p) for p in _ALLOWED_GCC_FLAG_PREFIXES):
            validated.append(flag)
        else:
            raise ValidationError(
                f"Unknown GCC flag: {flag}",
                code="VALIDATION_ERROR",
                details={"flag": flag},
            )
    return validated


# ── Generic string limits ────────────────────────────────

def validate_string_length(
    value: str,
    max_length: int,
    field_name: str = "input",
) -> str:
    """Enforce maximum string length."""
    if len(value) > max_length:
        raise ValidationError(
            f"{field_name} too long ({len(value)} > {max_length})",
            code="VALIDATION_ERROR",
            details={"field": field_name, "length": len(value), "max": max_length},
        )
    return value
