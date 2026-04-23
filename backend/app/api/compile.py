"""Compilation & binary analysis REST API routes.

Provides endpoints for:
- ASM compilation (nasm + ld/gcc)
- C compilation (gcc with security flags)
- Binary analysis (checksec, file info, sections)
- Workspace file management (write, read, list, delete)
"""

from __future__ import annotations

from backend.app.api.deps import get_session_manager, get_subprocess_manager
from backend.app.bridges.binary_analyzer import BinaryAnalyzer
from backend.app.bridges.compilation import CompilationBridge
from backend.app.core.subprocess_manager import SubprocessManager
from backend.app.core.workspace import WorkspaceManager
from backend.app.models.compilation import (
    ChecksecResponse,
    CompileAsmRequest,
    CompileCRequest,
    CompileError,
    CompileResponse,
    DependenciesResponse,
    DependencyEntry,
    DisassembleRequest,
    DisassemblyResponse,
    DynSymbolEntry,
    DynSymbolsResponse,
    FileContentResponse,
    FileEntry,
    FileInfoResponse,
    FileListResponse,
    GotEntry,
    GotResponse,
    HexdumpResponse,
    PltEntry,
    PltResponse,
    ProgramHeaderEntry,
    ProgramHeadersResponse,
    RelocationEntry,
    RelocationsResponse,
    SectionInfo,
    SectionsResponse,
    SizeInfoResponse,
    StringEntry,
    StringsResponse,
    SymbolEntry,
    SymbolsResponse,
    WriteSourceRequest,
)
from backend.app.sessions.manager import SessionManager
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/compile", tags=["compile"])

# Singleton workspace manager (created on first use)
_workspace_mgr: WorkspaceManager | None = None


def _get_workspace_mgr() -> WorkspaceManager:
    global _workspace_mgr
    if _workspace_mgr is None:
        _workspace_mgr = WorkspaceManager()
    return _workspace_mgr


def _get_compilation_bridge(spm: SubprocessManager) -> CompilationBridge:
    return CompilationBridge(spm)


def _get_analyzer(spm: SubprocessManager) -> BinaryAnalyzer:
    return BinaryAnalyzer(spm)


# ── File management ──────────────────────────────────────


