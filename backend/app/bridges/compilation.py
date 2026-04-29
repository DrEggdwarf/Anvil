"""Compilation bridge — ASM (nasm/gas/fasm+ld) and C (gcc) compilation.

Wraps nasm, as (GAS), fasm, ld, gcc as subprocesses. Parses errors into structured format.
Manages temporary workspaces per session with auto-cleanup.
"""

from __future__ import annotations

import logging
import platform
import re
from pathlib import Path

from backend.app.core.subprocess_manager import SubprocessManager

logger = logging.getLogger(__name__)

# ── Error parsing ────────────────────────────────────────

# nasm: file.asm:5: error: instruction not supported in 64-bit mode
NASM_ERROR_RE = re.compile(r"^(.+?):(\d+):\s*(error|warning):\s*(.+)$", re.MULTILINE)

# gcc/gas: file.s:10:5: error: expected ';' before '}' token
# gas also: file.s:10: Error: no such instruction
GCC_ERROR_RE = re.compile(r"^(.+?):(\d+):(\d+):\s*(error|warning|note):\s*(.+)$", re.MULTILINE)
GAS_ERROR_RE = re.compile(r"^(.+?):(\d+):\s*(Error|Warning):\s*(.+)$", re.MULTILINE)

# fasm: file.asm [5]:
#   error: illegal instruction.
FASM_ERROR_RE = re.compile(r"^(.+?)\s*\[(\d+)\]", re.MULTILINE)
FASM_MSG_RE = re.compile(r"^\s*(error|warning):\s*(.+)$", re.MULTILINE)

# ld: file.o: in function `_start': file.asm:3: undefined reference to `printf'
LD_ERROR_RE = re.compile(r"^(.+?):\s*(.+)$", re.MULTILINE)


def parse_nasm_errors(stderr: str) -> list[dict]:
    """Parse nasm stderr into structured errors."""
    errors = []
    for match in NASM_ERROR_RE.finditer(stderr):
        errors.append(
            {
                "file": match.group(1),
                "line": int(match.group(2)),
                "severity": match.group(3),
                "message": match.group(4),
            }
        )
    return errors


def parse_gas_errors(stderr: str) -> list[dict]:
    """Parse GNU Assembler (as/gcc -c) stderr into structured errors."""
    errors = []
    # Try gcc-style first (file:line:col: severity: message)
    for match in GCC_ERROR_RE.finditer(stderr):
        errors.append(
            {
                "file": match.group(1),
                "line": int(match.group(2)),
                "column": int(match.group(3)),
                "severity": match.group(4).lower(),
                "message": match.group(5),
            }
        )
    if errors:
        return errors
    # Fallback: GAS-style (file:line: Error: message)
    for match in GAS_ERROR_RE.finditer(stderr):
        errors.append(
            {
                "file": match.group(1),
                "line": int(match.group(2)),
                "severity": match.group(3).lower(),
                "message": match.group(4),
            }
        )
    return errors


def parse_fasm_errors(stderr: str) -> list[dict]:
    """Parse FASM stderr into structured errors."""
    errors = []
    # FASM outputs: "file.asm [5]:\n  error: message"
    loc_match = FASM_ERROR_RE.search(stderr)
    msg_match = FASM_MSG_RE.search(stderr)
    if loc_match and msg_match:
        errors.append(
            {
                "file": loc_match.group(1).strip(),
                "line": int(loc_match.group(2)),
                "severity": msg_match.group(1),
                "message": msg_match.group(2),
            }
        )
    elif msg_match:
        errors.append(
            {
                "file": "",
                "line": 0,
                "severity": msg_match.group(1),
                "message": msg_match.group(2),
            }
        )
    return errors


