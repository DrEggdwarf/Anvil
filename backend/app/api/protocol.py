"""Protocol REST API routes — ICS/OT Modbus endpoints."""

from __future__ import annotations

from backend.app.api.deps import get_session_manager
from backend.app.bridges.protocol_bridge import ProtocolBridge
from backend.app.core.exceptions import ValidationError
from backend.app.models.protocol import (
    ModbusConnectRequest,
    ModbusConnectResponse,
    ModbusConvertFromRequest,
    ModbusConvertResponse,
    ModbusConvertToRequest,
    ModbusDeviceIdRequest,
    ModbusDeviceInfoRequest,
    ModbusDeviceInfoResponse,
    ModbusDiagQueryRequest,
    ModbusDiagRequest,
    ModbusDiagResponse,
    ModbusDiagRestartRequest,
    ModbusEventCounterResponse,
    ModbusEventLogResponse,
    ModbusExceptionStatusResponse,
    ModbusFileRecordRequest,
    ModbusFileRecordResponse,
    ModbusMaskWriteRequest,
    ModbusReadRequest,
    ModbusReadResponse,
    ModbusReadWriteRequest,
    ModbusScanDevicesRequest,
    ModbusScanRegistersRequest,
    ModbusScanResponse,
    ModbusServerResponse,
    ModbusServerStartRequest,
    ModbusWriteCoilRequest,
    ModbusWriteCoilsRequest,
    ModbusWriteRegisterRequest,
    ModbusWriteRegistersRequest,
    ModbusWriteResponse,
)
from backend.app.sessions.manager import SessionManager
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/protocol", tags=["protocol"])


def _get_protocol_bridge(session_id: str, sm: SessionManager) -> ProtocolBridge:
    session = sm.get(session_id)
    if not isinstance(session.bridge, ProtocolBridge):
        raise ValidationError(f"Session '{session_id}' is not a protocol session", code="WRONG_SESSION_TYPE")
    return session.bridge


# ── Connection ───────────────────────────────────────────


