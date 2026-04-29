"""Rizin Pydantic models — request/response schemas for RE API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# ── Requests ─────────────────────────────────────────────


class RizinOpenRequest(BaseModel):
    binary_path: str = Field(..., max_length=4096)


class RizinAnalyzeRequest(BaseModel):
    level: str = Field(default="aaa", max_length=16)  # aa, aaa, aaaa


class RizinDisassembleRequest(BaseModel):
    address: str = Field(..., max_length=256)
    count: int = Field(default=32, ge=1, le=10000)


class RizinDisassembleBytesRequest(BaseModel):
    address: str = Field(..., max_length=256)
    nbytes: int = Field(default=64, ge=1, le=65536)


class RizinDecompileRequest(BaseModel):
    address: str = Field(..., max_length=256)


class RizinSearchHexRequest(BaseModel):
    hex_pattern: str = Field(..., max_length=4096)


class RizinSearchStringRequest(BaseModel):
    string: str = Field(..., max_length=4096)


class RizinSearchRopRequest(BaseModel):
    regex: str = Field(default="", max_length=1024)


class RizinReadHexRequest(BaseModel):
    address: str = Field(..., max_length=256)
    length: int = Field(default=256, ge=1, le=65536)


class RizinWriteHexRequest(BaseModel):
    address: str = Field(..., max_length=256)
    hex_data: str = Field(..., max_length=131072)


class RizinWriteStringRequest(BaseModel):
    address: str = Field(..., max_length=256)
    string: str = Field(..., max_length=4096)


class RizinWriteAsmRequest(BaseModel):
    address: str = Field(..., max_length=256)
    instruction: str = Field(..., max_length=1024)


class RizinNopRequest(BaseModel):
    address: str = Field(..., max_length=256)
    count: int = Field(default=1, ge=1, le=1024)


class RizinSeekRequest(BaseModel):
    address: str = Field(..., max_length=256)


class RizinFlagRequest(BaseModel):
    name: str = Field(..., max_length=256)
    address: str = Field(..., max_length=256)
    size: int = 1


class RizinCommentRequest(BaseModel):
    address: str = Field(..., max_length=256)
    comment: str = Field(..., max_length=4096)


class RizinDeleteCommentRequest(BaseModel):
    address: str = Field(..., max_length=256)


class RizinRenameFunctionRequest(BaseModel):
    address: str = Field(..., max_length=256)
    new_name: str = Field(..., max_length=256)


class RizinHashRequest(BaseModel):
    address: str = Field(..., max_length=256)
    size: int = Field(ge=1, le=1048576)
    algo: str = Field(default="md5", max_length=32)


class RizinEsilSetRegRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    register_name: str = Field(..., max_length=64, alias="register")
    value: str = Field(..., max_length=256)


class RizinProjectRequest(BaseModel):
    name: str = Field(..., max_length=256)


class RizinRawCommandRequest(BaseModel):
    command: str = Field(..., max_length=4096)


# ── Responses ────────────────────────────────────────────


class RizinRawResponse(BaseModel):
    """Raw rizin output — for commands that return unstructured text."""
    output: str = ""


class RizinJsonResponse(BaseModel):
    """JSON output from rizin commands."""
    data: list | dict = []


class RizinFunctionEntry(BaseModel):
    offset: int = 0
    name: str = ""
    size: int = 0
    nargs: int = 0
    nlocals: int = 0
    nbbs: int = 0
    cc: int = 0


class RizinFunctionsResponse(BaseModel):
    functions: list[dict] = []


class RizinStringEntry(BaseModel):
    vaddr: int = 0
    paddr: int = 0
    ordinal: int = 0
    size: int = 0
    length: int = 0
    section: str = ""
    type: str = ""
    string: str = ""


class RizinStringsResponse(BaseModel):
    strings: list[dict] = []


class RizinImportEntry(BaseModel):
    ordinal: int = 0
    bind: str = ""
    type: str = ""
    name: str = ""
    plt: int = 0


class RizinImportsResponse(BaseModel):
    imports: list[dict] = []


class RizinExportsResponse(BaseModel):
    exports: list[dict] = []


class RizinSymbolsResponse(BaseModel):
    symbols: list[dict] = []


class RizinSectionsResponse(BaseModel):
    sections: list[dict] = []


class RizinRelocationsResponse(BaseModel):
    relocations: list[dict] = []


class RizinXrefsResponse(BaseModel):
    xrefs: list[dict] = []


class RizinSearchResponse(BaseModel):
    results: list[dict] = []


class RizinFlagsResponse(BaseModel):
    flags: list[dict] = []


class RizinCommentsResponse(BaseModel):
    comments: list[dict] = []
