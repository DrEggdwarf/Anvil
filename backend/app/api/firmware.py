"""Firmware REST API routes — firmware analysis endpoints."""

from __future__ import annotations

from backend.app.api.deps import get_session_manager
from backend.app.bridges.firmware_bridge import FirmwareBridge
from backend.app.core.exceptions import ValidationError
from backend.app.models.firmware import (
    FirmwareEntropyGraphResponse,
    FirmwareEntropyResponse,
    FirmwareExtractRequest,
    FirmwareExtractResponse,
    FirmwareFileInfoResponse,
    FirmwareFilesResponse,
    FirmwareOpcodesResponse,
    FirmwareScanFilteredRequest,
    FirmwareScanRequest,
    FirmwareScanResponse,
    FirmwareSearchRawRequest,
    FirmwareSearchResponse,
    FirmwareSecretsResponse,
    FirmwareSignaturesResponse,
    FirmwareStringsRequest,
    FirmwareStringsResponse,
)
from backend.app.sessions.manager import SessionManager
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/firmware", tags=["firmware"])


def _get_firmware_bridge(session_id: str, sm: SessionManager) -> FirmwareBridge:
    session = sm.get(session_id)
    if not isinstance(session.bridge, FirmwareBridge):
        raise ValidationError(f"Session '{session_id}' is not a firmware session", code="WRONG_SESSION_TYPE")
    return session.bridge


# ── Scanning ─────────────────────────────────────────────

@router.post("/{session_id}/scan", response_model=FirmwareScanResponse)
async def scan(session_id: str, body: FirmwareScanRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_firmware_bridge(session_id, sm)
    results = await bridge.scan(body.binary_path)
    return FirmwareScanResponse(results=results)

@router.post("/{session_id}/scan/filtered", response_model=FirmwareScanResponse)
async def scan_filtered(session_id: str, body: FirmwareScanFilteredRequest,
        sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_firmware_bridge(session_id, sm)
    results = await bridge.scan_filtered(body.binary_path, body.include, body.exclude)
    return FirmwareScanResponse(results=results)

@router.post("/{session_id}/scan/crypto", response_model=FirmwareScanResponse)
async def scan_crypto(session_id: str, body: FirmwareScanRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_firmware_bridge(session_id, sm)
    results = await bridge.scan_crypto(body.binary_path)
    return FirmwareScanResponse(results=results)

@router.post("/{session_id}/scan/filesystems", response_model=FirmwareScanResponse)
async def scan_filesystems(session_id: str, body: FirmwareScanRequest,
        sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_firmware_bridge(session_id, sm)
    results = await bridge.scan_filesystems(body.binary_path)
    return FirmwareScanResponse(results=results)

@router.post("/{session_id}/scan/compression", response_model=FirmwareScanResponse)
async def scan_compression(session_id: str, body: FirmwareScanRequest,
        sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_firmware_bridge(session_id, sm)
    results = await bridge.scan_compression(body.binary_path)
    return FirmwareScanResponse(results=results)


# ── Extraction ───────────────────────────────────────────

@router.post("/{session_id}/extract", response_model=FirmwareExtractResponse)
async def extract(session_id: str, body: FirmwareExtractRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_firmware_bridge(session_id, sm)
    result = await bridge.extract(body.binary_path, body.output_dir)
    return result

@router.post("/{session_id}/extract/recursive", response_model=FirmwareExtractResponse)
async def extract_recursive(session_id: str, body: FirmwareExtractRequest,
        sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_firmware_bridge(session_id, sm)
    result = await bridge.extract_recursive(body.binary_path, body.output_dir)
    return result

@router.post("/{session_id}/carve", response_model=FirmwareExtractResponse)
async def carve(session_id: str, body: FirmwareExtractRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_firmware_bridge(session_id, sm)
    result = await bridge.carve(body.binary_path, body.output_dir)
    return result


# ── Entropy ──────────────────────────────────────────────

@router.post("/{session_id}/entropy", response_model=FirmwareEntropyResponse)
async def entropy(session_id: str, body: FirmwareScanRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_firmware_bridge(session_id, sm)
    blocks = await bridge.entropy(body.binary_path)
    return FirmwareEntropyResponse(blocks=blocks)

@router.post("/{session_id}/entropy/graph", response_model=FirmwareEntropyGraphResponse)
async def entropy_graph(session_id: str, body: FirmwareScanRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_firmware_bridge(session_id, sm)
    path = await bridge.entropy_graph(body.binary_path)
    return FirmwareEntropyGraphResponse(path=path)


# ── Strings ──────────────────────────────────────────────

@router.post("/{session_id}/strings", response_model=FirmwareStringsResponse)
async def strings(session_id: str, body: FirmwareStringsRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_firmware_bridge(session_id, sm)
    result = await bridge.strings(body.binary_path, body.min_length)
    return FirmwareStringsResponse(strings=result)


# ── Opcodes / arch detection ────────────────────────────

@router.post("/{session_id}/opcodes", response_model=FirmwareOpcodesResponse)
async def opcodes(session_id: str, body: FirmwareScanRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_firmware_bridge(session_id, sm)
    results = await bridge.opcodes(body.binary_path)
    return FirmwareOpcodesResponse(results=results)


# ── Raw search ───────────────────────────────────────────

@router.post("/{session_id}/search", response_model=FirmwareSearchResponse)
async def search_raw(session_id: str, body: FirmwareSearchRawRequest,
        sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_firmware_bridge(session_id, sm)
    results = await bridge.search_raw(body.binary_path, body.hex_pattern)
    return FirmwareSearchResponse(results=results)


# ── Secrets ──────────────────────────────────────────────

@router.post("/{session_id}/secrets", response_model=FirmwareSecretsResponse)
async def scan_secrets(session_id: str, body: FirmwareScanRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_firmware_bridge(session_id, sm)
    results = await bridge.scan_secrets(body.binary_path)
    return FirmwareSecretsResponse(secrets=results)


# ── File info ────────────────────────────────────────────

@router.post("/{session_id}/info", response_model=FirmwareFileInfoResponse)
async def file_info(session_id: str, body: FirmwareScanRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_firmware_bridge(session_id, sm)
    return await bridge.file_info(body.binary_path)


# ── Extracted files listing ──────────────────────────────

@router.get("/{session_id}/extracted", response_model=FirmwareFilesResponse)
async def list_extracted(session_id: str, directory: str | None = None,
        sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_firmware_bridge(session_id, sm)
    files = await bridge.list_extracted(directory)
    return FirmwareFilesResponse(files=files)


# ── Signatures ───────────────────────────────────────────

@router.get("/{session_id}/signatures", response_model=FirmwareSignaturesResponse)
async def list_signatures(session_id: str, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_firmware_bridge(session_id, sm)
    sigs = await bridge.list_signatures()
    return FirmwareSignaturesResponse(signatures=sigs)
