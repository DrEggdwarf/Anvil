# Anvil — Agent Instructions

Low-level security toolkit: ASM, Reverse Engineering, Exploitation, Debug, Firmware, ICS/OT Protocols.
Desktop app (Tauri v2) with React frontend and FastAPI backend wrapping 6 tool bridges.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `npm run dev` | Frontend dev server (port 1420) |
| `npm run tauri dev` | Full desktop dev (Tauri + frontend + backend) |
| `cd backend && uvicorn app.main:app --reload --port 8000` | Backend standalone |
| `cd backend && pytest ../tests/ -v` | Run all 637 Python tests |
| `cd backend && pytest ../tests/test_gdb_bridge.py -k "test_load"` | Single test |
| `npx vitest` | Frontend tests |
| `ruff check backend/ tests/` | Python lint |
| `bandit -r backend/ -c backend/pyproject.toml` | Security scan |

pytest asyncio_mode is `"auto"` — no `@pytest.mark.asyncio` needed.

## Architecture

See [CLAUDE.md](CLAUDE.md) for full architecture details, bridge pattern, security layers, and error hierarchy.

```
src-tauri/src/     Rust shell (thin — no business logic, just IPC + subprocess spawn)
src/               React 19 + TypeScript 5 — 6-mode UI: ASM (3-col debug), Pwn (split editors+terminal)
backend/app/       FastAPI — main.py → 8 routers, core/, bridges/, models/, sessions/
tests/             pytest modules — all use MockBridge (no real tools needed)
```

### Key patterns

- **Sessions**: every API call scoped to a `session_id` (16 hex chars). Session owns one bridge + workspace dir.
- **Bridges**: subclass `BaseBridge`, implement `start/stop/health/execute`, register via `bridge_registry`.
- **WebSocket**: single endpoint `/ws/{session_type}/{session_id}`, typed `WSMessage`, handlers registered by command name.
- **Frontend state**: `useAnvilSession()` hook manages GDB lifecycle; `usePwnSession()` manages Pwn mode; mode system via `data-cat` attribute.
- **Pwn pipeline**: drop source file → auto-compile backend → load ELF → checksec/symbols/GOT/PLT → side-by-side editors (SourceViewer + PwnEditor) + bottom panel (Terminal/data tabs).

## Conventions

### Python (backend)
- Type hints on everything, Pydantic v2 `Field(...)` with `max_length`/`ge`/`le` on **all** request fields
- Input sanitization mandatory in bridges (`core/sanitization.py`)
- Tests use `MockBridge` from `conftest.py` — never depend on real tools (gdb, rizin, etc.)
- `from __future__ import annotations` in every file
- Imports: stdlib → third-party → local (ruff I001)

### React / TypeScript (frontend)
- Functional components only, props via `interface XxxProps`
- Pure CSS with `anvil-` prefix — no CSS-in-JS, no Tailwind
- Design tokens via CSS custom properties (`--space-*`, `--cat-*`, `--font-*`)
- Theme: `data-theme="dark|light"` on root, mode accent via `data-cat="asm|re|pwn|dbg|fw|hw"`
- API calls through `src/api/client.ts` — single typed `request<T>()` wrapper

### Rust (src-tauri)
- Shell only — no business logic. Only IPC commands: `check_backend`, `check_dependencies`

## Backend dependencies

```bash
pip install -e backend/          # core only
pip install -e "backend/[dev]"   # + test/lint (pytest, ruff, bandit)
```

Optional groups: `re` (rzpipe), `pwn` (pwntools), `firmware` (binwalk), `protocols` (pymodbus).

## CI

GitHub Actions on push/PR to main: ruff → bandit → pytest. See [.github/workflows/ci.yml](.github/workflows/ci.yml).
