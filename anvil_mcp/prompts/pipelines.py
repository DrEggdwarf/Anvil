"""Orchestration prompt templates for common Anvil pipelines."""

from __future__ import annotations


def exploit_pipeline(binary_path: str, arch: str | None = None) -> str:
    """Return a step-by-step orchestration prompt for exploit development.

    Pipeline: checksec → RE analyze → function listing → GDB load → stepping → exploit.
    """
    arch_hint = f" (arch: {arch})" if arch else ""
    return (
        f"Exploit development pipeline for: {binary_path}{arch_hint}\n\n"
        "Steps:\n"
        "1. session_create('pwn') → session_id_pwn\n"
        "2. pwn_checksec(session_id_pwn, binary_path) — identify mitigations\n"
        "3. session_create('rizin') → session_id_re\n"
        "4. re_analyze(session_id_re, binary_path) — full analysis\n"
        "5. re_functions(session_id_re) — list functions, focus on main/vuln candidates\n"
        "6. re_decompile(session_id_re, 'main') — understand control flow\n"
        "7. re_strings(session_id_re) — look for interesting strings / format strings\n"
        "8. session_create('gdb') → session_id_gdb\n"
        "9. gdb_load(session_id_gdb, binary_path)\n"
        "10. gdb_breakpoint(session_id_gdb, 'main', 'set')\n"
        "11. gdb_run(session_id_gdb) → step through vulnerable code path\n"
        "12. pwn_rop_gadgets(session_id_pwn, binary_path) — build ROP chain if needed\n"
        "13. pwn_shellcraft(session_id_pwn, arch, 'linux', 'sh') — generate shellcode\n"
        "14. Write exploit.py using the gathered offsets, gadgets, and shellcode.\n"
        "Cleanup: session_delete all session IDs when done."
    )


def firmware_audit(blob_path: str) -> str:
    """Return a step-by-step orchestration prompt for firmware security audit."""
    return (
        f"Firmware security audit pipeline for: {blob_path}\n\n"
        "Steps:\n"
        "1. session_create('firmware') → session_id_fw\n"
        "2. firmware_scan(session_id_fw, blob_path) — identify components and offsets\n"
        "3. firmware_entropy(session_id_fw, blob_path) — locate encrypted/compressed regions\n"
        "4. firmware_extract(session_id_fw, blob_path) → output_dir\n"
        "5. firmware_triage(session_id_fw, output_dir) — flag high-severity findings first\n"
        "6. For each ELF binary found in the triage:\n"
        "   a. session_create('rizin') → session_id_re\n"
        "   b. re_analyze(session_id_re, elf_path)\n"
        "   c. re_strings(session_id_re) — look for credentials, URLs, keys\n"
        "   d. re_functions(session_id_re) — look for dangerous function calls\n"
        "   e. re_decompile(session_id_re, 'main') if relevant\n"
        "   f. session_delete(session_id_re)\n"
        "7. Summarize: CVEs, hardcoded secrets, attack surface.\n"
        "Cleanup: session_delete(session_id_fw)"
    )


def ctf_binary(binary_path: str, description: str | None = None) -> str:
    """Return a step-by-step orchestration prompt for CTF binary challenges."""
    desc_hint = f"\nChallenge description: {description}" if description else ""
    return (
        f"CTF binary challenge pipeline for: {binary_path}{desc_hint}\n\n"
        "Steps:\n"
        "1. session_create('pwn') → session_id_pwn\n"
        "2. pwn_checksec(session_id_pwn, binary_path) — note: NX? PIE? canary?\n"
        "3. session_create('rizin') → session_id_re\n"
        "4. re_analyze(session_id_re, binary_path)\n"
        "5. re_strings(session_id_re) — flags, hints, format strings?\n"
        "6. re_decompile(session_id_re, 'main') — understand the challenge logic\n"
        "7. re_functions(session_id_re) — find win() / shell() / hidden functions\n"
        "8. re_xrefs(session_id_re, 'win') — where is it called (or not called)?\n"
        "9. session_create('gdb') → session_id_gdb\n"
        "10. gdb_load(session_id_gdb, binary_path)\n"
        "11. gdb_breakpoint + gdb_run + gdb_step — confirm vulnerability\n"
        "12. pwn_cyclic + pwn_cyclic_find — determine buffer overflow offset\n"
        "13. pwn_rop_gadgets if ROP chain needed\n"
        "14. Write and test the exploit.\n"
        "Cleanup: session_delete all session IDs."
    )
