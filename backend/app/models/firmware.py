"""Pydantic models for the Firmware bridge (binwalk)."""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── Scan ─────────────────────────────────────────────────

class FirmwareScanRequest(BaseModel):
    binary_path: str = Field(..., max_length=4096)


class FirmwareScanFilteredRequest(BaseModel):
    binary_path: str = Field(..., max_length=4096)
    include: list[str] | None = Field(default=None, max_length=100)
    exclude: list[str] | None = Field(default=None, max_length=100)


class FirmwareScanResult(BaseModel):
    offset: int
    description: str
    size: int | None = None
    name: str | None = None
    confidence: int | None = None
    module: str | None = None


class FirmwareScanResponse(BaseModel):
    results: list[FirmwareScanResult]


# ── Extraction ───────────────────────────────────────────

class FirmwareExtractRequest(BaseModel):
    binary_path: str = Field(..., max_length=4096)
    output_dir: str | None = Field(default=None, max_length=4096)


class FirmwareExtractionEntry(BaseModel):
    id: str | None = None
    size: int = 0
    success: bool = False
    extractor: str = ""
    output_dir: str = ""


class FirmwareExtractResponse(BaseModel):
    output_dir: str
    results: list[FirmwareScanResult] | None = None
    extractions: list[FirmwareExtractionEntry] | None = None
    files: list[dict] | None = None


# ── Entropy ──────────────────────────────────────────────

class FirmwareEntropyBlock(BaseModel):
    start: int | None = None
    end: int | None = None
    offset: int | None = None
    entropy: float


class FirmwareEntropyResponse(BaseModel):
    blocks: list[FirmwareEntropyBlock]


class FirmwareEntropyGraphResponse(BaseModel):
    path: str


# ── Strings ──────────────────────────────────────────────

class FirmwareStringsRequest(BaseModel):
    binary_path: str = Field(..., max_length=4096)
    min_length: int = 4


class FirmwareStringEntry(BaseModel):
    offset: int
    string: str


class FirmwareStringsResponse(BaseModel):
    strings: list[FirmwareStringEntry]


# ── Secrets ──────────────────────────────────────────────

class FirmwareSecretEntry(BaseModel):
    offset: int
    type: str
    value: str


class FirmwareSecretsResponse(BaseModel):
    secrets: list[FirmwareSecretEntry]


# ── File info ────────────────────────────────────────────

class FirmwareFileInfoResponse(BaseModel):
    path: str
    type: str | None = None
    size: int | None = None


# ── Raw search ───────────────────────────────────────────

class FirmwareSearchRawRequest(BaseModel):
    binary_path: str = Field(..., max_length=4096)
    hex_pattern: str = Field(..., max_length=2048)


class FirmwareSearchResult(BaseModel):
    offset: int
    pattern: str | None = None


class FirmwareSearchResponse(BaseModel):
    results: list[FirmwareSearchResult]


# ── Opcodes ──────────────────────────────────────────────

class FirmwareOpcodesResponse(BaseModel):
    results: list[FirmwareScanResult]


# ── Files listing ────────────────────────────────────────

class FirmwareFileEntry(BaseModel):
    path: str
    size: int
    type: str


class FirmwareFilesResponse(BaseModel):
    files: list[FirmwareFileEntry]


# ── Signatures ───────────────────────────────────────────

class FirmwareSignaturesResponse(BaseModel):
    signatures: list[str]
