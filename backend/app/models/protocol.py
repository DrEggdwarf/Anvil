"""Pydantic models for the Protocol bridge (Modbus via pymodbus)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ── Connection ───────────────────────────────────────────

class ModbusConnectRequest(BaseModel):
    transport: str = Field(default="tcp", max_length=16)
    host: str = Field(default="127.0.0.1", max_length=256)
    port: int = Field(default=502, ge=1, le=65535)
    framer: str | None = Field(default=None, max_length=64)
    timeout: float = Field(default=3.0, ge=0.1, le=60.0)
    retries: int = Field(default=3, ge=0, le=10)
    baudrate: int = 19200
    bytesize: int = 8
    parity: str = Field(default="N", max_length=4)
    stopbits: int = 1


class ModbusConnectResponse(BaseModel):
    connected: bool
    transport: str
    host: str
    port: int


# ── Read operations ──────────────────────────────────────

class ModbusReadRequest(BaseModel):
    address: int = Field(default=0, ge=0)
    count: int = Field(default=1, ge=1, le=2000)
    device_id: int = Field(default=1, ge=0, le=247)


class ModbusReadResponse(BaseModel):
    error: bool
    values: list | None = None
    exception_code: int | None = None
    function_code: int | None = None


class ModbusExceptionStatusResponse(BaseModel):
    error: bool
    status: int | None = None
    exception_code: int | None = None


# ── Write operations ─────────────────────────────────────

class ModbusWriteCoilRequest(BaseModel):
    address: int
    value: bool
    device_id: int = 1


class ModbusWriteRegisterRequest(BaseModel):
    address: int
    value: int
    device_id: int = 1


class ModbusWriteCoilsRequest(BaseModel):
    address: int
    values: list[bool] = Field(..., max_length=2000)
    device_id: int = 1


class ModbusWriteRegistersRequest(BaseModel):
    address: int
    values: list[int] = Field(..., max_length=2000)
    device_id: int = 1


class ModbusMaskWriteRequest(BaseModel):
    address: int = 0
    and_mask: int = 0xFFFF
    or_mask: int = 0x0000
    device_id: int = 1


class ModbusReadWriteRequest(BaseModel):
    read_address: int = 0
    read_count: int = Field(default=1, ge=1, le=2000)
    write_address: int = 0
    write_values: list[int] | None = Field(default=None, max_length=2000)
    device_id: int = 1


class ModbusWriteResponse(BaseModel):
    error: bool
    exception_code: int | None = None
    function_code: int | None = None


# ── File records ─────────────────────────────────────────

class ModbusFileRecordRequest(BaseModel):
    file_number: int
    record_number: int
    record_length: int = 0
    record_data: str | None = Field(default=None, max_length=4096)  # hex string for writes
    device_id: int = 1


class ModbusFileRecordResponse(BaseModel):
    error: bool
    records: list[dict] | None = None
    exception_code: int | None = None


# ── Device identification ────────────────────────────────

class ModbusDeviceInfoRequest(BaseModel):
    read_code: int = 1  # 1=Basic, 2=Regular, 3=Extended, 4=Specific
    object_id: int = 0
    device_id: int = 1


class ModbusDeviceInfoResponse(BaseModel):
    error: bool
    information: dict[str, str] | None = None
    exception_code: int | None = None


class ModbusDeviceIdRequest(BaseModel):
    device_id: int = 1


# ── Diagnostics ──────────────────────────────────────────

class ModbusDiagRequest(BaseModel):
    device_id: int = 1


class ModbusDiagQueryRequest(BaseModel):
    message: str = Field(default="0000", max_length=1024)  # hex
    device_id: int = 1


class ModbusDiagRestartRequest(BaseModel):
    toggle: bool = False
    device_id: int = 1


class ModbusDiagResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    error: bool
    count: int | None = None
    message: str | None = None
    register_val: int | None = Field(None, alias="register")
    status: int | None = None
    exception_code: int | None = None


# ── Event counter/log ────────────────────────────────────

class ModbusEventCounterResponse(BaseModel):
    error: bool
    status: int | None = None
    count: int | None = None
    exception_code: int | None = None


class ModbusEventLogResponse(BaseModel):
    error: bool
    status: int | None = None
    event_count: int | None = None
    message_count: int | None = None
    events: list | None = None
    exception_code: int | None = None


# ── Data type conversion ────────────────────────────────

class ModbusConvertFromRequest(BaseModel):
    registers: list[int] = Field(..., max_length=500)
    data_type: str = Field(default="UINT16", max_length=32)
    word_order: str = Field(default="big", max_length=16)


class ModbusConvertToRequest(BaseModel):
    value: Any
    data_type: str = Field(default="UINT16", max_length=32)
    word_order: str = Field(default="big", max_length=16)


class ModbusConvertResponse(BaseModel):
    result: Any


# ── Scan ─────────────────────────────────────────────────

class ModbusScanDevicesRequest(BaseModel):
    start_id: int = 1
    end_id: int = 247


class ModbusScanRegistersRequest(BaseModel):
    start: int = 0
    end: int = 100
    register_type: str = Field(default="holding", max_length=32)
    device_id: int = 1


class ModbusScanResult(BaseModel):
    device_id: int | None = None
    address: int | None = None
    value: Any = None
    status: str | None = None
    register_0: int | None = None


class ModbusScanResponse(BaseModel):
    results: list[ModbusScanResult]


# ── Server / Simulator ──────────────────────────────────

class ModbusServerStartRequest(BaseModel):
    port: int = Field(default=5020, ge=1, le=65535)
    device_id: int = Field(default=1, ge=0, le=247)
    coils: int = Field(default=100, ge=1, le=10_000)
    discrete_inputs: int = Field(default=100, ge=1, le=10_000)
    holding_registers: int = Field(default=100, ge=1, le=10_000)
    input_registers: int = Field(default=100, ge=1, le=10_000)


class ModbusServerResponse(BaseModel):
    status: str
    port: int
    device_id: int
    registers: dict
