"""RE tools — wired to the FastAPI /api/re endpoints."""

from __future__ import annotations

from anvil_mcp.client import get_client


async def re_analyze(session_id: str, binary_path: str) -> dict:
    """Load and analyze a binary with rizin (aaa level).

    Returns: {ok, functions_found, strings_found, summary}
    """
    client = get_client()
    await client.post(
        f"/api/re/{session_id}/open",
        json={"binary_path": binary_path},
    )
    await client.post(
        f"/api/re/{session_id}/analyze",
        json={"level": "aaa"},
    )
    funcs = await client.get(f"/api/re/{session_id}/functions")
    fn_list = funcs.get("data") or funcs.get("functions") or []
    strings = await client.get(f"/api/re/{session_id}/strings/all")
    str_list = strings.get("data") or strings.get("strings") or []
    return {
        "summary": (
            f"Analyzed {binary_path}: {len(fn_list)} functions, {len(str_list)} strings"
        ),
        "ok": True,
        "functions_found": len(fn_list),
        "strings_found": len(str_list),
    }


async def re_functions(session_id: str) -> dict:
    """List all functions identified in the analyzed binary.

    Returns: {summary, functions: [{addr, name, size}]}
    """
    client = get_client()
    data = await client.get(f"/api/re/{session_id}/functions")
    fn_list = data.get("data") or data.get("functions") or []
    funcs = [
        {"addr": hex(f["offset"]), "name": f["name"], "size": f.get("size", 0)}
        for f in fn_list
    ]
    return {
        "summary": f"{len(funcs)} functions found",
        "functions": funcs,
    }


async def re_disasm(session_id: str, addr_or_name: str) -> dict:
    """Disassemble a function at the given address.

    Returns: {summary, instructions: [{addr, bytes, disasm}]}
    """
    client = get_client()
    data = await client.get(f"/api/re/{session_id}/disassemble/function/{addr_or_name}")
    ops = data.get("data") or data.get("ops") or []
    instrs = [
        {
            "addr": hex(op.get("offset", 0)),
            "bytes": op.get("bytes", ""),
            "disasm": op.get("disasm", ""),
        }
        for op in ops
    ]
    return {
        "summary": f"{len(instrs)} instructions at {addr_or_name}",
        "instructions": instrs,
    }


async def re_decompile(session_id: str, addr_or_name: str) -> dict:
    """Decompile a function to C via r2ghidra (falls back to rz-dec).

    Returns: {summary, addr, code, language, source}
    """
    client = get_client()
    data = await client.post(
        f"/api/re/{session_id}/decompile",
        json={"address": addr_or_name},
    )
    code = data.get("code", "")
    source = data.get("source", "unknown")
    lines = code.count("\n") + 1 if code else 0
    return {
        "summary": f"Decompiled {addr_or_name} ({lines} lines, via {source})",
        "addr": addr_or_name,
        "code": code,
        "language": data.get("language", "c"),
        "source": source,
    }


async def re_strings(session_id: str, min_len: int = 4) -> dict:
    """List strings found in the binary.

    Args:
        min_len: Minimum string length to include (default 4).

    Returns: {summary, strings: [{addr, value, size, type}]}
    """
    client = get_client()
    data = await client.get(f"/api/re/{session_id}/strings/all")
    raw = data.get("data") or data.get("strings") or []
    filtered = [
        {
            "addr": hex(s.get("vaddr", 0)),
            "value": s.get("string", ""),
            "size": s.get("size", 0),
            "type": s.get("type", "ascii"),
        }
        for s in raw
        if len(s.get("string", "")) >= min_len
    ]
    return {
        "summary": f"{len(filtered)} strings (min_len={min_len})",
        "strings": filtered,
    }


async def re_xrefs(session_id: str, addr: str) -> dict:
    """Get cross-references to and from an address.

    Returns: {summary, to: [{from, type, name}], from_: [{to, type, name}]}
    """
    client = get_client()
    to_data = await client.get(f"/api/re/{session_id}/xrefs/to/{addr}")
    from_data = await client.get(f"/api/re/{session_id}/xrefs/from/{addr}")
    xrefs_to = to_data.get("data") or to_data.get("xrefs") or []
    xrefs_from = from_data.get("data") or from_data.get("xrefs") or []
    to_list = [
        {
            "from": hex(x.get("from", 0)),
            "type": x.get("type", ""),
            "name": x.get("name", ""),
        }
        for x in xrefs_to
    ]
    from_list = [
        {
            "to": hex(x.get("to", 0)),
            "type": x.get("type", ""),
            "name": x.get("name", ""),
        }
        for x in xrefs_from
    ]
    return {
        "summary": f"{len(to_list)} refs to, {len(from_list)} refs from {addr}",
        "to": to_list,
        "from_": from_list,
    }
