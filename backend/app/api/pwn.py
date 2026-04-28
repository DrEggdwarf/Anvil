"""Pwn REST API routes — exploitation toolkit endpoints."""

from __future__ import annotations

import base64
from pathlib import Path

from backend.app.api.deps import get_session_manager
from backend.app.bridges.pwn_bridge import PwnBridge
from backend.app.core.exceptions import InvalidFile, ValidationError
from backend.app.core.subprocess_manager import SubprocessManager
from backend.app.core.workspace import WorkspaceManager
from backend.app.models.pwn import (
    PwnAsmRequest,
    PwnCompileRequest,
    PwnConstantRequest,
    PwnContextRequest,
    PwnContextResponse,
    PwnCorefileRequest,
    PwnCyclicFindRequest,
    PwnCyclicRequest,
    PwnDictResponse,
    PwnDisasmRequest,
    PwnElfBssRequest,
    PwnElfLoadRequest,
    PwnElfResponse,
    PwnElfSearchRequest,
    PwnEncodeShellcodeRequest,
    PwnFlatRequest,
    PwnFmtstrRequest,
    PwnHashRequest,
    PwnHexdumpRequest,
    PwnHexResponse,
    PwnIntResponse,
    PwnListConstantsRequest,
    PwnListResponse,
    PwnMakeElfFromAsmRequest,
    PwnMakeElfRequest,
    PwnPackRequest,
    PwnRet2dlRequest,
    PwnRopCallRequest,
    PwnRopCreateRequest,
    PwnRopGadgetRequest,
    PwnRopMigrateRequest,
    PwnRopRawRequest,
    PwnRopSetRegsRequest,
    PwnRotateRequest,
    PwnShellcraftRequest,
    PwnSropRequest,
    PwnStringResponse,
    PwnUnpackRequest,
    PwnUploadRequest,
    PwnXorKeyRequest,
    PwnXorRequest,
)
from backend.app.sessions.manager import SessionManager
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/pwn", tags=["pwn"])

_workspace = WorkspaceManager()
_subprocess = SubprocessManager()


def _get_pwn_bridge(session_id: str, sm: SessionManager) -> PwnBridge:
    session = sm.get(session_id)
    if not isinstance(session.bridge, PwnBridge):
        raise ValidationError(f"Session '{session_id}' is not a pwn session", code="WRONG_SESSION_TYPE")
    return session.bridge


def _resolve_path(session_id: str, raw_path: str, field_name: str = "path") -> str:
    """Force any user-supplied path under the session workspace.

    Sprint 14 fix #3 (Security A1, Pentester #5/#6): every endpoint that previously
    accepted a free-form `path` now goes through this guard to close LFI/symlink escapes.
    """
    try:
        return _workspace.resolve_under_workspace(session_id, raw_path)
    except InvalidFile as exc:
        raise ValidationError(f"Invalid {field_name}: {exc}", code="PATH_BLOCKED") from exc


# ── File upload ──────────────────────────────────────────

@router.post("/{session_id}/upload")
async def upload_binary(
    session_id: str,
    body: PwnUploadRequest,
    sm: SessionManager = Depends(get_session_manager),
) -> dict:
    """Upload a binary file (base64-encoded) to the session workspace."""
    _get_pwn_bridge(session_id, sm)  # validate session type
    # Reject path separators in filename (model already forbids them, double-check).
    if "/" in body.filename or "\\" in body.filename:
        raise ValidationError("Filename must not contain path separators", code="PATH_TRAVERSAL")
    target = Path(_resolve_path(session_id, body.filename, "filename"))
    try:
        data = base64.b64decode(body.data_b64)
    except Exception as exc:
        raise ValidationError(f"Invalid base64 data: {exc}", code="INVALID_BASE64") from exc
    # Refuse to overwrite an existing symlink (resolve_under_workspace also checks this).
    if target.is_symlink():
        raise ValidationError("Symlinks are not allowed", code="PATH_TRAVERSAL")
    target.write_bytes(data)
    # Only mark as executable if the payload looks like an ELF binary.
    if data.startswith(b"\x7fELF"):
        target.chmod(0o755)
    return {"path": str(target), "size": len(data)}


