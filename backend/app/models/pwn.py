"""Pydantic models for the Pwn bridge (pwntools)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# ── Context ──────────────────────────────────────────────


class PwnContextRequest(BaseModel):
    arch: str | None = Field(default=None, max_length=32)
    os: str | None = Field(default=None, max_length=32)
    bits: int | None = None
    endian: str | None = Field(default=None, max_length=16)
    signed: bool | None = None


class PwnContextResponse(BaseModel):
    arch: str
    os: str
    bits: int
    bytes: int
    endian: str
    signed: bool


# ── Cyclic ───────────────────────────────────────────────


class PwnCyclicRequest(BaseModel):
    length: int = Field(default=200, ge=1, le=100_000)
    alphabet: str | None = Field(default=None, max_length=256)
    n: int | None = None


class PwnCyclicFindRequest(BaseModel):
    subseq: str = Field(..., max_length=1024)
    alphabet: str | None = Field(default=None, max_length=256)
    n: int | None = None


# ── Packing ──────────────────────────────────────────────


class PwnPackRequest(BaseModel):
    value: int
    bits: int = 64
    endian: str = Field(default="little", max_length=16)
    signed: bool = False


class PwnUnpackRequest(BaseModel):
    hex_data: str = Field(..., max_length=131_072)
    bits: int = 64
    endian: str = Field(default="little", max_length=16)
    signed: bool = False


class PwnFlatRequest(BaseModel):
    values: list = Field(..., max_length=10_000)
    word_size: int | None = None


# ── Assembly ─────────────────────────────────────────────


class PwnAsmRequest(BaseModel):
    source: str = Field(..., max_length=65_536)
    arch: str | None = Field(default=None, max_length=32)
    os: str | None = Field(default=None, max_length=32)


class PwnDisasmRequest(BaseModel):
    hex_data: str = Field(..., max_length=131_072)
    arch: str | None = Field(default=None, max_length=32)


class PwnMakeElfRequest(BaseModel):
    hex_data: str = Field(..., max_length=1_048_576)


class PwnMakeElfFromAsmRequest(BaseModel):
    source: str = Field(..., max_length=65_536)


# ── Shellcraft ───────────────────────────────────────────


class PwnShellcraftRequest(BaseModel):
    name: str = Field(..., max_length=256)
    arch: str | None = Field(default=None, max_length=32)
    os: str | None = Field(default=None, max_length=32)


# ── ELF ──────────────────────────────────────────────────


class PwnUploadRequest(BaseModel):
    filename: str = Field(..., max_length=255)
    data_b64: str = Field(..., max_length=104_857_600)  # ~75 MB base64 → ~56 MB binary

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if "/" in v or "\\" in v or "\x00" in v:
            msg = "Filename must not contain path separators or null bytes"
            raise ValueError(msg)
        return v


class PwnCompileRequest(BaseModel):
    path: str = Field(..., max_length=4096)
    language: str = Field(..., max_length=16)
    vuln_flags: bool = Field(default=True)


class PwnElfLoadRequest(BaseModel):
    path: str = Field(..., max_length=4096)


class PwnElfSearchRequest(BaseModel):
    path: str = Field(..., max_length=4096)
    needle: str = Field(..., max_length=4096)
    is_hex: bool = False


class PwnElfBssRequest(BaseModel):
    path: str = Field(..., max_length=4096)
    offset: int = 0


class PwnElfResponse(BaseModel):
    path: str
    arch: str
    bits: int
    endian: str
    entry: str
    type: str


class PwnChecksecResponse(BaseModel):
    relro: str
    canary: bool
    nx: bool
    pie: bool
    rpath: bool
    runpath: bool
    fortify: bool
    arch: str
    bits: int


# ── ROP ──────────────────────────────────────────────────


class PwnRopCreateRequest(BaseModel):
    elf_path: str = Field(..., max_length=4096)


class PwnRopGadgetRequest(BaseModel):
    rop_id: str = Field(..., max_length=128)
    instructions: list[str] = Field(..., max_length=100)


class PwnRopCallRequest(BaseModel):
    rop_id: str = Field(..., max_length=128)
    function: str = Field(..., max_length=256)
    args: list | None = Field(default=None, max_length=100)


class PwnRopRawRequest(BaseModel):
    rop_id: str = Field(..., max_length=128)
    value: int


class PwnRopMigrateRequest(BaseModel):
    rop_id: str = Field(..., max_length=128)
    address: int


class PwnRopSetRegsRequest(BaseModel):
    rop_id: str = Field(..., max_length=128)
    registers: dict[str, int] = Field(...)

    @field_validator("registers")
    @classmethod
    def _limit_registers(cls, v: dict) -> dict:
        if len(v) > 64:
            msg = "too many registers (max 64)"
            raise ValueError(msg)
        return v


# ── Format string ────────────────────────────────────────


class PwnFmtstrRequest(BaseModel):
    offset: int
    writes: dict[str, int] = Field(...)  # {hex_addr: value}
    numbwritten: int = 0
    write_size: str = Field(default="byte", max_length=16)

    @field_validator("writes")
    @classmethod
    def _limit_writes(cls, v: dict) -> dict:
        if len(v) > 256:
            msg = "too many writes (max 256)"
            raise ValueError(msg)
        return v


# ── SROP ─────────────────────────────────────────────────


class PwnSropRequest(BaseModel):
    registers: dict[str, int] = Field(...)
    arch: str | None = Field(default=None, max_length=32)

    @field_validator("registers")
    @classmethod
    def _limit_registers(cls, v: dict) -> dict:
        if len(v) > 64:
            msg = "too many registers (max 64)"
            raise ValueError(msg)
        return v


# ── Ret2dlresolve ────────────────────────────────────────


class PwnRet2dlRequest(BaseModel):
    elf_path: str = Field(..., max_length=4096)
    symbol: str = Field(..., max_length=256)
    args: list | None = Field(default=None, max_length=100)


# ── Encoding / crypto ───────────────────────────────────


class PwnXorRequest(BaseModel):
    hex_data: str = Field(..., max_length=131_072)
    key: str = Field(..., max_length=1024)


class PwnXorKeyRequest(BaseModel):
    hex_data: str = Field(..., max_length=131_072)
    avoid: str = Field(default="00", max_length=256)


class PwnHashRequest(BaseModel):
    hex_data: str = Field(..., max_length=131_072)
    algo: str = Field(default="sha256", max_length=32)


class PwnEncodeShellcodeRequest(BaseModel):
    hex_shellcode: str = Field(..., max_length=131_072)
    avoid: str = Field(default="00", max_length=256)
    encoder: str | None = Field(default=None, max_length=64)


class PwnHexdumpRequest(BaseModel):
    hex_data: str = Field(..., max_length=131_072)
    width: int = 16


# ── Constants ────────────────────────────────────────────


class PwnConstantRequest(BaseModel):
    name: str = Field(..., max_length=256)


class PwnListConstantsRequest(BaseModel):
    prefix: str = Field(default="SYS_", max_length=256)


# ── Corefile ─────────────────────────────────────────────


class PwnCorefileRequest(BaseModel):
    path: str = Field(..., max_length=4096)


# ── Misc ─────────────────────────────────────────────────


class PwnRotateRequest(BaseModel):
    value: int
    count: int
    bits: int = 32


# ── Generic responses ────────────────────────────────────


class PwnHexResponse(BaseModel):
    hex: str


class PwnIntResponse(BaseModel):
    value: int


class PwnStringResponse(BaseModel):
    output: str


class PwnDictResponse(BaseModel):
    data: dict


class PwnListResponse(BaseModel):
    items: list
