# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Anvil

Toolkit de securite bas niveau integre : ASM, Pwn, Reverse Engineering, Firmware, Wire (ICS/OT). Desktop app — "Le Burp Suite du bas niveau" (ADR-021).

## Stack

| Layer | Tech | Role |
|-------|------|------|
| Shell | Tauri v2 (Rust) | Desktop app, IPC, spawns backend subprocess |
| Frontend | React 19 + TypeScript 5 + Vite 7 | UI with 5 modules (ASM, Pwn, RE, Firmware, Wire) |
| Backend | FastAPI + Python 3.12 | REST/WebSocket API, 6 tool bridges, security layers |

## Commands

```bash
# Frontend dev (port 1420)
npm run dev

# Full desktop dev (Tauri + frontend + backend)
npm run tauri dev

# Build desktop app
npm run tauri build

# Backend standalone (always from repo root — imports use `from backend.app.X`)
uvicorn backend.app.main:app --reload --port 8000

# Run all Python tests (`python -m` puts the repo root on sys.path so
# `from backend.app...` resolves; plain `pytest tests/` will fail otherwise)
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_gdb_bridge.py -v

# Run a single test by name
python -m pytest tests/test_gdb_bridge.py -k "test_load_binary" -v

# Run with coverage
python -m pytest tests/ --cov=backend/app --cov-report=term-missing

# Frontend tests
npx vitest

# Lint & security checks
npx tsc --noEmit
cargo check --manifest-path src-tauri/Cargo.toml
ruff check backend/ tests/
bandit -r backend/ -c backend/pyproject.toml
```

Note: pytest asyncio_mode is set to "auto" in pyproject.toml — no need for `@pytest.mark.asyncio`.

## Architecture

```
src-tauri/src/     Rust shell: spawns backend as subprocess, 2 IPC commands (check_backend, check_dependencies)
src/               React UI — multi-mode: ASM (3-col editor+debug), Pwn (split editors+terminal+tools)
backend/app/       FastAPI: main.py → 9 routers (health, sessions, gdb, compile, rizin, pwn, firmware, protocol, ws), core/, bridges/, models/, sessions/
anvil_mcp/         Standalone MCP server: exposes all tools/resources/prompts to Claude Desktop/Cursor
tests/             25+ pytest modules, ~736 tests, all use MockBridge (no real tools needed in CI)
ai/                12 Claude Code agents + 2 workflows (see ai/README.md)
```

[AGENTS.md](AGENTS.md) is a condensed companion to this file (commands cheatsheet + key patterns). Keep both in sync when editing.

### MCP Server (`anvil_mcp/`)

Standalone Python server, a client of the FastAPI backend. Lets Claude orchestrate the
full attack pipeline (Firmware → RE → Pwn) autonomously.

```
Claude Desktop / Cursor
      │ stdio (default) or SSE --port 8001
      ▼
anvil_mcp/server.py  (FastMCP)
      │ HTTP REST  →  http://127.0.0.1:8000
      ▼
FastAPI backend  ← existing bridges
```

- Install: `pip install -e "backend/[mcp]"` (adds `mcp>=1.0` + `httpx`)
- Run: `python -m anvil_mcp.server` (stdio) or `python -m anvil_mcp.server --transport sse --port 8001`
- **Session tools** (`anvil_mcp/tools/session.py`) are fully wired to `/api/sessions`.
- **Domain tools** (asm, pwn, re, firmware, wire) are stubs — `NotImplementedError` — filled per-sprint as modules mature.
- **LLM output rule**: every MCP-destined bridge method must return a structured `dict` (not raw `str`). Include a `summary` field (one sentence) when useful. `rizin_bridge.analyze()` and `decompile()` already follow this rule.

### How the layers connect