def parse_gcc_errors(stderr: str) -> list[dict]:
    """Parse gcc stderr into structured errors."""
    errors = []
    for match in GCC_ERROR_RE.finditer(stderr):
        errors.append(
            {
                "file": match.group(1),
                "line": int(match.group(2)),
                "column": int(match.group(3)),
                "severity": match.group(4),
                "message": match.group(5),
            }
        )
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
        assembler: str = "nasm",
        fmt: str | None = None,
        debug: bool = True,
        link: bool = True,
        use_libc: bool = False,
    ) -> dict:
        """Compile ASM source: assembler → .o → ld/gcc → binary.

        Supports nasm (Intel syntax), gas (AT&T syntax), and fasm.
        Returns: {success, binary_path, object_path, errors, stdout, stderr}
        """
        if fmt is None:
            fmt = "win64" if platform.system() == "Windows" else "elf64"

        src_path = Path(workspace) / filename
        obj_path = src_path.with_suffix(".o")
        bin_ext = ".exe" if fmt.startswith("win") else ""
        bin_path = src_path.with_suffix(bin_ext) if bin_ext else src_path.with_suffix("")

        # Write source
        src_path.write_text(source_code)

        # ── assemble ─────────────────────────────────────
        if assembler == "gas":
            asm_cmd, error_parser = self._gas_cmd(src_path, obj_path, fmt, debug)
        elif assembler == "fasm":
            asm_cmd, error_parser = self._fasm_cmd(src_path, obj_path, fmt)
        else:
            asm_cmd, error_parser = self._nasm_cmd(src_path, obj_path, fmt, debug)

        stdout, stderr, rc = await self._spm.execute(asm_cmd, cwd=workspace)

        if rc != 0:
            return {
                "success": False,
                "stage": "assemble",
                "binary_path": None,
                "object_path": None,
                "errors": error_parser(stderr),
                "stdout": stdout,
                "stderr": stderr,
                "returncode": rc,
            }

        # FASM can produce a binary directly (no .o), handle that
        if assembler == "fasm" and not obj_path.exists() and bin_path.exists():
            return {
                "success": True,
                "stage": "assemble",
                "binary_path": str(bin_path),
                "object_path": None,
                "errors": [],
                "stdout": stdout,
                "stderr": stderr,
                "returncode": 0,
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
        _ld_emulation = {
            "elf64": "elf_x86_64",
            "elf32": "elf_i386",
            "win64": "i386pep",
            "win32": "i386pe",
        }
        if use_libc:
            link_cmd = ["gcc", "-no-pie", str(obj_path), "-o", str(bin_path)]
        else:
            emu = _ld_emulation.get(fmt, "elf_x86_64")
            link_cmd = ["ld", "-m", emu, str(obj_path), "-o", str(bin_path)]

        l_stdout, l_stderr, l_rc = await self._spm.execute(link_cmd, cwd=workspace)

        if l_rc != 0:
            return {
                "success": False,
                "stage": "link",
                "binary_path": None,
                "object_path": str(obj_path),
                "errors": error_parser(l_stderr) or [{"message": l_stderr.strip()}],
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

    @staticmethod
    def _nasm_cmd(
        src_path: Path,
        obj_path: Path,
        fmt: str,
        debug: bool,
    ) -> tuple[list[str], type(parse_nasm_errors)]:
        """Build nasm command (Intel syntax)."""
        cmd = ["nasm", f"-f{fmt}"]
        if debug:
            cmd += ["-g", "-F", "dwarf"]
        cmd += [str(src_path), "-o", str(obj_path)]
        return cmd, parse_nasm_errors

    @staticmethod
    def _gas_cmd(
        src_path: Path,
        obj_path: Path,
        fmt: str,
        debug: bool,
    ) -> tuple[list[str], type(parse_gas_errors)]:
        """Build GNU Assembler command (AT&T syntax via gcc -c)."""
        # Map format to GAS arch flags
        arch_flag = "--64" if "64" in fmt else "--32"
        cmd = ["as", arch_flag]
        if debug:
            cmd += ["-g", "--gdwarf-5"]
        cmd += [str(src_path), "-o", str(obj_path)]
        return cmd, parse_gas_errors

    @staticmethod
    def _fasm_cmd(
        src_path: Path,
        obj_path: Path,
        fmt: str,
    ) -> tuple[list[str], type(parse_fasm_errors)]:
        """Build FASM command (Intel syntax, FASM dialect)."""
        # FASM compiles to ELF object by default with 'format ELF64' directive
        # Output goes to obj_path
        cmd = ["fasm", str(src_path), str(obj_path)]
        return cmd, parse_fasm_errors

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
        for flag_name in security_flags or []:
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