# ── Compile source → binary ──────────────────────────────

_LANG_MAP: dict[str, str] = {
    "c": "gcc",
    "cpp": "g++",
    "cc": "g++",
    "cxx": "g++",
    "asm": "nasm",
    "s": "gcc",  # GAS syntax via gcc
    "rs": "rustc",
    "go": "go",
}

_ALLOWED_LANGS = set(_LANG_MAP.keys())


@router.post("/{session_id}/compile")
async def compile_source(
    session_id: str,
    body: PwnCompileRequest,
    sm: SessionManager = Depends(get_session_manager),
) -> dict:
    """Compile a source file in the session workspace and return the binary path."""
    _get_pwn_bridge(session_id, sm)  # validate session type
    workspace = _workspace.get_workspace(session_id)

    lang = body.language.lower().strip(".")
    if lang not in _ALLOWED_LANGS:
        raise ValidationError(
            f"Unsupported language '{lang}'. Supported: {', '.join(sorted(_ALLOWED_LANGS))}",
            code="UNSUPPORTED_LANGUAGE",
        )

    src_path = _resolve_path(session_id, body.path, "path")
    src = Path(src_path)
    if not src.exists():
        raise ValidationError(f"Source file not found: {body.path}", code="FILE_NOT_FOUND")

    output = src.with_suffix("")  # strip extension → binary name
    compiler = _LANG_MAP[lang]
    # Force network-offline mode for managed-build languages until a sandbox is wired.
    # ADR-017: Rust/Go must not pull deps at build time (anti-SSRF, anti-RCE via build.rs / go.mod).
    extra_env: dict[str, str] = {}

    if compiler == "gcc":
        cmd = ["gcc"]
        if body.vuln_flags:
            cmd += ["-no-pie", "-fno-stack-protector", "-z", "execstack"]
        cmd += ["-g", "-o", str(output), str(src)]
    elif compiler == "g++":
        cmd = ["g++"]
        if body.vuln_flags:
            cmd += ["-no-pie", "-fno-stack-protector", "-z", "execstack"]
        cmd += ["-g", "-o", str(output), str(src)]
    elif compiler == "nasm":
        obj = src.with_suffix(".o")
        # Two-step: assemble then link
        asm_cmd = ["nasm", "-f", "elf64", "-g", "-F", "dwarf", str(src), "-o", str(obj)]
        _stdout, stderr, rc = await _subprocess.execute(asm_cmd, timeout=30.0, cwd=workspace)
        if rc != 0:
            raise ValidationError(f"NASM error:\n{stderr.strip()}", code="COMPILE_ERROR")
        cmd = ["ld", "-m", "elf_x86_64", str(obj), "-o", str(output)]
    elif compiler == "rustc":
        cmd = ["rustc", "-g", "-o", str(output), str(src)]
    elif compiler == "go":
        cmd = ["go", "build", "-o", str(output), str(src)]
        extra_env = {"GOFLAGS": "-mod=vendor", "GOPROXY": "off"}
    else:
        raise ValidationError(f"Compiler not configured: {compiler}", code="COMPILE_ERROR")

    _stdout, stderr, rc = await _subprocess.execute(
        cmd, timeout=60.0, cwd=workspace, env=extra_env or None
    )
    if rc != 0:
        raise ValidationError(f"Compilation error:\n{stderr.strip()}", code="COMPILE_ERROR")

    if not output.exists():
        raise ValidationError("Compilation succeeded but no binary produced", code="COMPILE_ERROR")

    output.chmod(0o755)
    return {"binary_path": str(output), "size": output.stat().st_size}


