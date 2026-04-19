"""Compilation bridge — ASM (nasm+ld) and C (gcc) compilation.

Wraps nasm, ld, gcc as subprocesses. Parses errors into structured format.
Manages temporary workspaces per session with auto-cleanup.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from backend.app.core.subprocess_manager import SubprocessManager

logger = logging.getLogger(__name__)

# ── Error parsing ────────────────────────────────────────

# nasm: file.asm:5: error: instruction not supported in 64-bit mode
NASM_ERROR_RE = re.compile(r"^(.+?):(\d+):\s*(error|warning):\s*(.+)$", re.MULTILINE)

# gcc: file.c:10:5: error: expected ';' before '}' token
GCC_ERROR_RE = re.compile(r"^(.+?):(\d+):(\d+):\s*(error|warning|note):\s*(.+)$", re.MULTILINE)

# ld: file.o: in function `_start': file.asm:3: undefined reference to `printf'
LD_ERROR_RE = re.compile(r"^(.+?):\s*(.+)$", re.MULTILINE)


def parse_nasm_errors(stderr: str) -> list[dict]:
    """Parse nasm stderr into structured errors."""
    errors = []
    for match in NASM_ERROR_RE.finditer(stderr):
        errors.append({
            "file": match.group(1),
            "line": int(match.group(2)),
            "severity": match.group(3),
            "message": match.group(4),
        })
    return errors


def parse_gcc_errors(stderr: str) -> list[dict]:
    """Parse gcc stderr into structured errors."""
    errors = []
    for match in GCC_ERROR_RE.finditer(stderr):
        errors.append({
            "file": match.group(1),
            "line": int(match.group(2)),
            "column": int(match.group(3)),
            "severity": match.group(4),
            "message": match.group(5),
        })
    return errors


# ── Security flags ───────────────────────────────────────

# GCC security compilation flags
SECURITY_FLAGS: dict[str, list[str]] = {
    "relro_full": ["-Wl,-z,relro,-z,now"],
    "relro_partial": ["-Wl,-z,relro"],
    "nx": [],  # NX is enabled by default
    "pie": ["-pie", "-fPIE"],
    "canary": ["-fstack-protector-all"],
    "fortify": ["-D_FORTIFY_SOURCE=2", "-O2"],
    "no_pie": ["-no-pie"],
    "no_canary": ["-fno-stack-protector"],
    "no_nx": ["-z", "execstack"],
}


class CompilationBridge:
    """Handles ASM and C compilation via subprocess."""

    def __init__(self, subprocess_manager: SubprocessManager) -> None:
        self._spm = subprocess_manager

    async def compile_asm(
        self,
        source_code: str,
        *,
        workspace: str,
        filename: str = "program.asm",
        fmt: str = "elf64",
        debug: bool = True,
        link: bool = True,
        use_libc: bool = False,
    ) -> dict:
        """Compile ASM source: nasm → .o → ld/gcc → binary.

        Returns: {success, binary_path, object_path, errors, stdout, stderr}
        """
        src_path = Path(workspace) / filename
        obj_path = src_path.with_suffix(".o")
        bin_path = src_path.with_suffix("")

        # Write source
        src_path.write_text(source_code)

        # ── nasm ─────────────────────────────────────────
        nasm_cmd = ["nasm", f"-f{fmt}"]
        if debug:
            nasm_cmd += ["-g", "-F", "dwarf"]
        nasm_cmd += [str(src_path), "-o", str(obj_path)]

        stdout, stderr, rc = await self._spm.execute(nasm_cmd, cwd=workspace)

        if rc != 0:
            return {
                "success": False,
                "stage": "assemble",
                "binary_path": None,
                "object_path": None,
                "errors": parse_nasm_errors(stderr),
                "stdout": stdout,
                "stderr": stderr,
                "returncode": rc,
            }

        if not link:
            return {
                "success": True,
                "stage": "assemble",
                "binary_path": None,
                "object_path": str(obj_path),
                "errors": [],
                "stdout": stdout,
                "stderr": stderr,
                "returncode": 0,
            }

        # ── link ─────────────────────────────────────────
        if use_libc:
            link_cmd = ["gcc", "-no-pie", str(obj_path), "-o", str(bin_path)]
        else:
            link_cmd = ["ld", "-m", "elf_x86_64", str(obj_path), "-o", str(bin_path)]

        l_stdout, l_stderr, l_rc = await self._spm.execute(link_cmd, cwd=workspace)

        if l_rc != 0:
            return {
                "success": False,
                "stage": "link",
                "binary_path": None,
                "object_path": str(obj_path),
                "errors": parse_nasm_errors(l_stderr) or [{"message": l_stderr.strip()}],
                "stdout": l_stdout,
                "stderr": l_stderr,
                "returncode": l_rc,
            }

        return {
            "success": True,
            "stage": "link",
            "binary_path": str(bin_path),
            "object_path": str(obj_path),
            "errors": [],
            "stdout": stdout + l_stdout,
            "stderr": stderr + l_stderr,
            "returncode": 0,
        }

    async def compile_c(
        self,
        source_code: str,
        *,
        workspace: str,
        filename: str = "program.c",
        security_flags: list[str] | None = None,
        extra_flags: list[str] | None = None,
        debug: bool = True,
        output_name: str | None = None,
    ) -> dict:
        """Compile C source with gcc.

        security_flags: list of keys from SECURITY_FLAGS (e.g. ["no_pie", "no_canary"])
        Returns: {success, binary_path, errors, warnings, stdout, stderr}
        """
        src_path = Path(workspace) / filename
        out_name = output_name or src_path.stem
        bin_path = Path(workspace) / out_name

        # Write source
        src_path.write_text(source_code)

        # Build gcc command
        gcc_cmd = ["gcc"]
        if debug:
            gcc_cmd += ["-g", "-ggdb"]

        # Security flags
        for flag_name in (security_flags or []):
            flags = SECURITY_FLAGS.get(flag_name, [])
            gcc_cmd.extend(flags)

        # Extra flags (validated)
        if extra_flags:
            from backend.app.core.sanitization import validate_gcc_flags
            gcc_cmd.extend(validate_gcc_flags(extra_flags))

        gcc_cmd += [str(src_path), "-o", str(bin_path)]

        stdout, stderr, rc = await self._spm.execute(gcc_cmd, cwd=workspace)

        errors = parse_gcc_errors(stderr)
        warnings = [e for e in errors if e["severity"] == "warning"]
        errors_only = [e for e in errors if e["severity"] == "error"]

        return {
            "success": rc == 0,
            "stage": "compile",
            "binary_path": str(bin_path) if rc == 0 else None,
            "errors": errors_only,
            "warnings": warnings,
            "stdout": stdout,
            "stderr": stderr,
            "returncode": rc,
        }
