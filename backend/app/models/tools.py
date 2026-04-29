"""Tool definitions — every external tool Anvil wraps.

This is the single source of truth for which tools exist, how to check them,
which modes use them, and whether they are required or optional.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class ToolCategory(StrEnum):
    COMPILATION = "compilation"
    DEBUG = "debug"
    REVERSE_ENGINEERING = "reverse_engineering"
    BINARY_ANALYSIS = "binary_analysis"
    EXPLOITATION = "exploitation"
    FIRMWARE = "firmware"
    PROTOCOLS = "protocols"
    UTILITY = "utility"


class ToolKind(StrEnum):
    """How the tool is invoked / checked."""

    SYSTEM_BINARY = "system_binary"
    PYTHON_PACKAGE = "python_package"


class ToolInfo(BaseModel):
    """Static definition of a tool Anvil wraps."""

    name: str
    display_name: str
    category: ToolCategory
    kind: ToolKind
    check_command: str  # binary name (which) or Python module name (find_spec)
    required: bool  # if False, mode works degraded without it
    description: str
    modes: list[str]  # which Anvil modes use this tool


class ToolStatus(BaseModel):
    """Runtime availability of a single tool."""

    name: str
    available: bool
    version: str | None = None
    path: str | None = None


# ─────────────────────────────────────────────────────────
# TOOL REGISTRY — every tool Anvil wraps (24 tools)
# ─────────────────────────────────────────────────────────

TOOL_DEFINITIONS: list[ToolInfo] = [
    # ── Compilation ──────────────────────────────────────
    ToolInfo(
        name="nasm",
        display_name="NASM",
        category=ToolCategory.COMPILATION,
        kind=ToolKind.SYSTEM_BINARY,
        check_command="nasm",
        required=True,
        description="Netwide Assembler — x86/x64 assembly",
        modes=["asm"],
    ),
    ToolInfo(
        name="ld",
        display_name="GNU Linker",
        category=ToolCategory.COMPILATION,
        kind=ToolKind.SYSTEM_BINARY,
        check_command="ld",
        required=True,
        description="GNU linker",
        modes=["asm"],
    ),
    ToolInfo(
        name="gcc",
        display_name="GCC",
        category=ToolCategory.COMPILATION,
        kind=ToolKind.SYSTEM_BINARY,
        check_command="gcc",
        required=True,
        description="GNU C Compiler",
        modes=["asm", "pwn"],
    ),
    ToolInfo(
        name="as",
        display_name="GNU Assembler",
        category=ToolCategory.COMPILATION,
        kind=ToolKind.SYSTEM_BINARY,
        check_command="as",
        required=False,
        description="GNU Assembler (alternative to NASM)",
        modes=["asm"],
    ),
    # ── Debug ────────────────────────────────────────────
    ToolInfo(
        name="gdb",
        display_name="GDB",
        category=ToolCategory.DEBUG,
        kind=ToolKind.SYSTEM_BINARY,
        check_command="gdb",
        required=True,
        description="GNU Debugger",
        modes=["asm", "debug", "pwn"],
    ),
    ToolInfo(
        name="gdb-multiarch",
        display_name="GDB Multiarch",
        category=ToolCategory.DEBUG,
        kind=ToolKind.SYSTEM_BINARY,
        check_command="gdb-multiarch",
        required=False,
        description="GDB with multi-architecture support",
        modes=["debug", "firmware"],
    ),
    ToolInfo(
        name="strace",
        display_name="strace",
        category=ToolCategory.DEBUG,
        kind=ToolKind.SYSTEM_BINARY,
        check_command="strace",
        required=False,
        description="System call tracer",
        modes=["debug"],
    ),
    # ── Reverse Engineering ──────────────────────────────
    ToolInfo(
        name="rizin",
        display_name="rizin",
        category=ToolCategory.REVERSE_ENGINEERING,
        kind=ToolKind.SYSTEM_BINARY,
        check_command="rizin",
        required=True,
        description="Reverse engineering framework (fork of radare2)",
        modes=["re"],
    ),
    # ── Binary Analysis ──────────────────────────────────
    ToolInfo(
        name="readelf",
        display_name="readelf",
        category=ToolCategory.BINARY_ANALYSIS,
        kind=ToolKind.SYSTEM_BINARY,
        check_command="readelf",
        required=False,
        description="ELF file analyzer",
        modes=["asm", "re", "pwn"],
    ),
    ToolInfo(
        name="objdump",
        display_name="objdump",
        category=ToolCategory.BINARY_ANALYSIS,
        kind=ToolKind.SYSTEM_BINARY,
        check_command="objdump",
        required=False,
        description="Object file disassembler",
        modes=["asm", "re"],
    ),
    ToolInfo(
        name="file",
        display_name="file",
        category=ToolCategory.BINARY_ANALYSIS,
        kind=ToolKind.SYSTEM_BINARY,
        check_command="file",
        required=False,
        description="File type identifier (magic bytes)",
        modes=["asm", "re", "firmware"],
    ),
    # ── Exploitation ─────────────────────────────────────
    ToolInfo(
        name="patchelf",
        display_name="patchelf",
        category=ToolCategory.EXPLOITATION,
        kind=ToolKind.SYSTEM_BINARY,
        check_command="patchelf",
        required=False,
        description="ELF binary patcher (change interpreter, rpath)",
        modes=["pwn"],
    ),
    ToolInfo(
        name="one_gadget",
        display_name="one_gadget",
        category=ToolCategory.EXPLOITATION,
        kind=ToolKind.SYSTEM_BINARY,
        check_command="one_gadget",
        required=False,
        description="One-shot RCE gadget finder in libc",
        modes=["pwn"],
    ),
    ToolInfo(
        name="ropper",
        display_name="Ropper",
        category=ToolCategory.EXPLOITATION,
        kind=ToolKind.SYSTEM_BINARY,
        check_command="ropper",
        required=False,
        description="ROP/JOP/SOP gadget finder",
        modes=["pwn"],
    ),
    # ── Firmware ─────────────────────────────────────────
    ToolInfo(
        name="qemu-user",
        display_name="QEMU User Mode",
        category=ToolCategory.FIRMWARE,
        kind=ToolKind.SYSTEM_BINARY,
        check_command="qemu-arm",
        required=False,
        description="QEMU user-mode emulation (ARM, MIPS, etc.)",
        modes=["firmware", "debug"],
    ),
    ToolInfo(
        name="qemu-system",
        display_name="QEMU System",
        category=ToolCategory.FIRMWARE,
        kind=ToolKind.SYSTEM_BINARY,
        check_command="qemu-system-arm",
        required=False,
        description="QEMU full system emulation",
        modes=["firmware"],
    ),
    # ── Utility ──────────────────────────────────────────
    ToolInfo(
        name="python3",
        display_name="Python 3",
        category=ToolCategory.UTILITY,
        kind=ToolKind.SYSTEM_BINARY,
        check_command="python3",
        required=True,
        description="Python interpreter (backend + pwn scripts)",
        modes=["pwn"],
    ),
    # ── Python Packages ──────────────────────────────────
    ToolInfo(
        name="pygdbmi",
        display_name="pygdbmi",
        category=ToolCategory.DEBUG,
        kind=ToolKind.PYTHON_PACKAGE,
        check_command="pygdbmi",
        required=True,
        description="GDB/MI interface for Python",
        modes=["asm", "debug", "pwn"],
    ),
    ToolInfo(
        name="rzpipe",
        display_name="rzpipe",
        category=ToolCategory.REVERSE_ENGINEERING,
        kind=ToolKind.PYTHON_PACKAGE,
        check_command="rzpipe",
        required=False,
        description="rizin pipe interface for Python",
        modes=["re"],
    ),
    ToolInfo(
        name="pwntools",
        display_name="pwntools",
        category=ToolCategory.EXPLOITATION,
        kind=ToolKind.PYTHON_PACKAGE,
        check_command="pwn",
        required=False,
        description="CTF exploitation framework",
        modes=["pwn"],
    ),
    ToolInfo(
        name="binwalk",
        display_name="binwalk",
        category=ToolCategory.FIRMWARE,
        kind=ToolKind.PYTHON_PACKAGE,
        check_command="binwalk",
        required=False,
        description="Firmware analysis and extraction",
        modes=["firmware"],
    ),
    ToolInfo(
        name="pymodbus",
        display_name="pymodbus",
        category=ToolCategory.PROTOCOLS,
        kind=ToolKind.PYTHON_PACKAGE,
        check_command="pymodbus",
        required=False,
        description="Modbus TCP/RTU protocol library",
        modes=["protocols"],
    ),
    ToolInfo(
        name="snap7",
        display_name="python-snap7",
        category=ToolCategory.PROTOCOLS,
        kind=ToolKind.PYTHON_PACKAGE,
        check_command="snap7",
        required=False,
        description="S7comm (Siemens) protocol library",
        modes=["protocols"],
    ),
    ToolInfo(
        name="opcua",
        display_name="opcua-asyncio",
        category=ToolCategory.PROTOCOLS,
        kind=ToolKind.PYTHON_PACKAGE,
        check_command="asyncua",
        required=False,
        description="OPC-UA async protocol library",
        modes=["protocols"],
    ),
]
