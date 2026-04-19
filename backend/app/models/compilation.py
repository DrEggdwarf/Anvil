"""Compilation Pydantic models — request/response schemas for compile & analyze API."""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── Compilation requests ─────────────────────────────────


class CompileAsmRequest(BaseModel):
    source_code: str = Field(..., max_length=1_000_000)
    filename: str = Field(default="program.asm", max_length=255)
    fmt: str = Field(default="elf64", max_length=32)
    debug: bool = True
    link: bool = True
    use_libc: bool = False


class CompileCRequest(BaseModel):
    source_code: str = Field(..., max_length=1_000_000)
    filename: str = Field(default="program.c", max_length=255)
    security_flags: list[str] = Field(default_factory=list, max_length=50)
    extra_flags: list[str] = Field(default_factory=list, max_length=50)
    debug: bool = True
    output_name: str | None = Field(default=None, max_length=255)


# ── Compilation responses ────────────────────────────────


class CompileError(BaseModel):
    file: str = ""
    line: int = 0
    column: int = 0
    severity: str = "error"
    message: str = ""


class CompileResponse(BaseModel):
    success: bool
    stage: str = ""
    binary_path: str | None = None
    object_path: str | None = None
    errors: list[CompileError] = []
    warnings: list[CompileError] = []
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0


# ── Binary analysis ──────────────────────────────────────


class ChecksecResponse(BaseModel):
    path: str
    relro: str = "none"
    canary: bool = False
    nx: bool = False
    pie: bool = False
    rpath: bool = False
    runpath: bool = False
    symbols: bool = False
    fortify: bool = False


class FileInfoResponse(BaseModel):
    path: str
    type: str = "unknown"
    details: str = ""
    success: bool = True


class SectionInfo(BaseModel):
    name: str
    type: str
    address: str = ""
    offset: str = ""
    size: int = 0
    flags: str = ""


class SectionsResponse(BaseModel):
    sections: list[SectionInfo]


# ── Workspace / file management ──────────────────────────


class WriteSourceRequest(BaseModel):
    filename: str = Field(..., max_length=255)
    content: str = Field(..., max_length=1_000_000)


class FileEntry(BaseModel):
    name: str
    size: int
    is_binary: bool = False


class FileListResponse(BaseModel):
    session_id: str
    files: list[FileEntry]


class FileContentResponse(BaseModel):
    filename: str
    content: str


# ── Extended binary analysis ─────────────────────────────


class SymbolEntry(BaseModel):
    address: str = ""
    type: str = ""
    name: str = ""


class SymbolsResponse(BaseModel):
    symbols: list[SymbolEntry]


class DynSymbolEntry(BaseModel):
    num: int = 0
    value: str = ""
    size: int = 0
    type: str = ""
    bind: str = ""
    visibility: str = ""
    ndx: str = ""
    name: str = ""


class DynSymbolsResponse(BaseModel):
    symbols: list[DynSymbolEntry]


class RelocationEntry(BaseModel):
    offset: str = ""
    info: str = ""
    type: str = ""
    value: str = ""
    name: str = ""


class RelocationsResponse(BaseModel):
    relocations: list[RelocationEntry]


class GotEntry(BaseModel):
    address: str = ""
    type: str = ""
    name: str = ""


class GotResponse(BaseModel):
    entries: list[GotEntry]


class PltEntry(BaseModel):
    address: str = ""
    name: str = ""


class PltResponse(BaseModel):
    entries: list[PltEntry]


class StringEntry(BaseModel):
    offset: str = ""
    string: str = ""


class StringsResponse(BaseModel):
    strings: list[StringEntry]


class DependencyEntry(BaseModel):
    name: str = ""
    path: str = ""
    address: str = ""


class DependenciesResponse(BaseModel):
    dependencies: list[DependencyEntry]


class ProgramHeaderEntry(BaseModel):
    type: str = ""
    offset: str = ""
    vaddr: str = ""
    paddr: str = ""
    filesz: str = ""
    memsz: str = ""
    flags: str = ""
    align: str = ""


class ProgramHeadersResponse(BaseModel):
    headers: list[ProgramHeaderEntry]


class SizeInfoResponse(BaseModel):
    text: int = 0
    data: int = 0
    bss: int = 0
    total: int = 0
    filename: str = ""


class HexdumpResponse(BaseModel):
    data: str = ""


class DisassemblyResponse(BaseModel):
    data: str = ""


class StringsRequest(BaseModel):
    min_length: int = Field(default=4, ge=1, le=100)


class HexdumpRequest(BaseModel):
    offset: int = Field(default=0, ge=0)
    length: int = Field(default=256, ge=1, le=65536)


class DisassembleRequest(BaseModel):
    section: str | None = Field(default=None, max_length=256)
    start_address: str | None = Field(default=None, max_length=256)
    stop_address: str | None = Field(default=None, max_length=256)
    intel_syntax: bool = True