# ── Context ──────────────────────────────────────────────

@router.post("/{session_id}/context", response_model=PwnContextResponse)
async def set_context(session_id: str, body: PwnContextRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    return await bridge.set_context(**body.model_dump(exclude_none=True))

@router.get("/{session_id}/context", response_model=PwnContextResponse)
async def get_context(session_id: str, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    return bridge.get_context()


# ── Cyclic ───────────────────────────────────────────────

@router.post("/{session_id}/cyclic", response_model=PwnHexResponse)
async def cyclic(session_id: str, body: PwnCyclicRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    result = await bridge.cyclic(body.length, body.alphabet, body.n)
    return PwnHexResponse(hex=result)

@router.post("/{session_id}/cyclic/find", response_model=PwnIntResponse)
async def cyclic_find(session_id: str, body: PwnCyclicFindRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    result = await bridge.cyclic_find(body.subseq, body.alphabet, body.n)
    return PwnIntResponse(value=result)


# ── Packing ──────────────────────────────────────────────

@router.post("/{session_id}/pack", response_model=PwnHexResponse)
async def pack(session_id: str, body: PwnPackRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    result = await bridge.pack(body.value, body.bits, body.endian, body.signed)
    return PwnHexResponse(hex=result)

@router.post("/{session_id}/unpack", response_model=PwnIntResponse)
async def unpack(session_id: str, body: PwnUnpackRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    result = await bridge.unpack(body.hex_data, body.bits, body.endian, body.signed)
    return PwnIntResponse(value=result)

@router.post("/{session_id}/flat", response_model=PwnHexResponse)
async def flat(session_id: str, body: PwnFlatRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    result = await bridge.flat(body.values, body.word_size)
    return PwnHexResponse(hex=result)


# ── Assembly ─────────────────────────────────────────────

@router.post("/{session_id}/asm", response_model=PwnHexResponse)
async def asm(session_id: str, body: PwnAsmRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    result = await bridge.asm(body.source, body.arch, body.os)
    return PwnHexResponse(hex=result)

@router.post("/{session_id}/disasm", response_model=PwnStringResponse)
async def disasm(session_id: str, body: PwnDisasmRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    result = await bridge.disasm(body.hex_data, body.arch)
    return PwnStringResponse(output=result)

@router.post("/{session_id}/asm/elf", response_model=PwnHexResponse)
async def make_elf(session_id: str, body: PwnMakeElfRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    result = await bridge.make_elf(body.hex_data)
    return PwnHexResponse(hex=result)

@router.post("/{session_id}/asm/elf-from-source", response_model=PwnHexResponse)
async def make_elf_from_asm(session_id: str, body: PwnMakeElfFromAsmRequest,
        sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    result = await bridge.make_elf_from_assembly(body.source)
    return PwnHexResponse(hex=result)


# ── Shellcraft ───────────────────────────────────────────

@router.post("/{session_id}/shellcraft", response_model=PwnStringResponse)
async def shellcraft(session_id: str, body: PwnShellcraftRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    result = await bridge.shellcraft(body.name, body.arch, body.os)
    return PwnStringResponse(output=result)

@router.post("/{session_id}/shellcraft/asm", response_model=PwnHexResponse)
async def shellcraft_asm(session_id: str, body: PwnShellcraftRequest,
        sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    result = await bridge.shellcraft_asm(body.name, body.arch, body.os)
    return PwnHexResponse(hex=result)

@router.get("/{session_id}/shellcraft/list", response_model=PwnListResponse)
async def shellcraft_list(session_id: str, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    result = await bridge.shellcraft_list()
    return PwnListResponse(items=result)


# ── ELF analysis ────────────────────────────────────────

@router.post("/{session_id}/elf/load", response_model=PwnElfResponse)
async def elf_load(session_id: str, body: PwnElfLoadRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    safe_path = _resolve_path(session_id, body.path)
    return await bridge.elf_load(safe_path)

@router.get("/{session_id}/elf/checksec", response_model=PwnDictResponse)
async def elf_checksec(session_id: str, path: str, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    safe_path = _resolve_path(session_id, path)
    return PwnDictResponse(data=await bridge.elf_checksec(safe_path))

@router.get("/{session_id}/elf/symbols", response_model=PwnDictResponse)
async def elf_symbols(session_id: str, path: str, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    safe_path = _resolve_path(session_id, path)
    return PwnDictResponse(data=await bridge.elf_symbols(safe_path))

@router.get("/{session_id}/elf/got", response_model=PwnDictResponse)
async def elf_got(session_id: str, path: str, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    safe_path = _resolve_path(session_id, path)
    return PwnDictResponse(data=await bridge.elf_got(safe_path))

@router.get("/{session_id}/elf/plt", response_model=PwnDictResponse)
async def elf_plt(session_id: str, path: str, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    safe_path = _resolve_path(session_id, path)
    return PwnDictResponse(data=await bridge.elf_plt(safe_path))

@router.get("/{session_id}/elf/functions", response_model=PwnListResponse)
async def elf_functions(session_id: str, path: str, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    safe_path = _resolve_path(session_id, path)
    return PwnListResponse(items=await bridge.elf_functions(safe_path))

@router.get("/{session_id}/elf/sections", response_model=PwnListResponse)
async def elf_sections(session_id: str, path: str, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    safe_path = _resolve_path(session_id, path)
    return PwnListResponse(items=await bridge.elf_sections(safe_path))

@router.post("/{session_id}/elf/search", response_model=PwnListResponse)
async def elf_search(session_id: str, body: PwnElfSearchRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    safe_path = _resolve_path(session_id, body.path)
    return PwnListResponse(items=await bridge.elf_search(safe_path, body.needle, body.is_hex))

@router.post("/{session_id}/elf/bss", response_model=PwnHexResponse)
async def elf_bss(session_id: str, body: PwnElfBssRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    safe_path = _resolve_path(session_id, body.path)
    return PwnHexResponse(hex=await bridge.elf_bss(safe_path, body.offset))


# ── ROP ──────────────────────────────────────────────────

@router.post("/{session_id}/rop/create", response_model=PwnStringResponse)
async def rop_create(session_id: str, body: PwnRopCreateRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    safe_path = _resolve_path(session_id, body.elf_path, "elf_path")
    rop_id = await bridge.rop_create(safe_path)
    return PwnStringResponse(output=rop_id)

@router.post("/{session_id}/rop/gadget", response_model=PwnStringResponse)
async def rop_find_gadget(session_id: str, body: PwnRopGadgetRequest,
        sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    result = await bridge.rop_find_gadget(body.rop_id, body.instructions)
    return PwnStringResponse(output=result or "")

@router.post("/{session_id}/rop/call")
async def rop_call(session_id: str, body: PwnRopCallRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    await bridge.rop_call(body.rop_id, body.function, body.args)
    return {"status": "ok"}

@router.post("/{session_id}/rop/raw")
async def rop_raw(session_id: str, body: PwnRopRawRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    await bridge.rop_raw(body.rop_id, body.value)
    return {"status": "ok"}

@router.get("/{session_id}/rop/{rop_id}/chain", response_model=PwnHexResponse)
async def rop_chain(session_id: str, rop_id: str, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    return PwnHexResponse(hex=await bridge.rop_chain(rop_id))

@router.get("/{session_id}/rop/{rop_id}/dump", response_model=PwnStringResponse)
async def rop_dump(session_id: str, rop_id: str, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    return PwnStringResponse(output=await bridge.rop_dump(rop_id))

@router.post("/{session_id}/rop/migrate")
async def rop_migrate(session_id: str, body: PwnRopMigrateRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    await bridge.rop_migrate(body.rop_id, body.address)
    return {"status": "ok"}

@router.post("/{session_id}/rop/set-registers")
async def rop_set_regs(session_id: str, body: PwnRopSetRegsRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    await bridge.rop_set_registers(body.rop_id, body.registers)
    return {"status": "ok"}


# ── Format string ────────────────────────────────────────

@router.post("/{session_id}/fmtstr", response_model=PwnHexResponse)
async def fmtstr_payload(session_id: str, body: PwnFmtstrRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    result = await bridge.fmtstr_payload(body.offset, body.writes, body.numbwritten, body.write_size)
    return PwnHexResponse(hex=result)


# ── SROP ─────────────────────────────────────────────────

@router.post("/{session_id}/srop", response_model=PwnHexResponse)
async def srop_frame(session_id: str, body: PwnSropRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    result = await bridge.srop_frame(body.registers, body.arch)
    return PwnHexResponse(hex=result)


# ── Ret2dlresolve ────────────────────────────────────────

@router.post("/{session_id}/ret2dlresolve", response_model=PwnDictResponse)
async def ret2dlresolve(session_id: str, body: PwnRet2dlRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    safe_path = _resolve_path(session_id, body.elf_path, "elf_path")
    return PwnDictResponse(data=await bridge.ret2dlresolve(safe_path, body.symbol, body.args))


# ── Encoding / crypto ───────────────────────────────────

@router.post("/{session_id}/xor", response_model=PwnHexResponse)
async def xor(session_id: str, body: PwnXorRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    return PwnHexResponse(hex=await bridge.xor(body.hex_data, body.key))

@router.post("/{session_id}/xor/key", response_model=PwnDictResponse)
async def xor_key(session_id: str, body: PwnXorKeyRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    return PwnDictResponse(data=await bridge.xor_key(body.hex_data, body.avoid))

@router.post("/{session_id}/hexdump", response_model=PwnStringResponse)
async def hexdump(session_id: str, body: PwnHexdumpRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    return PwnStringResponse(output=await bridge.hexdump(body.hex_data, body.width))

@router.post("/{session_id}/hash", response_model=PwnHexResponse)
async def hash_data(session_id: str, body: PwnHashRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    return PwnHexResponse(hex=await bridge.hash_data(body.hex_data, body.algo))

@router.post("/{session_id}/encode", response_model=PwnHexResponse)
async def encode_shellcode(session_id: str, body: PwnEncodeShellcodeRequest,
        sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    return PwnHexResponse(hex=await bridge.encode_shellcode(body.hex_shellcode, body.avoid, body.encoder))


# ── Constants ────────────────────────────────────────────

@router.post("/{session_id}/constant", response_model=PwnIntResponse)
async def get_constant(session_id: str, body: PwnConstantRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    result = await bridge.get_constant(body.name)
    return PwnIntResponse(value=result or 0)

@router.post("/{session_id}/constants", response_model=PwnDictResponse)
async def list_constants(session_id: str, body: PwnListConstantsRequest,
        sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    return PwnDictResponse(data=await bridge.list_constants(body.prefix))


# ── Corefile ─────────────────────────────────────────────

@router.post("/{session_id}/corefile", response_model=PwnDictResponse)
async def corefile_load(session_id: str, body: PwnCorefileRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    safe_path = _resolve_path(session_id, body.path)
    return PwnDictResponse(data=await bridge.corefile_load(safe_path))


# ── Misc ─────────────────────────────────────────────────

@router.post("/{session_id}/rol", response_model=PwnIntResponse)
async def rol(session_id: str, body: PwnRotateRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    return PwnIntResponse(value=await bridge.rol(body.value, body.count, body.bits))

@router.post("/{session_id}/ror", response_model=PwnIntResponse)
async def ror(session_id: str, body: PwnRotateRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_pwn_bridge(session_id, sm)
    return PwnIntResponse(value=await bridge.ror(body.value, body.count, body.bits))
