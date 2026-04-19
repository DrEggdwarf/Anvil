"""Rizin RE REST API routes — comprehensive reverse engineering endpoints.

All routes require an active rizin session. Session_id maps to a
SessionManager session which owns a RizinBridge instance.
"""

from __future__ import annotations

from backend.app.api.deps import get_session_manager
from backend.app.bridges.rizin_bridge import RizinBridge
from backend.app.core.exceptions import ValidationError
from backend.app.models.rizin import (
    RizinAnalyzeRequest,
    RizinCommentRequest,
    RizinCommentsResponse,
    RizinDecompileRequest,
    RizinDisassembleBytesRequest,
    RizinDisassembleRequest,
    RizinEsilSetRegRequest,
    RizinExportsResponse,
    RizinFlagRequest,
    RizinFlagsResponse,
    RizinFunctionsResponse,
    RizinHashRequest,
    RizinImportsResponse,
    RizinJsonResponse,
    RizinNopRequest,
    RizinOpenRequest,
    RizinProjectRequest,
    RizinRawCommandRequest,
    RizinRawResponse,
    RizinReadHexRequest,
    RizinRelocationsResponse,
    RizinRenameFunctionRequest,
    RizinSearchHexRequest,
    RizinSearchResponse,
    RizinSearchRopRequest,
    RizinSearchStringRequest,
    RizinSectionsResponse,
    RizinSeekRequest,
    RizinStringsResponse,
    RizinSymbolsResponse,
    RizinWriteAsmRequest,
    RizinWriteHexRequest,
    RizinWriteStringRequest,
    RizinXrefsResponse,
)
from backend.app.sessions.manager import SessionManager
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/re", tags=["re"])


def _get_rizin_bridge(session_id: str, sm: SessionManager) -> RizinBridge:
    """Get the Rizin bridge for a session."""
    session = sm.get(session_id)
    if not isinstance(session.bridge, RizinBridge):
        raise ValidationError(
            f"Session '{session_id}' is not a rizin session",
            code="WRONG_SESSION_TYPE",
        )
    return session.bridge


# ── Analysis ─────────────────────────────────────────────


