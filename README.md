# Anvil — Low-Level Security Toolkit

> Le Burp Suite du bas niveau — GDB, rizin, pwntools, binwalk dans une seule app.

Toolkit de sécurité bas niveau intégré : ASM, Pwn, Reverse Engineering, Firmware, Wire (ICS/OT).

## Stack

| Couche | Technologie | Rôle |
|--------|-------------|------|
| Shell | Tauri v2 (Rust) | Desktop app, IPC, file dialogs, serial port |
| Frontend | React 19 + TypeScript 5 + Vite 7 | UI, composants, panels, éditeur |
| Backend | FastAPI + Python 3.12 | API WebSocket/REST, bridges outils |

## Architecture

```
src-tauri/ (Rust)  → Shell : IPC, subprocess, file dialogs, serial, packaging
src/ (React/TS)    → UI : composants, panels, éditeur, 5 modules
backend/ (Python)  → Logique : FastAPI, bridges, sanitization, rate limiting
anvil_mcp/         → Serveur MCP standalone (Claude Desktop / Cursor)
ai/                → Système multi-agent (12 agents, 2 workflows)
tests/             → Tests Python (pytest, ~736 tests) + vitest (27) + e2e Playwright (31)
.github/           → CI GitHub Actions (5 jobs : lint, test, smoke, audit, e2e)
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

# Backend (pyproject.toml est la source de vérité — ADR-019)
pip install -e "backend/[dev]"                              # core + dev/test
pip install -e "backend/[dev,re,pwn,firmware,protocols]"   # full toolchain
```

## Développement

```bash
# Frontend seul
npm run dev

# Tauri (frontend + Rust shell)
npm run tauri dev

# Backend (toujours depuis la racine — imports via `from backend.app.X`)
uvicorn backend.app.main:app --reload --port 8000

# Vérification complète avant push (= CI locale exacte)
make check

# Tests Python (~736 tests)
python -m pytest tests/ -v --tb=short

# Lint
ruff check backend/ tests/ anvil_mcp/
bandit -r backend/ -c backend/pyproject.toml
npx tsc --noEmit
cargo check --manifest-path src-tauri/Cargo.toml
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
# Vérification complète (lint + tests + audits)
make check

# Python pytest (~736 tests)
python -m pytest tests/ -v

# Avec coverage
python -m pytest tests/ --cov=backend/app --cov-report=term-missing

# Un fichier
python -m pytest tests/test_rizin_bridge.py -v

# Frontend
npx vitest

# E2E Playwright
npx playwright test
```

## CI

5 jobs GitHub Actions sur push/PR vers main :

| Job | Contenu | Bloquant |
|-----|---------|----------|
| `lint` | ruff check+format, bandit, `anvil_mcp/` inclus | ✅ oui |
| `test` | pytest (~736) + vitest (27) | ✅ oui |
| `smoke` | backend live + 5 checks ADR-016 | ✅ oui |
| `audit` | pip-audit + npm audit + cargo audit | ⚠ non (continue-on-error) |
| `e2e` | Playwright 31 specs | ⚠ non (continue-on-error) |

## IDE recommandé

- [VS Code](https://code.visualstudio.com/) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)
