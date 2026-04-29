"""Protocol Bridge — ICS/OT protocol communication via pymodbus.

Wraps pymodbus with full Modbus feature coverage:
- Connection management (TCP, UDP, Serial RTU/ASCII, TLS)
- Read operations: coils, discrete inputs, holding registers, input registers,
  FIFO queue, exception status, file records
- Write operations: single/multiple coils, single/multiple registers,
  mask write, read/write multiple registers, file records
- Device identification (MEI type 14, report server ID)
- Diagnostics (all sub-functions 0x00-0x15)
- Communication event counters/log
- Data type conversion (INT16/32/64, UINT, FLOAT32/64, STRING, BITS)
- Simulator / honeypot server
- Framing: RTU, ASCII, TCP/IP (Socket), TLS
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from backend.app.bridges.base import BaseBridge, BridgeState
from backend.app.bridges.registry import bridge_registry
from backend.app.core.exceptions import BridgeCrash, BridgeNotReady

logger = logging.getLogger(__name__)

# Map transport names to pymodbus classes
TRANSPORT_MAP = {
    "tcp": "ModbusTcpClient",
    "udp": "ModbusUdpClient",
    "serial": "ModbusSerialClient",
    "tls": "ModbusTlsClient",
}

FRAMER_MAP = {
    "rtu": "RTU",
    "ascii": "ASCII",
    "socket": "SOCKET",
    "tls": "TLS",
}


class ProtocolBridge(BaseBridge):
    """Modbus protocol bridge via pymodbus."""

    bridge_type = "protocol"

    def __init__(self) -> None:
        super().__init__()
        self._pymodbus: Any = None
        self._client: Any = None
        self._connected = False
        self._transport: str | None = None
        self._server: Any = None

    async def start(self) -> None:
        """Import pymodbus — no connection yet."""
        self.state = BridgeState.STARTING
        try:
            import pymodbus

            self._pymodbus = pymodbus
            self.state = BridgeState.READY
            logger.info("Protocol bridge started (pymodbus %s)", getattr(pymodbus, "__version__", "?"))
        except Exception as e:
            self.state = BridgeState.ERROR
            raise BridgeCrash("protocol", exit_code=None) from e

    async def stop(self) -> None:
        """Disconnect and cleanup."""
        self.state = BridgeState.STOPPING
        await self.disconnect()
        if self._server:
            try:
                await self._stop_server()
            except Exception:
                logger.exception("Error stopping server")
        self._pymodbus = None
        self.state = BridgeState.STOPPED
        logger.info("Protocol bridge stopped")

    async def health(self) -> bool:
        return self._pymodbus is not None

    async def execute(self, command: str, **kwargs: Any) -> Any:
        """Generic execute."""
        self._require_ready()
        method = getattr(self, command, None)
        if method and callable(method):
            import inspect

            result = method(**kwargs)
            if inspect.isawaitable(result):
                return await result
            return result
        raise ValueError(f"Unknown command: {command}")

    # ── Connection management ────────────────────────────

    async def connect(
        self,
        transport: str = "tcp",
        host: str = "127.0.0.1",
        port: int = 502,
        framer: str | None = None,
        timeout: float = 3.0,
        retries: int = 3,
        baudrate: int = 19200,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: int = 1,
    ) -> dict:
        """Connect to Modbus device."""
        self._require_ready()
        from pymodbus.client import (
            ModbusSerialClient,
            ModbusTcpClient,
            ModbusTlsClient,
            ModbusUdpClient,
        )
        from pymodbus.framer import FramerType

        # Map framer
        framer_type = None
        if framer:
            framer_map = {
                "rtu": FramerType.RTU,
                "ascii": FramerType.ASCII,
                "socket": FramerType.SOCKET,
                "tls": FramerType.TLS,
            }
            framer_type = framer_map.get(framer.lower())

        client_map = {
            "tcp": lambda: ModbusTcpClient(
                host=host,
                port=port,
                timeout=timeout,
                retries=retries,
                framer=framer_type or FramerType.SOCKET,
            ),
            "udp": lambda: ModbusUdpClient(
                host=host,
                port=port,
                timeout=timeout,
                retries=retries,
                framer=framer_type or FramerType.SOCKET,
            ),
            "tls": lambda: ModbusTlsClient(
                host=host,
                port=port or 802,
                timeout=timeout,
                retries=retries,
                framer=framer_type or FramerType.TLS,
            ),
            "serial": lambda: ModbusSerialClient(
                port=host,  # serial port path
                baudrate=baudrate,
                bytesize=bytesize,
                parity=parity,
                stopbits=stopbits,
                timeout=timeout,
                retries=retries,
                framer=framer_type or FramerType.RTU,
            ),
        }

        factory = client_map.get(transport.lower())
        if not factory:
            raise ValueError(f"Unknown transport: {transport}. Use: {list(client_map)}")

        self._client = factory()
        result = self._client.connect()
        self._connected = bool(result)
        self._transport = transport
        return {
            "connected": self._connected,
            "transport": transport,
            "host": host,
            "port": port,
        }

    async def disconnect(self) -> None:
        """Disconnect from Modbus device."""
        if self._client:
            with contextlib.suppress(Exception):
                self._client.close()
            self._client = None
        self._connected = False

    def _require_connected(self) -> None:
        """Ensure client is connected."""
        self._require_ready()
        if not self._client or not self._connected:
            raise BridgeNotReady("protocol (not connected)")

    def _check_response(self, rr: Any) -> dict:
        """Check response for errors, return structured result."""
        if rr.isError():
            return {
                "error": True,
                "exception_code": getattr(rr, "exception_code", None),
                "function_code": getattr(rr, "function_code", None),
            }
        return {"error": False}

    # ── Read operations (safe) ───────────────────────────

    async def read_coils(self, address: int, count: int = 1, device_id: int = 1) -> dict:
        """FC01: Read coils. Returns list of booleans."""
        self._require_connected()
        rr = self._client.read_coils(address, count=count, slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["values"] = rr.bits[:count]
        return result

    async def read_discrete_inputs(self, address: int, count: int = 1, device_id: int = 1) -> dict:
        """FC02: Read discrete inputs. Returns list of booleans."""
        self._require_connected()
        rr = self._client.read_discrete_inputs(address, count=count, slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["values"] = rr.bits[:count]
        return result

    async def read_holding_registers(self, address: int, count: int = 1, device_id: int = 1) -> dict:
        """FC03: Read holding registers. Returns list of ints (16-bit)."""
        self._require_connected()
        rr = self._client.read_holding_registers(address, count=count, slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["values"] = rr.registers
        return result

    async def read_input_registers(self, address: int, count: int = 1, device_id: int = 1) -> dict:
        """FC04: Read input registers. Returns list of ints (16-bit)."""
        self._require_connected()
        rr = self._client.read_input_registers(address, count=count, slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["values"] = rr.registers
        return result

    async def read_exception_status(self, device_id: int = 1) -> dict:
        """FC07: Read exception status."""
        self._require_connected()
        rr = self._client.read_exception_status(slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["status"] = rr.status
        return result

    async def read_fifo_queue(self, address: int = 0, device_id: int = 1) -> dict:
        """FC24: Read FIFO queue."""
        self._require_connected()
        rr = self._client.read_fifo_queue(address=address, slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["values"] = rr.registers if hasattr(rr, "registers") else []
        return result

    async def read_file_record(
        self,
        file_number: int,
        record_number: int,
        record_length: int,
        device_id: int = 1,
    ) -> dict:
        """FC20: Read file record."""
        self._require_connected()
        from pymodbus.pdu import FileRecord

        record = FileRecord(
            file_number=file_number,
            record_number=record_number,
            record_length=record_length,
        )
        rr = self._client.read_file_record([record], slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["records"] = [{"data": r.record_data.hex()} for r in rr.records] if hasattr(rr, "records") else []
        return result

    # ── Write operations (DANGEROUS) ─────────────────────

    async def write_coil(self, address: int, value: bool, device_id: int = 1) -> dict:
        """FC05: Write single coil. ⚠️ WRITES TO DEVICE."""
        self._require_connected()
        rr = self._client.write_coil(address, value, slave=device_id)
        return self._check_response(rr)

    async def write_register(self, address: int, value: int, device_id: int = 1) -> dict:
        """FC06: Write single register. ⚠️ WRITES TO DEVICE."""
        self._require_connected()
        rr = self._client.write_register(address, value, slave=device_id)
        return self._check_response(rr)

    async def write_coils(self, address: int, values: list[bool], device_id: int = 1) -> dict:
        """FC15: Write multiple coils. ⚠️ BULK WRITE TO DEVICE."""
        self._require_connected()
        rr = self._client.write_coils(address, values, slave=device_id)
        return self._check_response(rr)

    async def write_registers(self, address: int, values: list[int], device_id: int = 1) -> dict:
        """FC16: Write multiple registers. ⚠️ BULK WRITE TO DEVICE."""
        self._require_connected()
        rr = self._client.write_registers(address, values, slave=device_id)
        return self._check_response(rr)

    async def mask_write_register(
        self,
        address: int = 0,
        and_mask: int = 0xFFFF,
        or_mask: int = 0x0000,
        device_id: int = 1,
    ) -> dict:
        """FC22: Mask write register (AND/OR). ⚠️ WRITES TO DEVICE."""
        self._require_connected()
        rr = self._client.mask_write_register(
            address=address,
            and_mask=and_mask,
            or_mask=or_mask,
            slave=device_id,
        )
        return self._check_response(rr)

    async def readwrite_registers(
        self,
        read_address: int = 0,
        read_count: int = 1,
        write_address: int = 0,
        write_values: list[int] | None = None,
        device_id: int = 1,
    ) -> dict:
        """FC23: Atomic read+write multiple registers. ⚠️ WRITES TO DEVICE."""
        self._require_connected()
        rr = self._client.readwrite_registers(
            read_address=read_address,
            read_count=read_count,
            write_address=write_address,
            values=write_values or [],
            slave=device_id,
        )
        result = self._check_response(rr)
        if not result["error"] and hasattr(rr, "registers"):
            result["values"] = rr.registers
        return result

    async def write_file_record(
        self,
        file_number: int,
        record_number: int,
        record_data: str,
        device_id: int = 1,
    ) -> dict:
        """FC21: Write file record. ⚠️ WRITES TO DEVICE."""
        self._require_connected()
        from pymodbus.pdu import FileRecord

        data = bytes.fromhex(record_data)
        record = FileRecord(
            file_number=file_number,
            record_number=record_number,
            record_data=data,
        )
        rr = self._client.write_file_record([record], slave=device_id)
        return self._check_response(rr)

    # ── Device identification ────────────────────────────

    async def read_device_info(self, read_code: int = 1, object_id: int = 0, device_id: int = 1) -> dict:
        """FC43/MEI14: Read device identification.

        read_code: 1=Basic, 2=Regular, 3=Extended, 4=Specific
        """
        self._require_connected()
        from pymodbus.constants import DeviceInformation

        code_map = {
            1: DeviceInformation.BASIC,
            2: DeviceInformation.REGULAR,
            3: DeviceInformation.EXTENDED,
            4: DeviceInformation.SPECIFIC,
        }
        rr = self._client.read_device_information(
            read_code=code_map.get(read_code, DeviceInformation.BASIC),
            object_id=object_id,
            slave=device_id,
        )
        result = self._check_response(rr)
        if not result["error"] and hasattr(rr, "information"):
            # Object ID → name mapping
            obj_names = {
                0x00: "VendorName",
                0x01: "ProductCode",
                0x02: "MajorMinorRevision",
                0x03: "VendorUrl",
                0x04: "ProductName",
                0x05: "ModelName",
                0x06: "UserApplicationName",
            }
            info = {}
            for oid, val in rr.information.items():
                name = obj_names.get(oid, f"object_{oid:#x}")
                info[name] = val.decode(errors="replace") if isinstance(val, bytes) else str(val)
            result["information"] = info
        return result

    async def report_server_id(self, device_id: int = 1) -> dict:
        """FC17: Report server/device ID."""
        self._require_connected()
        rr = self._client.report_slave_id(slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["data"] = rr.encode().hex() if hasattr(rr, "encode") else ""
        return result

    # ── Diagnostics (FC08) ───────────────────────────────

    async def diag_query(self, message: str = "0000", device_id: int = 1) -> dict:
        """FC08/00: Diagnostic query (loopback test)."""
        self._require_connected()
        data = bytes.fromhex(message)
        rr = self._client.diag_query_data(msg=data, slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["message"] = rr.message.hex() if hasattr(rr, "message") else ""
        return result

    async def diag_restart_comm(self, toggle: bool = False, device_id: int = 1) -> dict:
        """FC08/01: Restart communications. ⚠️ RESTARTS DEVICE COMMS."""
        self._require_connected()
        rr = self._client.diag_restart_communication(toggle=toggle, slave=device_id)
        return self._check_response(rr)

    async def diag_read_register(self, device_id: int = 1) -> dict:
        """FC08/02: Read diagnostic register."""
        self._require_connected()
        rr = self._client.diag_read_diagnostic_register(slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["register"] = rr.message if hasattr(rr, "message") else 0
        return result

    async def diag_force_listen_only(self, device_id: int = 1) -> dict:
        """FC08/04: Force listen-only mode. ⚠️ ISOLATES DEVICE FROM BUS."""
        self._require_connected()
        rr = self._client.diag_force_listen_only(slave=device_id)
        return self._check_response(rr)

    async def diag_clear_counters(self, device_id: int = 1) -> dict:
        """FC08/0A: Clear all diagnostic counters. ⚠️ MODIFIES DEVICE STATE."""
        self._require_connected()
        rr = self._client.diag_clear_counters(slave=device_id)
        return self._check_response(rr)

    async def diag_bus_message_count(self, device_id: int = 1) -> dict:
        """FC08/0B: Read bus message count."""
        self._require_connected()
        rr = self._client.diag_read_bus_message_count(slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["count"] = rr.message if hasattr(rr, "message") else 0
        return result

    async def diag_bus_error_count(self, device_id: int = 1) -> dict:
        """FC08/0C: Read bus communication error count."""
        self._require_connected()
        rr = self._client.diag_read_bus_comm_error_count(slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["count"] = rr.message if hasattr(rr, "message") else 0
        return result

    async def diag_bus_exception_count(self, device_id: int = 1) -> dict:
        """FC08/0D: Read bus exception error count."""
        self._require_connected()
        rr = self._client.diag_read_bus_exception_error_count(slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["count"] = rr.message if hasattr(rr, "message") else 0
        return result

    async def diag_device_message_count(self, device_id: int = 1) -> dict:
        """FC08/0E: Read device message count."""
        self._require_connected()
        rr = self._client.diag_read_device_message_count(slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["count"] = rr.message if hasattr(rr, "message") else 0
        return result

    async def diag_no_response_count(self, device_id: int = 1) -> dict:
        """FC08/0F: Read device no-response count."""
        self._require_connected()
        rr = self._client.diag_read_device_no_response_count(slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["count"] = rr.message if hasattr(rr, "message") else 0
        return result

    async def diag_nak_count(self, device_id: int = 1) -> dict:
        """FC08/10: Read device NAK count."""
        self._require_connected()
        rr = self._client.diag_read_device_nak_count(slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["count"] = rr.message if hasattr(rr, "message") else 0
        return result

    async def diag_busy_count(self, device_id: int = 1) -> dict:
        """FC08/11: Read device busy count."""
        self._require_connected()
        rr = self._client.diag_read_device_busy_count(slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["count"] = rr.message if hasattr(rr, "message") else 0
        return result

    async def diag_overrun_count(self, device_id: int = 1) -> dict:
        """FC08/12: Read bus character overrun count."""
        self._require_connected()
        rr = self._client.diag_read_bus_char_overrun_count(slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["count"] = rr.message if hasattr(rr, "message") else 0
        return result

    # ── Communication event counters/log ─────────────────

    async def get_comm_event_counter(self, device_id: int = 1) -> dict:
        """FC11: Get communication event counter."""
        self._require_connected()
        rr = self._client.diag_get_comm_event_counter(slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["status"] = getattr(rr, "status", 0)
            result["count"] = getattr(rr, "count", 0)
        return result

    async def get_comm_event_log(self, device_id: int = 1) -> dict:
        """FC12: Get communication event log."""
        self._require_connected()
        rr = self._client.diag_get_comm_event_log(slave=device_id)
        result = self._check_response(rr)
        if not result["error"]:
            result["status"] = getattr(rr, "status", 0)
            result["event_count"] = getattr(rr, "event_count", 0)
            result["message_count"] = getattr(rr, "message_count", 0)
            result["events"] = getattr(rr, "events", [])
        return result

    # ── Data type conversion ─────────────────────────────

    async def convert_from_registers(
        self,
        registers: list[int],
        data_type: str = "UINT16",
        word_order: str = "big",
    ) -> Any:
        """Convert register values to typed Python value."""
        self._require_ready()
        from pymodbus.client import ModbusClientMixin
        from pymodbus.constants import DATATYPE

        dtype = getattr(DATATYPE, data_type.upper(), None)
        if dtype is None:
            raise ValueError(f"Unknown data type: {data_type}")
        return ModbusClientMixin.convert_from_registers(registers, dtype, word_order=word_order)

    async def convert_to_registers(
        self,
        value: Any,
        data_type: str = "UINT16",
        word_order: str = "big",
    ) -> list[int]:
        """Convert typed Python value to register values."""
        self._require_ready()
        from pymodbus.client import ModbusClientMixin
        from pymodbus.constants import DATATYPE

        dtype = getattr(DATATYPE, data_type.upper(), None)
        if dtype is None:
            raise ValueError(f"Unknown data type: {data_type}")
        return ModbusClientMixin.convert_to_registers(value, dtype, word_order=word_order)

    # ── Scan / Discovery ─────────────────────────────────

    async def scan_devices(self, start_id: int = 1, end_id: int = 247) -> list[dict]:
        """Scan for responsive Modbus devices by unit ID."""
        self._require_connected()
        found = []
        for uid in range(start_id, min(end_id + 1, 248)):
            try:
                rr = self._client.read_holding_registers(0, count=1, slave=uid)
                if not rr.isError():
                    found.append(
                        {
                            "device_id": uid,
                            "status": "responsive",
                            "register_0": rr.registers[0] if rr.registers else None,
                        }
                    )
            except Exception:
                logger.debug("Device %d not responding", uid)
                continue
        return found

    async def scan_registers(
        self,
        start: int = 0,
        end: int = 100,
        register_type: str = "holding",
        device_id: int = 1,
    ) -> list[dict]:
        """Scan a range of registers. Returns non-zero values."""
        self._require_connected()
        read_fn = {
            "holding": self._client.read_holding_registers,
            "input": self._client.read_input_registers,
            "coil": self._client.read_coils,
            "discrete": self._client.read_discrete_inputs,
        }.get(register_type)
        if not read_fn:
            raise ValueError(f"Unknown register type: {register_type}")

        results = []
        # Read in chunks of 125 (Modbus max per request)
        chunk_size = 125
        for offset in range(start, end + 1, chunk_size):
            count = min(chunk_size, end - offset + 1)
            try:
                rr = read_fn(offset, count=count, slave=device_id)
                if not rr.isError():
                    values = rr.bits if register_type in ("coil", "discrete") else rr.registers
                    for i, val in enumerate(values[:count]):
                        if val:  # Only report non-zero
                            results.append(
                                {
                                    "address": offset + i,
                                    "value": val,
                                }
                            )
            except Exception:
                logger.debug("Scan chunk at offset %d failed", offset)
                continue
        return results

    # ── Server / Simulator ───────────────────────────────

    async def start_server(
        self,
        port: int = 5020,
        device_id: int = 1,
        coils: int = 100,
        discrete_inputs: int = 100,
        holding_registers: int = 100,
        input_registers: int = 100,
    ) -> dict:
        """Start a Modbus TCP simulator/honeypot server."""
        self._require_ready()
        from pymodbus.datastore import (
            ModbusSequentialDataBlock,
            ModbusServerContext,
            ModbusSlaveContext,
        )
        from pymodbus.server import StartAsyncTcpServer

        store = ModbusSlaveContext(
            di=ModbusSequentialDataBlock(0, [0] * discrete_inputs),
            co=ModbusSequentialDataBlock(0, [0] * coils),
            hr=ModbusSequentialDataBlock(0, [0] * holding_registers),
            ir=ModbusSequentialDataBlock(0, [0] * input_registers),
        )
        context = ModbusServerContext(slaves={device_id: store}, single=False)

        # Start server in background
        import asyncio

        self._server = asyncio.create_task(StartAsyncTcpServer(context=context, address=("127.0.0.1", port)))
        return {
            "status": "started",
            "port": port,
            "device_id": device_id,
            "registers": {
                "coils": coils,
                "discrete_inputs": discrete_inputs,
                "holding_registers": holding_registers,
                "input_registers": input_registers,
            },
        }

    async def _stop_server(self) -> None:
        """Stop the simulator server."""
        if self._server:
            self._server.cancel()
            self._server = None

    # ── Properties ───────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def transport(self) -> str | None:
        return self._transport


# Auto-register
bridge_registry.register("protocol", ProtocolBridge)
