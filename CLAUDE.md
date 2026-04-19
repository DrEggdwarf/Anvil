# Anvil — Low-Level Security Toolkit

## Description

Toolkit de sécurité bas niveau intégré : ASM, Reverse Engineering, Exploitation, Debug, Firmware, Protocoles ICS/OT.

"Ghidra + pwntools + pwndbg + binwalk — dans une seule app."

## Stack

| Couche | Technologie | Rôle |
|--------|-------------|------|
| Shell | Tauri v2 (Rust) | Desktop app, IPC, file dialogs, serial port |
| Frontend | React 19 + TypeScript 5 + Vite 7 | UI, composants, panels, éditeur |
| Backend | FastAPI + Python 3.12 | API WebSocket/REST, bridges outils |

## Architecture

```
src-tauri/ (Rust)  → Shell : IPC, subprocess, file dialogs, serial, packaging
src/ (React/TS)    → UI : composants, panels, éditeur, 6 modes
backend/ (Python)  → Logique : FastAPI, 6 bridges, sanitization, rate limiting
ai/                → Système multi-agent (12 agents, 2 workflows)
tests/             → Tests Python (pytest, 637 tests)
.github/           → CI GitHub Actions (ruff, bandit, pytest)
```

## Bridges (Phase 0 complète ✅)

| Bridge | Outil | Méthodes | Routes REST |
|--------|-------|----------|-------------|
| GDB | pygdbmi | ~45 | /api/gdb/* (~40) |
| Rizin | rzpipe | ~50 | /api/re/* (~70) |
| Compilation | nasm/gcc/ld | ~20 | /api/compile/* (~20) |
| Pwn | pwntools | ~40 | /api/pwn/* (~40) |
| Firmware | binwalk v2/v3 | ~20 | /api/firmware/* (~20) |
| Protocols | pymodbus | ~40 | /api/protocol/* (~40) |

## Commands

```bash
# Dev frontend
npm run dev

# Dev Tauri (frontend + Rust shell)
npm run tauri dev

# Build desktop
npm run tauri build

# Backend
cd backend && uvicorn app.main:app --reload --port 8000

# Tests Python
cd backend && pytest ../tests/

# Tests Frontend
npx vitest

# Lint + sécurité
npx tsc --noEmit
cargo check --manifest-path src-tauri/Cargo.toml
ruff check backend/ tests/
bandit -r backend/ -c backend/pyproject.toml
```

## Communication

- Frontend ↔ Backend : WebSocket (localhost:8000) pour le streaming (debug, console) + REST pour les requêtes simples
- Tauri ↔ Frontend : IPC invoke (file dialogs, serial port, dependency check)

## Conventions

- CSS pure avec prefix `anvil-`, design tokens via CSS custom properties
- Composants fonctionnels React uniquement
- Type hints Python systématiques, Pydantic v2 pour la validation (max_length sur tous les champs string)
- Bridges Python = wrappers fins sur les outils (pygdbmi, rzpipe, pwntools)
- Pas de logique métier en Rust — c'est un shell
- Input sanitization obligatoire dans les bridges (core/sanitization.py)
- Rate limiting global via slowapi + SlowAPIMiddleware (120 req/min)
- Subprocess limité à 20 concurrents (sémaphore asyncio)
- Workspace par session : ~/.anvil/workspaces/{session_id}/
- Session ID validé (hex 16 chars) dans SessionManager.get()/destroy()
- Pydantic Field constraints sur tous les champs request (max_length, ge/le, max_length sur listes)
- Cache ELF/ROP borné (max 50 entries, eviction LRU)

## AI Multi-Agent System

12 agents (pm, architect, rust, backend, frontend, devops, security, testing, quality, performance, a11y, pentester).
Voir `ai/README.md` pour le fonctionnement complet.