@router.post("/{session_id}/files", response_model=FileContentResponse)
async def write_source(
    session_id: str,
    body: WriteSourceRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Write a source file to the session workspace."""
    sm.get(session_id)  # Validate session exists
    wmgr = _get_workspace_mgr()
    wmgr.write_source(session_id, body.filename, body.content)
    return FileContentResponse(filename=body.filename, content=body.content)


@router.get("/{session_id}/files", response_model=FileListResponse)
async def list_files(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """List all files in the session workspace."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    files = wmgr.list_files(session_id)
    return FileListResponse(
        session_id=session_id,
        files=[FileEntry(**f) for f in files],
    )


@router.get("/{session_id}/files/{filename}", response_model=FileContentResponse)
async def read_source(
    session_id: str,
    filename: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Read a source file from the session workspace."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    content = wmgr.read_source(session_id, filename)
    return FileContentResponse(filename=filename, content=content)


@router.delete("/{session_id}/files/{filename}")
async def delete_file(
    session_id: str,
    filename: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Delete a file from the session workspace."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    deleted = wmgr.delete_file(session_id, filename)
    return {"deleted": deleted, "filename": filename}


# ── ASM compilation ──────────────────────────────────────


@router.post("/{session_id}/asm", response_model=CompileResponse)
async def compile_asm(
    session_id: str,
    body: CompileAsmRequest,
    sm: SessionManager = Depends(get_session_manager),
    spm: SubprocessManager = Depends(get_subprocess_manager),
):
    """Compile ASM source (nasm + ld/gcc)."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    workspace = wmgr.get_workspace(session_id)
    bridge = _get_compilation_bridge(spm)

    result = await bridge.compile_asm(
        source_code=body.source_code,
        workspace=workspace,
        filename=body.filename,
        assembler=body.assembler,
        fmt=body.fmt,
        debug=body.debug,
        link=body.link,
        use_libc=body.use_libc,
    )
    return _compile_result_to_response(result)


# ── C compilation ────────────────────────────────────────


@router.post("/{session_id}/c", response_model=CompileResponse)
async def compile_c(
    session_id: str,
    body: CompileCRequest,
    sm: SessionManager = Depends(get_session_manager),
    spm: SubprocessManager = Depends(get_subprocess_manager),
):
    """Compile C source (gcc with security flag control)."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    workspace = wmgr.get_workspace(session_id)
    bridge = _get_compilation_bridge(spm)

    result = await bridge.compile_c(
        source_code=body.source_code,
        workspace=workspace,
        filename=body.filename,
        security_flags=body.security_flags,
        extra_flags=body.extra_flags,
        debug=body.debug,
        output_name=body.output_name,
    )
    return _compile_result_to_response(result)


# ── Binary analysis ──────────────────────────────────────


@router.get("/{session_id}/checksec/{filename}", response_model=ChecksecResponse)
async def checksec(
    session_id: str,
    filename: str,
    sm: SessionManager = Depends(get_session_manager),
    spm: SubprocessManager = Depends(get_subprocess_manager),
):
    """Run checksec on a compiled binary."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    path = wmgr.get_file_path(session_id, filename)
    analyzer = _get_analyzer(spm)
    result = await analyzer.checksec(path)
    return ChecksecResponse(**result)


@router.get("/{session_id}/fileinfo/{filename}", response_model=FileInfoResponse)
async def file_info(
    session_id: str,
    filename: str,
    sm: SessionManager = Depends(get_session_manager),
    spm: SubprocessManager = Depends(get_subprocess_manager),
):
    """Get file type info for a binary."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    path = wmgr.get_file_path(session_id, filename)
    analyzer = _get_analyzer(spm)
    result = await analyzer.file_info(path)
    return FileInfoResponse(**result)


@router.get("/{session_id}/sections/{filename}", response_model=SectionsResponse)
async def sections(
    session_id: str,
    filename: str,
    sm: SessionManager = Depends(get_session_manager),
    spm: SubprocessManager = Depends(get_subprocess_manager),
):
    """List ELF sections of a binary."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    path = wmgr.get_file_path(session_id, filename)
    analyzer = _get_analyzer(spm)
    result = await analyzer.sections(path)
    return SectionsResponse(sections=[SectionInfo(**s) for s in result])


# ── Extended binary analysis ─────────────────────────────


@router.get("/{session_id}/header/{filename}")
async def elf_header(
    session_id: str,
    filename: str,
    sm: SessionManager = Depends(get_session_manager),
    spm: SubprocessManager = Depends(get_subprocess_manager),
):
    """Get ELF header details."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    path = wmgr.get_file_path(session_id, filename)
    analyzer = _get_analyzer(spm)
    return await analyzer.elf_header(path)


@router.get("/{session_id}/program-headers/{filename}", response_model=ProgramHeadersResponse)
async def program_headers(
    session_id: str,
    filename: str,
    sm: SessionManager = Depends(get_session_manager),
    spm: SubprocessManager = Depends(get_subprocess_manager),
):
    """List ELF program headers (segments)."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    path = wmgr.get_file_path(session_id, filename)
    analyzer = _get_analyzer(spm)
    result = await analyzer.program_headers(path)
    return ProgramHeadersResponse(headers=[ProgramHeaderEntry(**h) for h in result])


@router.get("/{session_id}/symbols/{filename}", response_model=SymbolsResponse)
async def symbols(
    session_id: str,
    filename: str,
    sm: SessionManager = Depends(get_session_manager),
    spm: SubprocessManager = Depends(get_subprocess_manager),
):
    """List symbols (nm)."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    path = wmgr.get_file_path(session_id, filename)
    analyzer = _get_analyzer(spm)
    result = await analyzer.symbols(path)
    return SymbolsResponse(symbols=[SymbolEntry(**s) for s in result])


@router.get("/{session_id}/dynamic-symbols/{filename}", response_model=DynSymbolsResponse)
async def dynamic_symbols(
    session_id: str,
    filename: str,
    sm: SessionManager = Depends(get_session_manager),
    spm: SubprocessManager = Depends(get_subprocess_manager),
):
    """List dynamic symbols."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    path = wmgr.get_file_path(session_id, filename)
    analyzer = _get_analyzer(spm)
    result = await analyzer.dynamic_symbols(path)
    return DynSymbolsResponse(symbols=[DynSymbolEntry(**s) for s in result])


@router.get("/{session_id}/imports/{filename}", response_model=DynSymbolsResponse)
async def imports(
    session_id: str,
    filename: str,
    sm: SessionManager = Depends(get_session_manager),
    spm: SubprocessManager = Depends(get_subprocess_manager),
):
    """List imported functions."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    path = wmgr.get_file_path(session_id, filename)
    analyzer = _get_analyzer(spm)
    result = await analyzer.imports(path)
    return DynSymbolsResponse(symbols=[DynSymbolEntry(**s) for s in result])


@router.get("/{session_id}/exports/{filename}", response_model=DynSymbolsResponse)
async def exports(
    session_id: str,
    filename: str,
    sm: SessionManager = Depends(get_session_manager),
    spm: SubprocessManager = Depends(get_subprocess_manager),
):
    """List exported functions."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    path = wmgr.get_file_path(session_id, filename)
    analyzer = _get_analyzer(spm)
    result = await analyzer.exports(path)
    return DynSymbolsResponse(symbols=[DynSymbolEntry(**s) for s in result])


@router.get("/{session_id}/relocations/{filename}", response_model=RelocationsResponse)
async def relocations(
    session_id: str,
    filename: str,
    sm: SessionManager = Depends(get_session_manager),
    spm: SubprocessManager = Depends(get_subprocess_manager),
):
    """List relocations."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    path = wmgr.get_file_path(session_id, filename)
    analyzer = _get_analyzer(spm)
    result = await analyzer.relocations(path)
    return RelocationsResponse(relocations=[RelocationEntry(**r) for r in result])


@router.get("/{session_id}/got/{filename}", response_model=GotResponse)
async def got_entries(
    session_id: str,
    filename: str,
    sm: SessionManager = Depends(get_session_manager),
    spm: SubprocessManager = Depends(get_subprocess_manager),
):
    """List GOT entries."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    path = wmgr.get_file_path(session_id, filename)
    analyzer = _get_analyzer(spm)
    result = await analyzer.got_entries(path)
    return GotResponse(entries=[GotEntry(**e) for e in result])


@router.get("/{session_id}/plt/{filename}", response_model=PltResponse)
async def plt_entries(
    session_id: str,
    filename: str,
    sm: SessionManager = Depends(get_session_manager),
    spm: SubprocessManager = Depends(get_subprocess_manager),
):
    """List PLT entries."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    path = wmgr.get_file_path(session_id, filename)
    analyzer = _get_analyzer(spm)
    result = await analyzer.plt_entries(path)
    return PltResponse(entries=[PltEntry(**e) for e in result])


@router.get("/{session_id}/strings/{filename}", response_model=StringsResponse)
async def strings(
    session_id: str,
    filename: str,
    min_length: int = 4,
    sm: SessionManager = Depends(get_session_manager),
    spm: SubprocessManager = Depends(get_subprocess_manager),
):
    """Extract printable strings."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    path = wmgr.get_file_path(session_id, filename)
    analyzer = _get_analyzer(spm)
    result = await analyzer.strings(path, min_length=min_length)
    return StringsResponse(strings=[StringEntry(**s) for s in result])


@router.get("/{session_id}/dependencies/{filename}", response_model=DependenciesResponse)
async def dependencies(
    session_id: str,
    filename: str,
    sm: SessionManager = Depends(get_session_manager),
    spm: SubprocessManager = Depends(get_subprocess_manager),
):
    """List shared library dependencies (ldd)."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    path = wmgr.get_file_path(session_id, filename)
    analyzer = _get_analyzer(spm)
    result = await analyzer.dependencies(path)
    return DependenciesResponse(dependencies=[DependencyEntry(**d) for d in result])


@router.post("/{session_id}/disassemble/{filename}", response_model=DisassemblyResponse)
async def disassemble(
    session_id: str,
    filename: str,
    body: DisassembleRequest = DisassembleRequest(),
    sm: SessionManager = Depends(get_session_manager),
    spm: SubprocessManager = Depends(get_subprocess_manager),
):
    """Disassemble binary (objdump)."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    path = wmgr.get_file_path(session_id, filename)
    analyzer = _get_analyzer(spm)
    result = await analyzer.disassemble(
        path,
        section=body.section,
        start_address=body.start_address,
        stop_address=body.stop_address,
        intel_syntax=body.intel_syntax,
    )
    return DisassemblyResponse(data=result)


@router.get("/{session_id}/hexdump/{filename}", response_model=HexdumpResponse)
async def hexdump(
    session_id: str,
    filename: str,
    offset: int = 0,
    length: int = 256,
    sm: SessionManager = Depends(get_session_manager),
    spm: SubprocessManager = Depends(get_subprocess_manager),
):
    """Hex dump a region of the binary."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    path = wmgr.get_file_path(session_id, filename)
    analyzer = _get_analyzer(spm)
    result = await analyzer.hexdump(path, offset=offset, length=length)
    return HexdumpResponse(data=result)


@router.get("/{session_id}/size/{filename}", response_model=SizeInfoResponse)
async def size_info(
    session_id: str,
    filename: str,
    sm: SessionManager = Depends(get_session_manager),
    spm: SubprocessManager = Depends(get_subprocess_manager),
):
    """Get section sizes."""
    sm.get(session_id)
    wmgr = _get_workspace_mgr()
    path = wmgr.get_file_path(session_id, filename)
    analyzer = _get_analyzer(spm)
    result = await analyzer.size_info(path)
    return SizeInfoResponse(**result) if result else SizeInfoResponse()


# ── Helpers ──────────────────────────────────────────────


def _compile_result_to_response(result: dict) -> CompileResponse:
    """Convert bridge result dict to CompileResponse model."""
    errors = [CompileError(**e) for e in result.get("errors", [])]
    warnings = [CompileError(**w) for w in result.get("warnings", [])]
    return CompileResponse(
        success=result["success"],
        stage=result.get("stage", ""),
        binary_path=result.get("binary_path"),
        object_path=result.get("object_path"),
        errors=errors,
        warnings=warnings,
        stdout=result.get("stdout", ""),
        stderr=result.get("stderr", ""),
        returncode=result.get("returncode", 0),
    )