@router.post("/{session_id}/open", response_model=RizinRawResponse)
async def open_binary(
    session_id: str,
    body: RizinOpenRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Open a new binary in the session."""
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.open_binary(body.binary_path)
    return RizinRawResponse(output=output)


@router.post("/{session_id}/analyze", response_model=RizinRawResponse)
async def analyze(
    session_id: str,
    body: RizinAnalyzeRequest = RizinAnalyzeRequest(),
    sm: SessionManager = Depends(get_session_manager),
):
    """Run analysis (aa/aaa/aaaa)."""
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.analyze(body.level)
    return RizinRawResponse(output=output)


# ── Binary info ──────────────────────────────────────────


@router.get("/{session_id}/info", response_model=RizinJsonResponse)
async def binary_info(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Get binary info."""
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.binary_info()
    return RizinJsonResponse(data=data)


@router.get("/{session_id}/entry-points", response_model=RizinJsonResponse)
async def entry_points(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """List entry points."""
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.entry_points()
    return RizinJsonResponse(data=data)


# ── Functions ────────────────────────────────────────────


@router.get("/{session_id}/functions", response_model=RizinFunctionsResponse)
async def functions(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """List all functions."""
    bridge = _get_rizin_bridge(session_id, sm)
    funcs = await bridge.functions()
    return RizinFunctionsResponse(functions=funcs)


@router.get("/{session_id}/functions/{address}", response_model=RizinJsonResponse)
async def function_info(
    session_id: str,
    address: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Get function details."""
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.function_info(address)
    return RizinJsonResponse(data=data)


@router.get("/{session_id}/xrefs/to/{address}", response_model=RizinXrefsResponse)
async def xrefs_to(
    session_id: str,
    address: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Get cross-references TO an address."""
    bridge = _get_rizin_bridge(session_id, sm)
    xrefs = await bridge.function_xrefs_to(address)
    return RizinXrefsResponse(xrefs=xrefs)


@router.get("/{session_id}/xrefs/from/{address}", response_model=RizinXrefsResponse)
async def xrefs_from(
    session_id: str,
    address: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Get cross-references FROM an address."""
    bridge = _get_rizin_bridge(session_id, sm)
    xrefs = await bridge.function_xrefs_from(address)
    return RizinXrefsResponse(xrefs=xrefs)


@router.post("/{session_id}/functions/rename", response_model=RizinRawResponse)
async def rename_function(
    session_id: str,
    body: RizinRenameFunctionRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Rename a function."""
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.rename_function(body.address, body.new_name)
    return RizinRawResponse(output=output)


# ── Graphs ───────────────────────────────────────────────


@router.get("/{session_id}/callgraph/{address}", response_model=RizinJsonResponse)
async def callgraph(
    session_id: str,
    address: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Get function call graph."""
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.function_callgraph(address)
    return RizinJsonResponse(data=data)


@router.get("/{session_id}/cfg/{address}", response_model=RizinJsonResponse)
async def cfg(
    session_id: str,
    address: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Get control flow graph."""
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.function_cfg(address)
    return RizinJsonResponse(data=data)


@router.get("/{session_id}/graph/ascii/{address}", response_model=RizinRawResponse)
async def ascii_graph(
    session_id: str,
    address: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Get ASCII control flow graph."""
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.ascii_graph(address)
    return RizinRawResponse(output=output)


@router.get("/{session_id}/graph/dot/{address}", response_model=RizinRawResponse)
async def dot_graph(
    session_id: str,
    address: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Get DOT format call graph."""
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.dot_graph(address)
    return RizinRawResponse(output=output)


# ── Disassembly ──────────────────────────────────────────


@router.post("/{session_id}/disassemble", response_model=RizinJsonResponse)
async def disassemble(
    session_id: str,
    body: RizinDisassembleRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Disassemble N instructions at address."""
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.disassemble(body.address, body.count)
    return RizinJsonResponse(data=data)


@router.post("/{session_id}/disassemble/function/{address}", response_model=RizinJsonResponse)
async def disassemble_function(
    session_id: str,
    address: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Disassemble a full function."""
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.disassemble_function(address)
    return RizinJsonResponse(data=data)


@router.post("/{session_id}/disassemble/bytes", response_model=RizinJsonResponse)
async def disassemble_bytes(
    session_id: str,
    body: RizinDisassembleBytesRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Disassemble N bytes at address."""
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.disassemble_bytes(body.address, body.nbytes)
    return RizinJsonResponse(data=data)


@router.post("/{session_id}/disassemble/text", response_model=RizinRawResponse)
async def disassemble_text(
    session_id: str,
    body: RizinDisassembleRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Disassemble as plain text."""
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.disassemble_text(body.address, body.count)
    return RizinRawResponse(output=output)


# ── Decompiler ───────────────────────────────────────────


@router.post("/{session_id}/decompile", response_model=RizinRawResponse)
async def decompile(
    session_id: str,
    body: RizinDecompileRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Decompile function (r2ghidra/pdd)."""
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.decompile(body.address)
    return RizinRawResponse(output=output)


# ── Strings ──────────────────────────────────────────────


@router.get("/{session_id}/strings", response_model=RizinStringsResponse)
async def strings(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """List strings in data sections."""
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.strings()
    return RizinStringsResponse(strings=data)


@router.get("/{session_id}/strings/all", response_model=RizinStringsResponse)
async def strings_all(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """List ALL strings in entire binary."""
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.strings_all()
    return RizinStringsResponse(strings=data)


# ── Imports / Exports / Symbols ──────────────────────────


@router.get("/{session_id}/imports", response_model=RizinImportsResponse)
async def imports(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.imports()
    return RizinImportsResponse(imports=data)


@router.get("/{session_id}/exports", response_model=RizinExportsResponse)
async def exports(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.exports()
    return RizinExportsResponse(exports=data)


@router.get("/{session_id}/symbols", response_model=RizinSymbolsResponse)
async def symbols(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.symbols()
    return RizinSymbolsResponse(symbols=data)


# ── Sections / segments / relocations ────────────────────


@router.get("/{session_id}/sections", response_model=RizinSectionsResponse)
async def sections(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.sections()
    return RizinSectionsResponse(sections=data)


@router.get("/{session_id}/segments", response_model=RizinJsonResponse)
async def segments(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.segments()
    return RizinJsonResponse(data=data)


@router.get("/{session_id}/relocations", response_model=RizinRelocationsResponse)
async def relocations(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.relocations()
    return RizinRelocationsResponse(relocations=data)


@router.get("/{session_id}/classes", response_model=RizinJsonResponse)
async def classes(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.classes()
    return RizinJsonResponse(data=data)


@router.get("/{session_id}/headers", response_model=RizinJsonResponse)
async def headers(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.headers()
    return RizinJsonResponse(data=data)


@router.get("/{session_id}/libraries", response_model=RizinJsonResponse)
async def libraries(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.libraries()
    return RizinJsonResponse(data=data)


# ── Memory / hex ─────────────────────────────────────────


@router.post("/{session_id}/hex/read", response_model=RizinJsonResponse)
async def read_hex(
    session_id: str,
    body: RizinReadHexRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.read_hex(body.address, body.length)
    return RizinJsonResponse(data=data)


@router.post("/{session_id}/hex/read/text", response_model=RizinRawResponse)
async def read_hex_text(
    session_id: str,
    body: RizinReadHexRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.read_hex_text(body.address, body.length)
    return RizinRawResponse(output=output)


# ── Write / patch ────────────────────────────────────────


@router.post("/{session_id}/write/hex", response_model=RizinRawResponse)
async def write_hex(
    session_id: str,
    body: RizinWriteHexRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.write_hex(body.address, body.hex_data)
    return RizinRawResponse(output=output)


@router.post("/{session_id}/write/string", response_model=RizinRawResponse)
async def write_string(
    session_id: str,
    body: RizinWriteStringRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.write_string(body.address, body.string)
    return RizinRawResponse(output=output)


@router.post("/{session_id}/write/asm", response_model=RizinRawResponse)
async def write_asm(
    session_id: str,
    body: RizinWriteAsmRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.write_assembly(body.address, body.instruction)
    return RizinRawResponse(output=output)


@router.post("/{session_id}/nop", response_model=RizinRawResponse)
async def nop_fill(
    session_id: str,
    body: RizinNopRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.nop_fill(body.address, body.count)
    return RizinRawResponse(output=output)


# ── Search ───────────────────────────────────────────────


@router.post("/{session_id}/search/hex", response_model=RizinSearchResponse)
async def search_hex(
    session_id: str,
    body: RizinSearchHexRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    results = await bridge.search_hex(body.hex_pattern)
    return RizinSearchResponse(results=results)


@router.post("/{session_id}/search/string", response_model=RizinSearchResponse)
async def search_string(
    session_id: str,
    body: RizinSearchStringRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    results = await bridge.search_string(body.string)
    return RizinSearchResponse(results=results)


@router.post("/{session_id}/search/rop", response_model=RizinSearchResponse)
async def search_rop(
    session_id: str,
    body: RizinSearchRopRequest = RizinSearchRopRequest(),
    sm: SessionManager = Depends(get_session_manager),
):
    """Search ROP gadgets."""
    bridge = _get_rizin_bridge(session_id, sm)
    results = await bridge.search_rop(body.regex)
    return RizinSearchResponse(results=results)


@router.post("/{session_id}/search/crypto", response_model=RizinSearchResponse)
async def search_crypto(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Search for crypto constants."""
    bridge = _get_rizin_bridge(session_id, sm)
    results = await bridge.search_crypto()
    return RizinSearchResponse(results=results)


# ── Flags & comments ─────────────────────────────────────


@router.get("/{session_id}/flags", response_model=RizinFlagsResponse)
async def flags(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.flags()
    return RizinFlagsResponse(flags=data)


@router.post("/{session_id}/flags", response_model=RizinRawResponse)
async def set_flag(
    session_id: str,
    body: RizinFlagRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.set_flag(body.name, body.address, body.size)
    return RizinRawResponse(output=output)


@router.get("/{session_id}/comments", response_model=RizinCommentsResponse)
async def get_comments(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.get_comments()
    return RizinCommentsResponse(comments=data)


@router.post("/{session_id}/comments", response_model=RizinRawResponse)
async def add_comment(
    session_id: str,
    body: RizinCommentRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.add_comment(body.address, body.comment)
    return RizinRawResponse(output=output)


@router.delete("/{session_id}/comments/{address}", response_model=RizinRawResponse)
async def delete_comment(
    session_id: str,
    address: str,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.delete_comment(address)
    return RizinRawResponse(output=output)


# ── Seek ─────────────────────────────────────────────────


@router.post("/{session_id}/seek", response_model=RizinRawResponse)
async def seek(
    session_id: str,
    body: RizinSeekRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.seek(body.address)
    return RizinRawResponse(output=output)


@router.get("/{session_id}/seek", response_model=RizinRawResponse)
async def current_seek(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.current_seek()
    return RizinRawResponse(output=output)


# ── ESIL emulation ───────────────────────────────────────


@router.post("/{session_id}/esil/init", response_model=RizinRawResponse)
async def esil_init(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.esil_init()
    return RizinRawResponse(output=output)


@router.post("/{session_id}/esil/step", response_model=RizinRawResponse)
async def esil_step(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.esil_step()
    return RizinRawResponse(output=output)


@router.post("/{session_id}/esil/step-over", response_model=RizinRawResponse)
async def esil_step_over(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.esil_step_over()
    return RizinRawResponse(output=output)


@router.post("/{session_id}/esil/continue", response_model=RizinRawResponse)
async def esil_continue(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.esil_continue()
    return RizinRawResponse(output=output)


@router.get("/{session_id}/esil/registers", response_model=RizinJsonResponse)
async def esil_registers(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.esil_registers()
    return RizinJsonResponse(data=data)


@router.post("/{session_id}/esil/registers/set", response_model=RizinRawResponse)
async def esil_set_register(
    session_id: str,
    body: RizinEsilSetRegRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.esil_set_register(body.register, body.value)
    return RizinRawResponse(output=output)


# ── Hashing ──────────────────────────────────────────────


@router.post("/{session_id}/hash", response_model=RizinRawResponse)
async def hash_block(
    session_id: str,
    body: RizinHashRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.hash_block(body.address, body.size, body.algo)
    return RizinRawResponse(output=output)


# ── Projects ─────────────────────────────────────────────


@router.post("/{session_id}/project/save", response_model=RizinRawResponse)
async def save_project(
    session_id: str,
    body: RizinProjectRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.save_project(body.name)
    return RizinRawResponse(output=output)


@router.post("/{session_id}/project/load", response_model=RizinRawResponse)
async def load_project(
    session_id: str,
    body: RizinProjectRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.load_project(body.name)
    return RizinRawResponse(output=output)


# ── Types ────────────────────────────────────────────────


@router.get("/{session_id}/types", response_model=RizinJsonResponse)
async def types(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    bridge = _get_rizin_bridge(session_id, sm)
    data = await bridge.types()
    return RizinJsonResponse(data=data)


# ── Raw command ──────────────────────────────────────────


@router.post("/{session_id}/command", response_model=RizinRawResponse)
async def raw_command(
    session_id: str,
    body: RizinRawCommandRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Execute a raw rizin command."""
    bridge = _get_rizin_bridge(session_id, sm)
    output = await bridge.execute(body.command)
    return RizinRawResponse(output=output)
