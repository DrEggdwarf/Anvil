"""GDB Pydantic models — request/response schemas for GDB API."""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── Requests ─────────────────────────────────────────────


class GdbLoadRequest(BaseModel):
    binary_path: str = Field(..., max_length=4096)


class GdbRunRequest(BaseModel):
    args: str = Field(default="", max_length=4096)


class GdbBreakpointRequest(BaseModel):
    location: str = Field(..., max_length=1024)  # address (*0x401000), function (main), or file:line


class GdbMemoryRequest(BaseModel):
    address: str = Field(..., max_length=256)
    size: int = Field(ge=1, le=65536, default=256)


class GdbDisassembleRequest(BaseModel):
    start: str | None = Field(default=None, max_length=256)
    end: str | None = Field(default=None, max_length=256)
    function: str | None = Field(default=None, max_length=1024)


class GdbEvaluateRequest(BaseModel):
    expression: str = Field(..., max_length=4096)


# ── Responses ────────────────────────────────────────────


class GdbRegister(BaseModel):
    name: str
    number: int
    value: str


class GdbRegistersResponse(BaseModel):
    registers: list[GdbRegister]


class GdbStackFrame(BaseModel):
    level: int
    addr: str
    func: str = ""
    file: str = ""
    line: int = 0


class GdbStackResponse(BaseModel):
    frames: list[GdbStackFrame]


class GdbMemoryBlock(BaseModel):
    begin: str
    offset: str
    end: str
    contents: str


class GdbMemoryResponse(BaseModel):
    memory: list[GdbMemoryBlock]


class GdbBreakpointInfo(BaseModel):
    number: int
    type: str = ""
    disp: str = ""
    enabled: str = ""
    addr: str = ""
    func: str = ""
    file: str = ""
    line: int = 0


class GdbBreakpointsResponse(BaseModel):
    breakpoints: list[GdbBreakpointInfo]


class GdbDisassemblyLine(BaseModel):
    address: str
    inst: str
    func_name: str = ""
    offset: int = 0


class GdbDisassemblyResponse(BaseModel):
    instructions: list[GdbDisassemblyLine]


class GdbRawResponse(BaseModel):
    """Raw GDB/MI response — used when structured parsing isn't available."""
    responses: list[dict]


# ── Extended requests ────────────────────────────────────


class GdbWatchpointRequest(BaseModel):
    expression: str = Field(..., max_length=4096)
    access: str = Field(default="write", max_length=16)  # write, read, access


class GdbBreakpointConditionRequest(BaseModel):
    bp_number: int
    condition: str = Field(..., max_length=4096)


class GdbWriteMemoryRequest(BaseModel):
    address: str = Field(..., max_length=256)
    hex_data: str = Field(..., max_length=131072)  # 64KB hex


class GdbSetRegisterRequest(BaseModel):
    register: str = Field(..., max_length=64)
    value: str = Field(..., max_length=256)


class GdbSetVariableRequest(BaseModel):
    variable: str = Field(..., max_length=1024)
    value: str = Field(..., max_length=4096)


class GdbSearchMemoryRequest(BaseModel):
    start: str = Field(..., max_length=256)
    end: str = Field(..., max_length=256)
    pattern: str = Field(..., max_length=4096)


class GdbUntilRequest(BaseModel):
    location: str = Field(..., max_length=1024)


class GdbAttachRequest(BaseModel):
    pid: int


class GdbCatchSyscallRequest(BaseModel):
    syscall: str = Field(default="", max_length=256)


class GdbCatchSignalRequest(BaseModel):
    signal: str = Field(default="", max_length=256)


class GdbSignalHandleRequest(BaseModel):
    signal: str = Field(..., max_length=256)
    stop: bool = False
    print_: bool = True
    pass_: bool = True
