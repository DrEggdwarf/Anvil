# Anvil — Low-Level Security Toolkit

> Ghidra + pwntools + pwndbg + binwalk — dans une seule app.

Toolkit de sécurité bas niveau intégré : ASM, Reverse Engineering, Exploitation, Debug, Firmware, Protocoles ICS/OT.

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
tests/             → Tests Python (pytest, ~664 tests sur 24 modules)
.github/           → CI GitHub Actions (ruff, bandit, pytest)
```

## Prérequis

- **Node.js** >= 18 + npm
- **Python** >= 3.12 + pip
- **Rust** (pour Tauri) — `rustup`
- **Outils optionnels** : gdb, nasm, gcc, ld, rizin, binwalk

## Installation

```bash
# Frontend
npm install

# Backend (pyproject.toml is the single source of truth — ADR-019)
pip install -e "backend/[dev]"                              # core + dev/test
pip install -e "backend/[dev,re,pwn,firmware,protocols]"   # full toolchain
```

## Développement

```bash
# Frontend seul
npm run dev

# Tauri (frontend + Rust shell)
npm run tauri dev

# Backend (always from repo root — imports use `from backend.app.X`)
uvicorn backend.app.main:app --reload --port 8000

# Tests Python (~664 tests)
python -m pytest tests/ -v --tb=short

# Lint
npx tsc --noEmit
cargo check --manifest-path src-tauri/Cargo.toml
ruff check backend/ tests/
bandit -r backend/ -c backend/pyproject.toml
```

## API Bridges

| Bridge | Outil | Routes | Méthodes |
|--------|-------|--------|----------|
| GDB | pygdbmi | `/api/gdb/{session_id}/*` (~40 routes) | ~45 commandes GDB/MI |
| Rizin | rzpipe | `/api/re/{session_id}/*` (~70 routes) | ~50 méthodes RE |
| Compilation | nasm/gcc/ld | `/api/compile/{session_id}/*` (~20 routes) | ASM + C compilation |
| Binary Analysis | readelf/nm/objdump/ldd | `/api/compile/{session_id}/*` (~15 routes) | ELF analysis complète |
| Pwn | pwntools | `/api/pwn/{session_id}/*` (~40 routes) | ROP, fmtstr, shellcraft, ELF |
| Firmware | binwalk v2/v3 | `/api/firmware/{session_id}/*` (~20 routes) | Scan, extract, entropy |
| Protocols | pymodbus | `/api/protocol/{session_id}/*` (~40 routes) | Modbus TCP/UDP/Serial/TLS |

## Communication

- **Frontend ↔ Backend** : WebSocket (localhost:8000) pour le streaming + REST pour les requêtes simples
- **Tauri ↔ Frontend** : IPC invoke (file dialogs, serial port, dependency check)

## Tests

```bash
# Full suite (~664 tests)
python -m pytest tests/ -v

# Avec coverage
python -m pytest tests/ --cov=backend/app --cov-report=term-missing

# Un fichier
python -m pytest tests/test_rizin_bridge.py -v
```

## IDE recommandé

- [VS Code](https://code.visualstudio.com/) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)