- **Tauri spawns FastAPI** as a child process on port 8000 at app start, kills it on exit. Tauri itself is a thin shell — no business logic in Rust.
- **Frontend talks to backend** via REST (simple requests) and WebSocket (`/ws/{session_type}/{session_id}`) for streaming (debug stepping, console output).
- **Tauri IPC** is only used for native features: file dialogs, serial port, health/dependency checks.

### Session-based isolation

Every API interaction goes through sessions. A session owns one bridge instance (GDB, rizin, pwntools, etc.) and one workspace directory (`~/.anvil/workspaces/{session_id}/`). `session_id` is `uuid.uuid4().hex[:16]` (16 hex chars). Sessions auto-expire after 1 hour via a background cleanup loop (60s interval). Max 10 concurrent sessions.

```
POST /api/sessions {bridge_type: "gdb"} → session_id
POST /api/gdb/{session_id}/load → uses session's GdbBridge
DELETE /api/sessions/{session_id} → destroys bridge + workspace
```

### Bridge pattern

All 6 bridges inherit `BaseBridge` with lifecycle states: `CREATED → STARTING → READY → BUSY → STOPPING → STOPPED | ERROR`. Each wraps an external tool (pygdbmi, rzpipe, pwntools, binwalk, pymodbus, or nasm/gcc/ld via SubprocessManager). Bridges self-register in `bridge_registry` at import time. To add a new bridge: subclass BaseBridge, implement `start/stop/health/execute`, import it in `core/lifecycle.py`.

### WebSocket dispatcher

Single endpoint `/ws/{session_type}/{session_id}` routes typed messages (`WSMessage`) by command name (e.g., `"gdb.step_into"`). New WS commands are added by registering a handler function, not by adding routes.

### Security layers (3 deep)

1. **API layer**: Pydantic v2 validators with Field constraints (max_length on all strings, ge/le on numerics, max_length on lists)
2. **Bridge layer**: command injection blockers in `core/sanitization.py` — GDB blocks `shell`/`python`/`source`; rizin blocks `!` prefix; GCC flags use allowlists
3. **Path layer**: workspace sandbox via `.is_relative_to()`, blocks `/etc`, `/proc`, `/sys`, null bytes, traversal

### Subprocess management

`SubprocessManager` enforces max 20 concurrent processes via asyncio semaphore, 10 MB output limit, configurable timeouts (default 30s). Graceful kill: SIGTERM → 5s grace → SIGKILL. All processes tracked and cleaned on shutdown.

### Error hierarchy

```
AnvilError (code, message, details) → mapped to HTTP status in main.py exception handler
├── BridgeError → BridgeNotReady, BridgeTimeout, BridgeCrash
├── SessionError → SessionNotFound, SessionExpired, SessionLimitReached
├── ValidationError → InvalidFile, InvalidCommand
└── SubprocessError → SubprocessTimeout, SubprocessCrash
```

## Frontend modes

### Theme & mode accent system
Root element carries `data-theme="dark|light"` (toggled via `document.documentElement.setAttribute`) and `data-cat="asm|re|pwn|dbg|fw|hw"` (set by current mode). CSS rules key off `data-cat` to swap the `--accent` / `--accent-dim` tokens, which cascades to all mode-aware components.

### ASM mode (default)
3-column layout: ASM editor | registers+terminal | stack/memory/security panels.
Custom syntax-highlighted editor with breakpoint gutter, register pane with sub-register breakdown, xterm.js terminal. State managed by `hooks/useAnvilSession.ts` (GDB lifecycle, breakpoints, stepping, register/memory snapshots).

### Pwn mode
Split layout: topbar (binary loader + checksec badges + tool buttons) → side-by-side editors (Source viewer + exploit.py Monaco) → bottom panel (Terminal/Symbols/GOT/PLT/Strings tabs).