@router.post("/{session_id}/connect", response_model=ModbusConnectResponse)
async def connect(session_id: str, body: ModbusConnectRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.connect(**body.model_dump())


@router.post("/{session_id}/disconnect")
async def disconnect(session_id: str, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_protocol_bridge(session_id, sm)
    await bridge.disconnect()
    return {"status": "disconnected"}


# ── Read operations ──────────────────────────────────────


@router.post("/{session_id}/read/coils", response_model=ModbusReadResponse)
async def read_coils(session_id: str, body: ModbusReadRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.read_coils(body.address, body.count, body.device_id)


@router.post("/{session_id}/read/discrete-inputs", response_model=ModbusReadResponse)
async def read_discrete_inputs(
    session_id: str, body: ModbusReadRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.read_discrete_inputs(body.address, body.count, body.device_id)


@router.post("/{session_id}/read/holding-registers", response_model=ModbusReadResponse)
async def read_holding_registers(
    session_id: str, body: ModbusReadRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.read_holding_registers(body.address, body.count, body.device_id)


@router.post("/{session_id}/read/input-registers", response_model=ModbusReadResponse)
async def read_input_registers(
    session_id: str, body: ModbusReadRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.read_input_registers(body.address, body.count, body.device_id)


@router.post("/{session_id}/read/exception-status", response_model=ModbusExceptionStatusResponse)
async def read_exception_status(
    session_id: str, body: ModbusDiagRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.read_exception_status(body.device_id)


@router.post("/{session_id}/read/fifo-queue", response_model=ModbusReadResponse)
async def read_fifo_queue(session_id: str, body: ModbusReadRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.read_fifo_queue(body.address, body.device_id)


@router.post("/{session_id}/read/file-record", response_model=ModbusFileRecordResponse)
async def read_file_record(
    session_id: str, body: ModbusFileRecordRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.read_file_record(body.file_number, body.record_number, body.record_length, body.device_id)


# ── Write operations ─────────────────────────────────────


@router.post("/{session_id}/write/coil", response_model=ModbusWriteResponse)
async def write_coil(session_id: str, body: ModbusWriteCoilRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.write_coil(body.address, body.value, body.device_id)


@router.post("/{session_id}/write/register", response_model=ModbusWriteResponse)
async def write_register(
    session_id: str, body: ModbusWriteRegisterRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.write_register(body.address, body.value, body.device_id)


@router.post("/{session_id}/write/coils", response_model=ModbusWriteResponse)
async def write_coils(
    session_id: str, body: ModbusWriteCoilsRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.write_coils(body.address, body.values, body.device_id)


@router.post("/{session_id}/write/registers", response_model=ModbusWriteResponse)
async def write_registers(
    session_id: str, body: ModbusWriteRegistersRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.write_registers(body.address, body.values, body.device_id)


@router.post("/{session_id}/write/mask", response_model=ModbusWriteResponse)
async def mask_write(session_id: str, body: ModbusMaskWriteRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.mask_write_register(body.address, body.and_mask, body.or_mask, body.device_id)


@router.post("/{session_id}/readwrite/registers", response_model=ModbusReadResponse)
async def readwrite_registers(
    session_id: str, body: ModbusReadWriteRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.readwrite_registers(
        body.read_address,
        body.read_count,
        body.write_address,
        body.write_values,
        body.device_id,
    )


@router.post("/{session_id}/write/file-record", response_model=ModbusWriteResponse)
async def write_file_record(
    session_id: str, body: ModbusFileRecordRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.write_file_record(body.file_number, body.record_number, body.record_data, body.device_id)


# ── Device identification ────────────────────────────────


@router.post("/{session_id}/device/info", response_model=ModbusDeviceInfoResponse)
async def device_info(
    session_id: str, body: ModbusDeviceInfoRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.read_device_info(body.read_code, body.object_id, body.device_id)


@router.post("/{session_id}/device/report-id")
async def report_server_id(
    session_id: str, body: ModbusDeviceIdRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.report_server_id(body.device_id)


# ── Diagnostics ──────────────────────────────────────────


@router.post("/{session_id}/diag/query", response_model=ModbusDiagResponse)
async def diag_query(session_id: str, body: ModbusDiagQueryRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.diag_query(body.message, body.device_id)


@router.post("/{session_id}/diag/restart", response_model=ModbusWriteResponse)
async def diag_restart(
    session_id: str, body: ModbusDiagRestartRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.diag_restart_comm(body.toggle, body.device_id)


@router.post("/{session_id}/diag/register", response_model=ModbusDiagResponse)
async def diag_read_register(
    session_id: str, body: ModbusDiagRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.diag_read_register(body.device_id)


@router.post("/{session_id}/diag/force-listen-only", response_model=ModbusWriteResponse)
async def diag_force_listen_only(
    session_id: str, body: ModbusDiagRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.diag_force_listen_only(body.device_id)


@router.post("/{session_id}/diag/clear-counters", response_model=ModbusWriteResponse)
async def diag_clear_counters(
    session_id: str, body: ModbusDiagRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.diag_clear_counters(body.device_id)


@router.post("/{session_id}/diag/bus-message-count", response_model=ModbusDiagResponse)
async def diag_bus_message_count(
    session_id: str, body: ModbusDiagRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.diag_bus_message_count(body.device_id)


@router.post("/{session_id}/diag/bus-error-count", response_model=ModbusDiagResponse)
async def diag_bus_error_count(
    session_id: str, body: ModbusDiagRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.diag_bus_error_count(body.device_id)


@router.post("/{session_id}/diag/bus-exception-count", response_model=ModbusDiagResponse)
async def diag_bus_exception_count(
    session_id: str, body: ModbusDiagRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.diag_bus_exception_count(body.device_id)


@router.post("/{session_id}/diag/device-message-count", response_model=ModbusDiagResponse)
async def diag_device_message_count(
    session_id: str, body: ModbusDiagRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.diag_device_message_count(body.device_id)


@router.post("/{session_id}/diag/no-response-count", response_model=ModbusDiagResponse)
async def diag_no_response_count(
    session_id: str, body: ModbusDiagRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.diag_no_response_count(body.device_id)


@router.post("/{session_id}/diag/nak-count", response_model=ModbusDiagResponse)
async def diag_nak_count(session_id: str, body: ModbusDiagRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.diag_nak_count(body.device_id)


@router.post("/{session_id}/diag/busy-count", response_model=ModbusDiagResponse)
async def diag_busy_count(session_id: str, body: ModbusDiagRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.diag_busy_count(body.device_id)


@router.post("/{session_id}/diag/overrun-count", response_model=ModbusDiagResponse)
async def diag_overrun_count(
    session_id: str, body: ModbusDiagRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.diag_overrun_count(body.device_id)


# ── Event counter/log ────────────────────────────────────


@router.post("/{session_id}/events/counter", response_model=ModbusEventCounterResponse)
async def event_counter(session_id: str, body: ModbusDiagRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.get_comm_event_counter(body.device_id)


@router.post("/{session_id}/events/log", response_model=ModbusEventLogResponse)
async def event_log(session_id: str, body: ModbusDiagRequest, sm: SessionManager = Depends(get_session_manager)):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.get_comm_event_log(body.device_id)


# ── Data type conversion ────────────────────────────────


@router.post("/{session_id}/convert/from-registers", response_model=ModbusConvertResponse)
async def convert_from_registers(
    session_id: str, body: ModbusConvertFromRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    result = await bridge.convert_from_registers(body.registers, body.data_type, body.word_order)
    return ModbusConvertResponse(result=result)


@router.post("/{session_id}/convert/to-registers", response_model=ModbusConvertResponse)
async def convert_to_registers(
    session_id: str, body: ModbusConvertToRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    result = await bridge.convert_to_registers(body.value, body.data_type, body.word_order)
    return ModbusConvertResponse(result=result)


# ── Scan / Discovery ────────────────────────────────────


@router.post("/{session_id}/scan/devices", response_model=ModbusScanResponse)
async def scan_devices(
    session_id: str, body: ModbusScanDevicesRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    results = await bridge.scan_devices(body.start_id, body.end_id)
    return ModbusScanResponse(results=results)


@router.post("/{session_id}/scan/registers", response_model=ModbusScanResponse)
async def scan_registers(
    session_id: str, body: ModbusScanRegistersRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    results = await bridge.scan_registers(body.start, body.end, body.register_type, body.device_id)
    return ModbusScanResponse(results=results)


# ── Server / Simulator ──────────────────────────────────


@router.post("/{session_id}/server/start", response_model=ModbusServerResponse)
async def start_server(
    session_id: str, body: ModbusServerStartRequest, sm: SessionManager = Depends(get_session_manager)
):
    bridge = _get_protocol_bridge(session_id, sm)
    return await bridge.start_server(**body.model_dump())
