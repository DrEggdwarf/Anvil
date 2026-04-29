"""Tests for Protocol Bridge — ICS/OT Modbus via pymodbus.

All tests mock pymodbus — no real Modbus devices needed.
Validates: lifecycle, connection, read operations, write operations,
diagnostics, device info, data conversion, scan, server.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from backend.app.bridges.base import BridgeState
from backend.app.bridges.protocol_bridge import ProtocolBridge
from backend.app.core.exceptions import BridgeCrash, BridgeNotReady


# ── Mock helpers ─────────────────────────────────────────


def make_mock_response(error: bool = False, **kwargs):
    """Create a mock Modbus response."""
    resp = MagicMock()
    resp.isError.return_value = error
    if error:
        resp.exception_code = kwargs.get("exception_code", 2)
        resp.function_code = kwargs.get("function_code", 0x81)
    for key, val in kwargs.items():
        setattr(resp, key, val)
    return resp


def make_mock_client():
    """Create a mock Modbus client."""
    client = MagicMock()
    client.connect.return_value = True
    client.close.return_value = None
    # Read operations
    client.read_coils.return_value = make_mock_response(bits=[True, False, True])
    client.read_discrete_inputs.return_value = make_mock_response(bits=[False, True])
    client.read_holding_registers.return_value = make_mock_response(
        registers=[100, 200, 300]
    )
    client.read_input_registers.return_value = make_mock_response(registers=[400, 500])
    client.read_exception_status.return_value = make_mock_response(status=0xFF)
    client.read_fifo_queue.return_value = make_mock_response(registers=[10, 20])
    client.read_file_record.return_value = make_mock_response()
    # Write operations
    client.write_coil.return_value = make_mock_response()
    client.write_register.return_value = make_mock_response()
    client.write_coils.return_value = make_mock_response()
    client.write_registers.return_value = make_mock_response()
    client.mask_write_register.return_value = make_mock_response()
    client.readwrite_registers.return_value = make_mock_response(registers=[42])
    client.write_file_record.return_value = make_mock_response()
    # Device info
    client.read_device_information.return_value = make_mock_response(
        information={0x00: b"TestVendor", 0x01: b"TestProduct"}
    )
    client.report_slave_id.return_value = make_mock_response()
    # Diagnostics
    client.diag_query_data.return_value = make_mock_response(message=b"\x00\x00")
    client.diag_restart_communication.return_value = make_mock_response()
    client.diag_read_diagnostic_register.return_value = make_mock_response(message=0)
    client.diag_force_listen_only.return_value = make_mock_response()
    client.diag_clear_counters.return_value = make_mock_response()
    client.diag_read_bus_message_count.return_value = make_mock_response(message=42)
    client.diag_read_bus_comm_error_count.return_value = make_mock_response(message=0)
    client.diag_read_bus_exception_error_count.return_value = make_mock_response(
        message=1
    )
    client.diag_read_device_message_count.return_value = make_mock_response(message=100)
    client.diag_read_device_no_response_count.return_value = make_mock_response(
        message=0
    )
    client.diag_read_device_nak_count.return_value = make_mock_response(message=0)
    client.diag_read_device_busy_count.return_value = make_mock_response(message=0)
    client.diag_read_bus_char_overrun_count.return_value = make_mock_response(message=0)
    # Event counter/log
    client.diag_get_comm_event_counter.return_value = make_mock_response(
        status=0, count=10
    )
    client.diag_get_comm_event_log.return_value = make_mock_response(
        status=0, event_count=5, message_count=10, events=[]
    )
    return client


@pytest_asyncio.fixture
async def proto():
    """Protocol bridge with mocked pymodbus."""
    bridge = ProtocolBridge()
    mock_pymodbus = MagicMock()
    mock_pymodbus.__version__ = "3.13.0"
    bridge._pymodbus = mock_pymodbus
    bridge.state = BridgeState.READY
    yield bridge
    bridge.state = BridgeState.STOPPED


@pytest_asyncio.fixture
async def connected_proto(proto: ProtocolBridge):
    """Protocol bridge with a connected mock client."""
    proto._client = make_mock_client()
    proto._connected = True
    proto._transport = "tcp"
    yield proto


# ── Lifecycle ────────────────────────────────────────────


class TestProtocolLifecycle:
    @pytest.mark.asyncio
    async def test_start_imports_pymodbus(self):
        bridge = ProtocolBridge()
        mock_pymodbus = MagicMock()
        mock_pymodbus.__version__ = "3.13.0"
        with patch.dict("sys.modules", {"pymodbus": mock_pymodbus}):
            await bridge.start()
        assert bridge.state == BridgeState.READY

    @pytest.mark.asyncio
    async def test_start_failure(self):
        bridge = ProtocolBridge()
        with patch.dict("sys.modules", {"pymodbus": None}):
            with patch("builtins.__import__", side_effect=ImportError("no pymodbus")):
                with pytest.raises(BridgeCrash):
                    await bridge.start()
        assert bridge.state == BridgeState.ERROR

    @pytest.mark.asyncio
    async def test_stop(self, proto: ProtocolBridge):
        await proto.stop()
        assert proto.state == BridgeState.STOPPED
        assert proto._pymodbus is None

    @pytest.mark.asyncio
    async def test_stop_with_connection(self, connected_proto: ProtocolBridge):
        await connected_proto.stop()
        assert connected_proto._connected is False

    @pytest.mark.asyncio
    async def test_health(self, proto: ProtocolBridge):
        assert await proto.health() is True

    @pytest.mark.asyncio
    async def test_health_no_pymodbus(self):
        bridge = ProtocolBridge()
        assert await bridge.health() is False

    @pytest.mark.asyncio
    async def test_execute_dispatches(self, proto: ProtocolBridge):
        result = await proto.execute("health")
        assert result is True

    @pytest.mark.asyncio
    async def test_execute_unknown(self, proto: ProtocolBridge):
        with pytest.raises(ValueError, match="Unknown command"):
            await proto.execute("nonexistent")


# ── Connection ───────────────────────────────────────────


class TestProtocolConnection:
    @pytest.mark.asyncio
    async def test_connect_tcp(self, proto: ProtocolBridge):
        mock_client = MagicMock()
        mock_client.connect.return_value = True
        mock_pymodbus_client = MagicMock()
        mock_pymodbus_client.ModbusTcpClient.return_value = mock_client
        mock_pymodbus_framer = MagicMock()
        mock_pymodbus_framer.FramerType.SOCKET = "socket"
        with patch.dict(
            "sys.modules",
            {
                "pymodbus": MagicMock(),
                "pymodbus.client": mock_pymodbus_client,
                "pymodbus.framer": mock_pymodbus_framer,
            },
        ):
            result = await proto.connect(transport="tcp", host="192.168.1.1", port=502)
        assert result["connected"] is True
        assert result["transport"] == "tcp"

    @pytest.mark.asyncio
    async def test_connect_unknown_transport(self, proto: ProtocolBridge):
        mock_pymodbus_client = MagicMock()
        mock_pymodbus_framer = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "pymodbus": MagicMock(),
                "pymodbus.client": mock_pymodbus_client,
                "pymodbus.framer": mock_pymodbus_framer,
            },
        ):
            with pytest.raises(ValueError, match="Unknown transport"):
                await proto.connect(transport="bluetooth")

    @pytest.mark.asyncio
    async def test_disconnect(self, connected_proto: ProtocolBridge):
        await connected_proto.disconnect()
        assert connected_proto._connected is False
        assert connected_proto._client is None

    @pytest.mark.asyncio
    async def test_disconnect_no_connection(self, proto: ProtocolBridge):
        await proto.disconnect()  # Should not raise


# ── Read operations ──────────────────────────────────────


class TestProtocolRead:
    @pytest.mark.asyncio
    async def test_read_coils(self, connected_proto: ProtocolBridge):
        result = await connected_proto.read_coils(0, count=3)
        assert result["error"] is False
        assert result["values"] == [True, False, True]

    @pytest.mark.asyncio
    async def test_read_discrete_inputs(self, connected_proto: ProtocolBridge):
        result = await connected_proto.read_discrete_inputs(0, count=2)
        assert result["error"] is False
        assert result["values"] == [False, True]

    @pytest.mark.asyncio
    async def test_read_holding_registers(self, connected_proto: ProtocolBridge):
        result = await connected_proto.read_holding_registers(0, count=3)
        assert result["error"] is False
        assert result["values"] == [100, 200, 300]

    @pytest.mark.asyncio
    async def test_read_input_registers(self, connected_proto: ProtocolBridge):
        result = await connected_proto.read_input_registers(0, count=2)
        assert result["error"] is False
        assert result["values"] == [400, 500]

    @pytest.mark.asyncio
    async def test_read_exception_status(self, connected_proto: ProtocolBridge):
        result = await connected_proto.read_exception_status()
        assert result["error"] is False
        assert result["status"] == 0xFF

    @pytest.mark.asyncio
    async def test_read_fifo_queue(self, connected_proto: ProtocolBridge):
        result = await connected_proto.read_fifo_queue(address=0)
        assert result["error"] is False

    @pytest.mark.asyncio
    async def test_read_error_response(self, connected_proto: ProtocolBridge):
        connected_proto._client.read_coils.return_value = make_mock_response(
            error=True, exception_code=2, function_code=0x81
        )
        result = await connected_proto.read_coils(0)
        assert result["error"] is True
        assert result["exception_code"] == 2

    @pytest.mark.asyncio
    async def test_read_requires_connection(self, proto: ProtocolBridge):
        with pytest.raises(BridgeNotReady):
            await proto.read_coils(0)


# ── Write operations ─────────────────────────────────────


class TestProtocolWrite:
    @pytest.mark.asyncio
    async def test_write_coil(self, connected_proto: ProtocolBridge):
        result = await connected_proto.write_coil(0, True)
        assert result["error"] is False
        connected_proto._client.write_coil.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_register(self, connected_proto: ProtocolBridge):
        result = await connected_proto.write_register(0, 1234)
        assert result["error"] is False

    @pytest.mark.asyncio
    async def test_write_coils(self, connected_proto: ProtocolBridge):
        result = await connected_proto.write_coils(0, [True, False, True])
        assert result["error"] is False

    @pytest.mark.asyncio
    async def test_write_registers(self, connected_proto: ProtocolBridge):
        result = await connected_proto.write_registers(0, [100, 200, 300])
        assert result["error"] is False

    @pytest.mark.asyncio
    async def test_mask_write_register(self, connected_proto: ProtocolBridge):
        result = await connected_proto.mask_write_register(0, 0xFF00, 0x00FF)
        assert result["error"] is False

    @pytest.mark.asyncio
    async def test_readwrite_registers(self, connected_proto: ProtocolBridge):
        result = await connected_proto.readwrite_registers(
            read_address=0,
            read_count=1,
            write_address=10,
            write_values=[42],
        )
        assert result["error"] is False
        assert result["values"] == [42]

    @pytest.mark.asyncio
    async def test_write_requires_connection(self, proto: ProtocolBridge):
        with pytest.raises(BridgeNotReady):
            await proto.write_coil(0, True)


# ── Device identification ────────────────────────────────


class TestProtocolDeviceInfo:
    @pytest.mark.asyncio
    async def test_read_device_info(self, connected_proto: ProtocolBridge):
        mock_constants = MagicMock()
        mock_constants.DeviceInformation.BASIC = 1
        mock_constants.DeviceInformation.REGULAR = 2
        mock_constants.DeviceInformation.EXTENDED = 3
        mock_constants.DeviceInformation.SPECIFIC = 4
        with patch.dict(
            "sys.modules",
            {
                "pymodbus": MagicMock(),
                "pymodbus.constants": mock_constants,
            },
        ):
            result = await connected_proto.read_device_info(read_code=1)
        assert result["error"] is False
        assert "information" in result
        assert result["information"]["VendorName"] == "TestVendor"

    @pytest.mark.asyncio
    async def test_report_server_id(self, connected_proto: ProtocolBridge):
        mock_resp = make_mock_response()
        mock_resp.encode.return_value = b"\x01\x02\x03"
        connected_proto._client.report_slave_id.return_value = mock_resp
        result = await connected_proto.report_server_id()
        assert result["error"] is False
        assert result["data"] == "010203"


# ── Diagnostics ──────────────────────────────────────────


class TestProtocolDiagnostics:
    @pytest.mark.asyncio
    async def test_diag_query(self, connected_proto: ProtocolBridge):
        result = await connected_proto.diag_query("0000")
        assert result["error"] is False

    @pytest.mark.asyncio
    async def test_diag_restart(self, connected_proto: ProtocolBridge):
        result = await connected_proto.diag_restart_comm(toggle=True)
        assert result["error"] is False

    @pytest.mark.asyncio
    async def test_diag_read_register(self, connected_proto: ProtocolBridge):
        result = await connected_proto.diag_read_register()
        assert result["error"] is False

    @pytest.mark.asyncio
    async def test_diag_force_listen_only(self, connected_proto: ProtocolBridge):
        result = await connected_proto.diag_force_listen_only()
        assert result["error"] is False

    @pytest.mark.asyncio
    async def test_diag_clear_counters(self, connected_proto: ProtocolBridge):
        result = await connected_proto.diag_clear_counters()
        assert result["error"] is False

    @pytest.mark.asyncio
    async def test_diag_bus_message_count(self, connected_proto: ProtocolBridge):
        result = await connected_proto.diag_bus_message_count()
        assert result["error"] is False
        assert result["count"] == 42

    @pytest.mark.asyncio
    async def test_diag_bus_error_count(self, connected_proto: ProtocolBridge):
        result = await connected_proto.diag_bus_error_count()
        assert result["error"] is False

    @pytest.mark.asyncio
    async def test_diag_bus_exception_count(self, connected_proto: ProtocolBridge):
        result = await connected_proto.diag_bus_exception_count()
        assert result["error"] is False

    @pytest.mark.asyncio
    async def test_diag_device_message_count(self, connected_proto: ProtocolBridge):
        result = await connected_proto.diag_device_message_count()
        assert result["error"] is False

    @pytest.mark.asyncio
    async def test_diag_no_response_count(self, connected_proto: ProtocolBridge):
        result = await connected_proto.diag_no_response_count()
        assert result["error"] is False

    @pytest.mark.asyncio
    async def test_diag_nak_count(self, connected_proto: ProtocolBridge):
        result = await connected_proto.diag_nak_count()
        assert result["error"] is False

    @pytest.mark.asyncio
    async def test_diag_busy_count(self, connected_proto: ProtocolBridge):
        result = await connected_proto.diag_busy_count()
        assert result["error"] is False

    @pytest.mark.asyncio
    async def test_diag_overrun_count(self, connected_proto: ProtocolBridge):
        result = await connected_proto.diag_overrun_count()
        assert result["error"] is False

    @pytest.mark.asyncio
    async def test_diag_requires_connection(self, proto: ProtocolBridge):
        with pytest.raises(BridgeNotReady):
            await proto.diag_query()


# ── Event counter/log ────────────────────────────────────


class TestProtocolEvents:
    @pytest.mark.asyncio
    async def test_get_comm_event_counter(self, connected_proto: ProtocolBridge):
        result = await connected_proto.get_comm_event_counter()
        assert result["error"] is False
        assert result["count"] == 10

    @pytest.mark.asyncio
    async def test_get_comm_event_log(self, connected_proto: ProtocolBridge):
        result = await connected_proto.get_comm_event_log()
        assert result["error"] is False
        assert result["event_count"] == 5


# ── Data type conversion ────────────────────────────────


class TestProtocolConversion:
    @pytest.mark.asyncio
    async def test_convert_from_registers(self, proto: ProtocolBridge):
        mock_mixin = MagicMock()
        mock_mixin.convert_from_registers.return_value = 3.14
        mock_dtype = MagicMock()
        mock_constants = MagicMock()
        mock_constants.DATATYPE.FLOAT32 = mock_dtype
        mock_client_mod = MagicMock()
        mock_client_mod.ModbusClientMixin = mock_mixin
        with patch.dict(
            "sys.modules",
            {
                "pymodbus": MagicMock(),
                "pymodbus.client": mock_client_mod,
                "pymodbus.constants": mock_constants,
            },
        ):
            result = await proto.convert_from_registers([0x4048, 0xF5C3], "FLOAT32")
        assert result == 3.14

    @pytest.mark.asyncio
    async def test_convert_to_registers(self, proto: ProtocolBridge):
        mock_mixin = MagicMock()
        mock_mixin.convert_to_registers.return_value = [0x4048, 0xF5C3]
        mock_dtype = MagicMock()
        mock_constants = MagicMock()
        mock_constants.DATATYPE.FLOAT32 = mock_dtype
        mock_client_mod = MagicMock()
        mock_client_mod.ModbusClientMixin = mock_mixin
        with patch.dict(
            "sys.modules",
            {
                "pymodbus": MagicMock(),
                "pymodbus.client": mock_client_mod,
                "pymodbus.constants": mock_constants,
            },
        ):
            result = await proto.convert_to_registers(3.14, "FLOAT32")
        assert result == [0x4048, 0xF5C3]

    @pytest.mark.asyncio
    async def test_convert_unknown_type(self, proto: ProtocolBridge):
        mock_mixin = MagicMock()
        mock_constants = MagicMock()
        mock_constants.DATATYPE = MagicMock(spec=[])
        mock_client_mod = MagicMock()
        mock_client_mod.ModbusClientMixin = mock_mixin
        with patch.dict(
            "sys.modules",
            {
                "pymodbus": MagicMock(),
                "pymodbus.client": mock_client_mod,
                "pymodbus.constants": mock_constants,
            },
        ):
            with pytest.raises(ValueError, match="Unknown data type"):
                await proto.convert_from_registers([0], "NONEXISTENT")


# ── Scan / Discovery ────────────────────────────────────


class TestProtocolScan:
    @pytest.mark.asyncio
    async def test_scan_devices(self, connected_proto: ProtocolBridge):
        # Only device_id=1 responds normally, others error
        ok_response = make_mock_response(registers=[42])
        err_response = make_mock_response(error=True)
        connected_proto._client.read_holding_registers.side_effect = (
            lambda addr, count, slave: ok_response if slave == 1 else err_response
        )
        results = await connected_proto.scan_devices(start_id=1, end_id=3)
        assert len(results) == 1
        assert results[0]["device_id"] == 1

    @pytest.mark.asyncio
    async def test_scan_devices_exception(self, connected_proto: ProtocolBridge):
        connected_proto._client.read_holding_registers.side_effect = Exception(
            "timeout"
        )
        results = await connected_proto.scan_devices(start_id=1, end_id=3)
        assert results == []

    @pytest.mark.asyncio
    async def test_scan_registers_holding(self, connected_proto: ProtocolBridge):
        mock_resp = make_mock_response(registers=[0, 42, 0, 100])
        connected_proto._client.read_holding_registers.return_value = mock_resp
        results = await connected_proto.scan_registers(
            start=0, end=3, register_type="holding"
        )
        # Non-zero values
        assert any(r["value"] == 42 for r in results)
        assert any(r["value"] == 100 for r in results)

    @pytest.mark.asyncio
    async def test_scan_registers_coils(self, connected_proto: ProtocolBridge):
        mock_resp = make_mock_response(bits=[True, False, True])
        connected_proto._client.read_coils.return_value = mock_resp
        results = await connected_proto.scan_registers(
            start=0, end=2, register_type="coil"
        )
        assert any(r["value"] is True for r in results)

    @pytest.mark.asyncio
    async def test_scan_registers_unknown_type(self, connected_proto: ProtocolBridge):
        with pytest.raises(ValueError, match="Unknown register type"):
            await connected_proto.scan_registers(register_type="nonexistent")


# ── Server / Simulator ──────────────────────────────────


class TestProtocolServer:
    @pytest.mark.asyncio
    async def test_start_server(self, proto: ProtocolBridge):
        mock_datastore = MagicMock()
        mock_server_mod = MagicMock()
        mock_server_mod.StartAsyncTcpServer = AsyncMock()
        with patch.dict(
            "sys.modules",
            {
                "pymodbus": MagicMock(),
                "pymodbus.datastore": mock_datastore,
                "pymodbus.server": mock_server_mod,
            },
        ):
            result = await proto.start_server(port=5020)
        assert result["status"] == "started"
        assert result["port"] == 5020

    @pytest.mark.asyncio
    async def test_stop_server(self, proto: ProtocolBridge):
        mock_task = MagicMock()
        proto._server = mock_task
        await proto._stop_server()
        mock_task.cancel.assert_called_once()
        assert proto._server is None


# ── Properties ───────────────────────────────────────────


class TestProtocolProperties:
    def test_is_connected_false(self, proto: ProtocolBridge):
        assert proto.is_connected is False

    def test_is_connected_true(self, connected_proto: ProtocolBridge):
        assert connected_proto.is_connected is True

    def test_transport(self, connected_proto: ProtocolBridge):
        assert connected_proto.transport == "tcp"

    def test_transport_none(self, proto: ProtocolBridge):
        assert proto.transport is None


# ── Not ready guard ──────────────────────────────────────


class TestProtocolGuards:
    @pytest.mark.asyncio
    async def test_read_fails_without_connection(self, proto: ProtocolBridge):
        with pytest.raises(BridgeNotReady):
            await proto.read_coils(0)
        with pytest.raises(BridgeNotReady):
            await proto.read_holding_registers(0)
        with pytest.raises(BridgeNotReady):
            await proto.write_coil(0, True)
        with pytest.raises(BridgeNotReady):
            await proto.diag_query()

    @pytest.mark.asyncio
    async def test_methods_fail_when_bridge_not_ready(self):
        bridge = ProtocolBridge()
        with pytest.raises(BridgeNotReady):
            await bridge.connect()