Key components:
- `PwnMode.tsx` — main layout with resizable panels (col + row resize handles)
- `PwnEditor.tsx` — Monaco editor for Python with `anvil-dark` theme and pwntools autocompletion
- `SourceViewer.tsx` — read-only Monaco with vulnerability pattern detection (gets/sprintf/strcpy/system highlighted)
- `editor/pwnCompletions.ts` — ~150 completion items (pwntools API + Python stdlib + exploit templates)
- `hooks/usePwnSession.ts` — session hook: load binary (auto-compile if source), fetch checksec/symbols/GOT/PLT

Pipeline: drop source (.c/.cpp/.rs/.go/.asm) → auto-compile via backend → load ELF → analyze → display.

### Shared components
- `AnvilTerminal.tsx` — xterm.js terminal (used by ASM and Pwn modes)
- `hooks/useColResize.ts` — column resize hook (2 or 3 column modes)
- `api/client.ts` — typed REST client wrapping fetch

## API Routes

| Router | Prefix | Bridge | Key endpoints |
|--------|--------|--------|---------------|
| sessions | /api/sessions | all | CRUD sessions |
| gdb | /api/gdb/{session_id} | pygdbmi | load, run, step (into/over/out/back), record, breakpoints, registers, memory, disassembly, current-line |
| rizin | /api/re/{session_id} | rzpipe | analyze, functions, disasm, strings, imports, xrefs, decompile, emulate |
| compile | /api/compile/{session_id} | nasm/gcc/ld | write/read source, compile ASM/C, checksec, readelf, objdump |
| pwn | /api/pwn/{session_id} | pwntools | cyclic, shellcraft, ROP, format string, ELF analysis, encoding |
| firmware | /api/firmware/{session_id} | binwalk | scan, extract, entropy, strings, arch detection |
| protocol | /api/protocol/{session_id} | pymodbus | Modbus TCP/UDP/Serial/TLS read/write, device ID, diagnostics |
| health | /api/health | - | status, detailed tool check, tools by mode |

## Conventions

- **CSS**: pure CSS with `anvil-` prefix, design tokens via CSS custom properties (`--space-*` for spacing, `--cat-*` for mode accents, `--font-*` for typography). No CSS-in-JS, no Tailwind.
- **React**: functional components only, props via `interface XxxProps`. API calls go through `src/api/client.ts` (single typed `request<T>()` wrapper).
- **Python**: type hints everywhere, Pydantic v2 for all request/response models. `from __future__ import annotations` at the top of every module. Imports ordered stdlib → third-party → local (ruff `I`).
- **Bridges**: thin wrappers on tools — no extra abstraction
- **Rust**: shell only — no business logic
- **Sanitization**: mandatory in all bridges via `core/sanitization.py`
- **Rate limiting**: 120 req/min via slowapi + SlowAPIMiddleware
- **Config**: via env vars with `ANVIL_` prefix (see `core/config.py`)
- **Testing**: MockBridge in conftest.py — tests never depend on real tools (gdb, rizin, etc.)
- **Cache**: ELF/ROP caches bounded at 50 entries with LRU eviction

## Backend dependencies

Core deps are always installed. Optional tool groups in pyproject.toml:
- `dev`: pytest, pytest-asyncio, httpx, ruff, bandit
- `re`: rzpipe
- `pwn`: pwntools
- `firmware`: binwalk
- `protocols`: pymodbus

```bash
pip install -e backend/                    # core only (use this when adding deps to pyproject.toml)
pip install -e "backend/[dev]"             # + test/lint (pytest, ruff, bandit)
pip install -e "backend/[dev,re,pwn,firmware,protocols]"  # everything
```

ADR-019: `pyproject.toml` is the **single** source of truth — `requirements.txt` was removed
in Sprint 16 to eliminate version drift.

## CI

GitHub Actions (`.github/workflows/ci.yml`) on push to main/develop and PRs to main:
1. **Lint**: ruff check + bandit scan (skips B101/B603/B607 intentionally)
2. **Test**: `pip install -e .[dev]` then `pytest ../tests/ -v`
