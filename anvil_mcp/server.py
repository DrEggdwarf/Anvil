"""Anvil MCP Server — entry point.

Run with stdio (Claude Desktop):
    python -m anvil_mcp.server

Run with SSE transport (browser/web clients):
    python -m anvil_mcp.server --transport sse --port 8001

Requires the Anvil FastAPI backend to be running on port 8000.
"""

from __future__ import annotations

import argparse

from mcp.server.fastmcp import FastMCP

import anvil_mcp.client as _client_mod
from anvil_mcp.client import AnvilClient
from anvil_mcp.prompts.pipelines import ctf_binary, exploit_pipeline, firmware_audit
from anvil_mcp.tools.asm import (
    gdb_breakpoint,
    gdb_disasm,
    gdb_load,
    gdb_memory,
    gdb_registers,
    gdb_run,
    gdb_step,
)
from anvil_mcp.tools.firmware import (
    firmware_entropy,
    firmware_extract,
    firmware_scan,
    firmware_triage,
)
from anvil_mcp.tools.pwn import (
    pwn_checksec,
    pwn_cyclic,
    pwn_cyclic_find,
    pwn_rop_gadgets,
    pwn_shellcraft,
)
from anvil_mcp.tools.re import (
    re_analyze,
    re_decompile,
    re_disasm,
    re_functions,
    re_strings,
    re_xrefs,
)
from anvil_mcp.tools.session import session_create, session_delete, session_list
from anvil_mcp.tools.wire import (
    wire_decode_frame,
    wire_load_pcap,
    wire_replay,
    wire_send,
)

mcp = FastMCP("anvil")

# ── Session tools (wired) ────────────────────────────────
mcp.tool()(session_create)
mcp.tool()(session_delete)
mcp.tool()(session_list)

# ── ASM/GDB tools (stubs) ────────────────────────────────
mcp.tool()(gdb_load)
mcp.tool()(gdb_run)
mcp.tool()(gdb_step)
mcp.tool()(gdb_breakpoint)
mcp.tool()(gdb_registers)
mcp.tool()(gdb_memory)
mcp.tool()(gdb_disasm)

# ── Pwn tools (stubs) ────────────────────────────────────
mcp.tool()(pwn_checksec)
mcp.tool()(pwn_cyclic)
mcp.tool()(pwn_cyclic_find)
mcp.tool()(pwn_rop_gadgets)
mcp.tool()(pwn_shellcraft)

# ── RE tools (stubs) ─────────────────────────────────────
mcp.tool()(re_analyze)
mcp.tool()(re_functions)
mcp.tool()(re_disasm)
mcp.tool()(re_decompile)
mcp.tool()(re_strings)
mcp.tool()(re_xrefs)

# ── Firmware tools (stubs) ───────────────────────────────
mcp.tool()(firmware_scan)
mcp.tool()(firmware_extract)
mcp.tool()(firmware_entropy)
mcp.tool()(firmware_triage)

# ── Wire/ICS tools (stubs) ───────────────────────────────
mcp.tool()(wire_load_pcap)
mcp.tool()(wire_decode_frame)
mcp.tool()(wire_send)
mcp.tool()(wire_replay)

# ── Prompts ──────────────────────────────────────────────
mcp.prompt()(exploit_pipeline)
mcp.prompt()(firmware_audit)
mcp.prompt()(ctf_binary)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Anvil MCP Server")
    p.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    p.add_argument("--port", type=int, default=8001)
    p.add_argument(
        "--backend", default="http://127.0.0.1:8000", help="FastAPI base URL"
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    _client_mod._client = AnvilClient(args.backend)

    if args.transport == "sse":
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run(transport="stdio")
