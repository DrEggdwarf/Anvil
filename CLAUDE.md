# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Anvil

Toolkit de securite bas niveau integre : ASM, Reverse Engineering, Exploitation, Debug, Firmware, Protocoles ICS/OT. Desktop app combining Ghidra + pwntools + pwndbg + binwalk capabilities.

## Stack

| Layer | Tech | Role |
|-------|------|------|
| Shell | Tauri v2 (Rust) | Desktop app, IPC, spawns backend subprocess |
| Frontend | React 19 + TypeScript 5 + Vite 7 | UI with 6 modes (ASM, RE, Pwn, Debug, Firmware, Protocols) |
| Backend | FastAPI + Python 3.12 | REST/WebSocket API, 6 tool bridges, security layers |

## Commands

```bash
# Frontend dev (port 1420)
npm run dev

# Full desktop dev (Tauri + frontend + backend)
npm run tauri dev

# Build desktop app
npm run tauri build

# Backend standalone
cd backend && uvicorn app.main:app --reload --port 8000

# Run all Python tests
cd backend && pytest ../tests/ -v

# Run a single test file
cd backend && pytest ../tests/test_gdb_bridge.py -v

# Run a single test by name
cd backend && pytest ../tests/test_gdb_bridge.py -k "test_load_binary" -v

# Run with coverage
cd backend && pytest ../tests/ --cov=app --cov-report=term-missing

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
src/               React UI (skeleton — ~50 LOC, mode switcher only)
backend/app/       FastAPI: main.py → 8 routers, core/, bridges/, models/, sessions/
tests/             24 pytest modules, all use MockBridge (no real tools needed in CI)
ai/                12 Claude Code agents + 2 workflows (see ai/README.md)
```

### How the layers connect

- **Tauri spawns FastAPI** as a child process on port 8000 at app start, kills it on exit. Tauri itself is a thin shell — no business logic in Rust.
- **Frontend talks to backend** via REST (simple requests) and WebSocket (`/ws/{session_type}/{session_id}`) for streaming (debug stepping, console output).
- **Tauri IPC** is only used for native features: file dialogs, serial port, health/dependency checks.

### Session-based isolation

Every API interaction goes through sessions. A session owns one bridge instance (GDB, rizin, pwntools, etc.) and one workspace directory (`~/.anvil/workspaces/{session_id}/`). Sessions auto-expire after 1 hour via a background cleanup loop (60s interval). Max 10 concurrent sessions.

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

- **CSS**: pure CSS with `anvil-` prefix, design tokens via CSS custom properties
- **React**: functional components only
- **Python**: type hints everywhere, Pydantic v2 for all request/response models
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
pip install -e backend/          # core only
pip install -e "backend/[dev]"   # + test/lint tools
```

## CI

GitHub Actions (`.github/workflows/ci.yml`) on push to main/develop and PRs to main:
1. **Lint**: ruff check + bandit scan (skips B101/B603/B607 intentionally)
2. **Test**: `pip install -e .[dev]` then `pytest ../tests/ -v`
