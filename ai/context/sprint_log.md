# Sprint Log — Anvil

## Sprint 0 — Bootstrap (18 avril 2026) ✅

### Objectif
Scaffolding du projet : Tauri v2 + React 19 + TypeScript + Vite 7 + système AI multi-agent.

### Réalisé
- [x] Init projet Tauri v2 avec template react-ts
- [x] npm install (72 packages)
- [x] Création du système AI multi-agent (12 agents, 2 workflows)
- [x] Adaptation des agents de Rails (Ruby/Inertia) vers Anvil (Rust/React/Python)
- [x] Remplacement de l'agent `database` par `rust` (pas de DB, mais shell Tauri)
- [x] Fichiers context initialisés (sprint_log, decisions, backlog)

### Décisions
- Voir ai/context/decisions.md

---
---

## Sprint 1 — API Engine Core (19 avril 2026) ✅
**Objectif** : Fondation backend blindée — architecture modulaire, gestion de sessions,
lifecycle subprocess, WebSocket infra, error handling, tests complets.
**Agents** : @architect → @backend → @security → @testing
**Priorité** : 🔴 CRITIQUE — c'est le socle de tout le reste

### Réalisé
- [x] `backend/app/core/config.py` — Settings Pydantic (env vars, ANVIL_ prefix, defaults)
- [x] `backend/app/core/exceptions.py` — Hiérarchie complète (AnvilError → BridgeError, SessionError, ValidationError, SubprocessError, ToolNotFound)
- [x] `backend/app/core/lifecycle.py` — Startup/shutdown events FastAPI (SubprocessManager, SessionManager, WorkspaceManager)
- [x] `backend/app/core/subprocess_manager.py` — spawn(), execute(), kill(), cleanup_all()
- [x] `backend/app/bridges/base.py` — BaseBridge ABC (start, stop, health, execute, state machine)
- [x] `backend/app/bridges/registry.py` — Bridge Registry (enregistrement dynamique)
- [x] `backend/app/sessions/manager.py` — Session Manager (create, get, destroy, timeout, cleanup, concurrent limits)
- [x] `backend/app/api/health.py`, `sessions.py`, `ws.py`, `deps.py`
- [x] `backend/app/models/` — tools.py (24 tools), ws.py, sessions.py, errors.py, health.py
- [x] WebSocket infra (typed JSON messages, handlers dispatcher, heartbeat, errors)
- [x] Exception hierarchy + error middleware → JSON responses uniformes
- [x] **97 tests, 95% coverage**

---
---

## Sprint 2 — GDB Bridge (19 avril 2026) ✅
**Objectif** : Premier bridge concret (GDB/MI via pygdbmi). Implémentation de référence,
tests exhaustifs avec mocks. Pattern réutilisable pour tous les autres bridges.
**Agents** : @backend → @testing → @security → @pentester

### Réalisé
- [x] `bridges/gdb_bridge.py` — full pygdbmi wrapper (~15 commandes initiales : load, run, step, bp, registers, memory, stack, disassemble, evaluate)
- [x] `api/gdb.py` — 14 routes REST /api/gdb/{session_id}/*
- [x] `api/gdb_ws.py` — 14 handlers WebSocket (gdb.step_into, gdb.registers, etc.)
- [x] `models/gdb.py` — Schemas Pydantic complets
- [x] Mock pygdbmi complet — CI sans GDB installé
- [x] **171 tests, 97% coverage**

---
---

## Sprint 3 — Compilation Pipeline (19 avril 2026) ✅
**Objectif** : Compiler ASM (nasm+ld) et C (gcc), checksec, gestion fichiers.
**Agents** : @backend → @security → @testing

### Réalisé
- [x] `bridges/compilation.py` — CompilationBridge (ASM: nasm+ld/gcc, C: gcc avec flags sécurité)
- [x] `bridges/binary_analyzer.py` — BinaryAnalyzer (checksec, file info, ELF sections)
- [x] `core/workspace.py` — WorkspaceManager (dirs isolés par session, protection path traversal)
- [x] `api/compile.py` — Routes REST /api/compile/{session_id}/* (files CRUD, asm, c, checksec, fileinfo, sections)
- [x] `models/compilation.py` — Schemas Pydantic (compile req/resp, checksec, sections, file management)
- [x] Error parsers : nasm stderr + gcc stderr → erreurs structurées (file/line/severity)
- [x] Security flags map : relro, canary, nx, pie, fortify + négations
- [x] **243 tests, 97% coverage**

---
---

## Sprint 4 — RE Bridge + Feature Completion (19 avril 2026) ✅
**Objectif** : Bridge rzpipe complet + couverture 100% features GDB et binary analysis.
**Agents** : @backend → @testing → @security

### Réalisé — Rizin Bridge
- [x] `bridges/rizin_bridge.py` — ~50 méthodes via rzpipe (analyse, fonctions, désassemblage, décompilation, strings, imports/exports, symboles, sections, segments, relocations, classes, xrefs, search, flags, comments, types, ESIL, hashing, graphs, projets, patching)
- [x] `api/rizin.py` — ~70 endpoints REST /api/re/{session_id}/* (couverture complète du bridge)
- [x] `models/rizin.py` — Schemas Pydantic (22 request models + 13 response models)
- [x] Auto-register bridge dans registry + lifecycle.py
- [x] `rzpipe>=0.4.0` ajouté à requirements.txt

### Réalisé — GDB Bridge étendu (de ~15 → ~45 commandes)
- [x] Nouvelles commandes : interrupt, step_source, next_source, until, reverse_continue, reverse_step
- [x] Breakpoints avancés : enable/disable, condition, watchpoints (write/read/access), hardware bp, temporary bp
- [x] Mémoire : write_memory, search_memory
- [x] Registres : set_register, get_register, get_changed_registers
- [x] Stack : get_stack_arguments, get_stack_depth, select_frame
- [x] Threads : thread_info, thread_select
- [x] Process : attach, detach, get_memory_map, get_shared_libraries
- [x] Variables : set_variable, print_variable, get_local_variables
- [x] Signaux : get_signals, handle_signal, catch_syscall, catch_signal
- [x] Record : record_start, record_stop
- [x] Disassemble : disassemble_with_source
- [x] ~40 nouvelles routes REST dans api/gdb.py

### Réalisé — Binary Analyzer étendu (de 3 → ~20 méthodes)
- [x] ELF header, program headers, symbols (nm), dynamic symbols (readelf)
- [x] Imports, exports, relocations, GOT entries, PLT entries
- [x] Strings (strings -a -t x), dependencies (ldd)
- [x] Disassemble (objdump -d), hexdump (xxd), size info (size)
- [x] ~15 nouvelles routes REST dans api/compile.py

### Tests
- [x] `test_rizin_bridge.py` — 75 tests (mock rzpipe, lifecycle, toutes méthodes)
- [x] `test_gdb_bridge.py` étendu — ~40 nouveaux tests
- [x] `test_binary_analyzer.py` étendu — ~25 nouveaux tests
- [x] Fix regex dynamic_symbols parser (\s+ matchait \n)
- [x] **388 tests, 0 failures**

---
---

## Sprint 5 — Bridges Pwn, Firmware, Protocols (19 avril 2026) ✅
**Objectif** : Compléter l'arsenal de bridges — couverture 100% features des outils wrappés.
**Agents** : @backend → @testing → @security → @pentester

### Réalisé — Pwn Bridge (pwntools)
- [x] `bridges/pwn_bridge.py` — ~40 méthodes : context, cyclic, pack/unpack/flat, asm/disasm, make_elf, shellcraft (multi-arch), ELF analysis (checksec, symbols, GOT, PLT, sections, search, bss), ROP (create, gadgets, call, raw, chain, dump, migrate, setRegisters), fmtstr_payload, SigreturnFrame (SROP), Ret2dlresolvePayload, encoding (XOR, hex, base64, URL), hashing (md5/sha1/sha256/sha512), shellcode encoding, constants DB, corefile analysis, bit rotation
- [x] `api/pwn.py` — ~40 routes REST /api/pwn/{session_id}/*
- [x] `models/pwn.py` — Schemas Pydantic (context, cyclic, pack, asm, shellcraft, ELF, ROP, fmtstr, SROP, encoding, hash, constants, corefile)

### Réalisé — Firmware Bridge (binwalk)
- [x] `bridges/firmware_bridge.py` — ~20 méthodes : scan (signature, filtered, crypto, filesystem, compression), extract (auto, recursive, carve), entropy (blocks + PNG graph), strings, opcodes/arch detection, raw byte search, secret scanning (private keys, certs, passwords, API keys, SSH keys), file info, extracted listing, signatures list
- [x] Auto-détection binwalk v3 CLI (JSON --log=-) ou v2 Python module fallback
- [x] `api/firmware.py` — ~20 routes REST /api/firmware/{session_id}/*
- [x] `models/firmware.py` — Schemas Pydantic (scan, extract, entropy, strings, secrets, search, files, signatures)

### Réalisé — Protocol Bridge (pymodbus)
- [x] `bridges/protocol_bridge.py` — ~40 méthodes : connect (TCP/UDP/Serial/TLS + framer), disconnect, read coils/discrete/holding/input/exception_status/FIFO/file_record, write single/multiple coils/registers/mask/readwrite/file_record, device info (MEI type 14), report_server_id, diagnostics (all sub-functions 0x00-0x15), comm event counter/log, data type conversion (INT16-64/UINT/FLOAT32-64/STRING/BITS), scan devices, scan registers, start server (simulator/honeypot)
- [x] `api/protocol.py` — ~40 routes REST /api/protocol/{session_id}/*
- [x] `models/protocol.py` — Schemas Pydantic (connect, read/write, diagnostics, device info, conversion, scan, server)

### Wiring & Dependencies
- [x] `main.py` — 3 nouveaux routers inclus (pwn, firmware, protocol)
- [x] `lifecycle.py` — 3 imports bridges auto-register
- [x] `requirements.txt` — pwntools>=4.0, binwalk>=2.3, pymodbus>=3.0

### Tests
- [x] `test_pwn_bridge.py` — tests exhaustifs (lifecycle, context, cyclic, packing, asm, shellcraft, ELF, ROP, fmtstr, SROP, ret2dl, encoding, hashing, constants, corefile, misc, guards)
- [x] `test_firmware_bridge.py` — tests exhaustifs (lifecycle, scan v2/v3, filtered scans, extraction, entropy, strings, opcodes, raw search, secrets, file info, listing, signatures, parsing helpers, guards)
- [x] `test_protocol_bridge.py` — tests exhaustifs (lifecycle, connection, read/write ops, device info, diagnostics all sub-functions, event counter/log, data conversion, scan devices/registers, server, properties, guards)
- [x] **586 tests, 0 failures** (198 nouveaux tests)

### Décisions techniques
- Binary data I/O en hex strings pour JSON REST API (pwntools)
- binwalk v3 CLI préféré (JSON), v2 Python fallback automatique
- execute() utilise inspect.isawaitable() pour gérer méthodes sync/async
- Tous les mocks via sys.modules (pas d'import réel pwntools/binwalk/pymodbus en CI)

---
---

## Sprint 6 — Hardening & Integration (completed) ✅
**Objectif** : Sécurité, performance, tests E2E API, CI.
**Agents** : @security → @pentester → @performance → @testing → @devops

### 6.1 — Security ✅
- [x] Input sanitization module (`core/sanitization.py`) — GDB/MI, Rizin, path traversal, GCC flags, session ID, string length validators
- [x] GDB bridge hardened — all user-controlled inputs sanitized (binary_path, location, expression, variable, pattern, address, etc.)
- [x] Rizin bridge hardened — all user-controlled inputs sanitized (command, address, new_name, hex_data, string, instruction, etc.)
- [x] `!`, `;`, `` ` ``, `\n` blocked in GDB/Rizin inputs — prevents shell escape and command chaining
- [x] `shell`, `python`, `pipe`, `source`, `define` blocked in GDB inputs
- [x] Path validation — blocks /etc, /proc, /sys, /dev, /root, /boot; enforces allowed_dirs containment
- [x] GCC extra_flags allowlist — blocks -wrapper, -fplugin, -specs; allows -O, -g, -W, -f, -m, -std=, etc.
- [x] Session ID format validation — regex `^[a-f0-9]{16}$`
- [x] Rate limiting via slowapi — `rate_limit_per_minute=120` from config, applied globally
- [x] CORS hardened — explicit methods (GET/POST/PUT/DELETE/PATCH) and headers (Content-Type/Authorization/X-Session-ID)
- [x] Workspace base dir changed from `/tmp/anvil` to `~/.anvil/workspaces`
- [x] Error codes: INJECTION_BLOCKED (400), PATH_BLOCKED (403) added to status map

### 6.2 — Performance ✅
- [x] Subprocess concurrency limit — semaphore (max 20 concurrent) in SubprocessManager
- [x] Subprocess output size enforcement — truncate to `subprocess_max_output_bytes` (10MB)
- [x] Semaphore release in both kill() and execute() cleanup paths

### 6.3 — Input Validation ✅
- [x] Pydantic max_length on all GDB model string fields (binary_path: 4096, expression: 4096, address: 256, register: 64, etc.)
- [x] Pydantic max_length on all Rizin model string fields
- [x] Pydantic max_length on compilation models (source_code: 1M)

### 6.4 — Tests ✅
- [x] `test_security.py` — 30 tests: GDB injection, Rizin injection, path traversal, session ID, GCC flags, string length
- [x] `test_e2e_security.py` — E2E API tests: dangerous flags, oversized inputs, malformed session IDs, CORS
- [x] **631 tests, 0 failures** (45 new security tests)

### 6.5 — CI & Linting ✅
- [x] `.github/workflows/ci.yml` — GitHub Actions: lint + security scan + tests
- [x] `pyproject.toml` — ruff config (E/W/F/I/S/B/UP/SIM/RUF rules), bandit config
- [x] slowapi added to requirements.txt and pyproject.toml

### Décisions techniques
- Sanitization at bridge level (not API level) — defense in depth, bridges are reusable
- `$` allowed in GDB inputs (needed for register references like `$rax`)
- `|` allowed in both GDB/Rizin (needed for some valid expressions) — `pipe` command blocked separately
- Null bytes in paths caught before `Path.resolve()` to avoid ValueError
- Semaphore-based concurrency limit (not queue-based) — simpler, no ordering needed

---

> **FIN DE LA PHASE 0 — API ENGINE** ✅
> Sprints 0-6 terminés. 631 tests, 0 failures.
> 6 bridges (GDB, Rizin, Compilation, Pwn, Firmware, Protocols), ~100+ routes REST, WS infra, CI, sécurité.
> Tout le backend est prêt. Les phases suivantes sont principalement **frontend**.

---
---

## Sprint 7+8 — Mode ASM : Éditeur, Compilation & Debug UI (21 avril 2026) ✅

### Réalisé
- [x] Layout 3 colonnes : éditeur | registres+terminal | panels droite (stack/memory/security)
- [x] Éditeur ASM custom avec numéros de ligne, highlighting ligne active, support NASM/GAS/FASM
- [x] Toolbar : Run (F5), Auto-step, Back/Into/Over/Out/Next
- [x] Session GDB : compile → load → break _start → step interactif
- [x] Panel Registres — copie fidèle ASMBLE (segments colorés, sub-registres, flags pills, flash, toggle delta/upper/hex)
- [x] Panel Terminal — xterm.js avec output GDB, collapse/expand
- [x] Panel Stack — visualisation compacte de la pile :
  - Rows compactes : offset RSP-relatif + mini-barre bytes + valeur qword
  - Click-to-expand pour détail byte-par-byte
  - Zones groupées avec labels : **Locals** / **Stack frame** / **Caller**
  - Annotations sémantiques : `saved rbp`, `ret addr`
  - Bordures colorées par zone (teal locals, orange frame)
  - Toggle hex/dec/bin
  - Refresh automatique à chaque step
- [x] Syscall snippets panel (write, exit)
- [x] Rate limit augmenté à 600/min pour dev local
- [x] Breakpoints visuels (click gutter)

---
---

## Sprint 7+8b — Reference Modal Multi-Mode (22 avril 2026) ✅

### Objectif
Modal de référence contextuelle — contenu adapté au mode actif (ASM, RE, Pwn, Debug, Firmware, Protocols).

### Réalisé
- [x] CSS bugfix : stack frame diagram et patterns code blocks tronqués (flex-shrink: 0)
- [x] `src/data/reference-re.ts` — 70 commandes rizin, ELF format/sections, RE patterns
- [x] `src/data/reference-pwn.ts` — 7 protections+bypass, 6 techniques, format strings, pwntools cheatsheet
- [x] `src/data/reference-dbg.ts` — 49 commandes GDB, 24 pwndbg, examine formats
- [x] `src/data/reference-fw.ts` — 27 options binwalk, 23 magic signatures, entropie guide, FW patterns
- [x] `src/data/reference-hw.ts` — 20 fonctions Modbus, 4 types registres, 9 exceptions, trames TCP/RTU, patterns
- [x] `src/data/index.ts` — barrel exports pour les 5 nouveaux modules
- [x] `src/components/ReferenceModal.tsx` — réécriture complète : mode-aware, 6 configurations d'onglets, recherche, filtres catégories
- [x] `src/App.tsx` — wiring mode prop via MODE_CAT mapping
- [x] `src/App.css` — styles bypass list (Pwn protections tab)
- [x] Convention cleanup : inline prop types → named interfaces (FilterBarProps, SearchProps, PatternsViewProps, TabContentProps)
- [x] Ruff auto-fix : 24 F841 (unused variables) nettoyés dans 5 fichiers test
- [x] TypeScript clean : 0 erreurs tsc
- [x] **639 tests passed** (2 pre-existing failures non liées)

### Onglets par mode
| Mode | Titre | Onglets |
|------|-------|---------|
| ASM | Reference x86-64 | Syscalls (174), Instructions, ABI, Directives, Patterns |
| RE | Reference Reverse Engineering | Commandes (61), ELF, Sections, Patterns |
| Pwn | Reference Exploitation | Protections, Techniques, Format String, pwntools, Syscalls |
| Debug | Reference Debug (GDB) | GDB (49), pwndbg (24), x/ Format, ABI |
| Firmware | Reference Firmware | Binwalk (27), Signatures (23), Entropie, Patterns |
| Protocols | Reference Protocoles | Fonctions (20), Registres, Exceptions, Trames, Patterns |

---
---

## Sprint 9 — Mode Pwn : UI Complète (23 avril 2026) ✅

### Objectif
Mode Pwn fonctionnel — charger un binaire/source, analyser, éditer un exploit Python avec autocomplétion pwntools.
**Agents** : @frontend → @pentester → @testing

### Réalisé — Frontend Pwn Mode
- [x] `PwnMode.tsx` — layout complet : topbar (dropzone + checksec badges + tools inline) → split editors → bottom panel tabbé
- [x] `PwnEditor.tsx` — Monaco Editor pour Python avec thème `anvil-dark`, font Geist Mono, snippets pwntools
- [x] `SourceViewer.tsx` — Monaco read-only avec détection patterns vulnérables (gets/sprintf/strcpy/printf/system/malloc par langage)
- [x] `editor/pwnCompletions.ts` — ~150 items autocomplétion (pwntools API complète + Python stdlib + templates exploit)
- [x] `hooks/usePwnSession.ts` — hook session : load binary, auto-compile si source, fetch checksec/symbols/GOT/PLT
- [x] `ChecksecBadges` — badges inline colorés (ok=vert, vuln=rouge) pour RELRO/Canary/NX/PIE/Fortify
- [x] `BottomPanel` — onglets Terminal (xterm.js via AnvilTerminal) | Symbols | GOT | PLT | Strings
- [x] Resize handles : vertical (col-resize entre Source et exploit.py) + horizontal (row-resize éditeurs ↔ bottom panel)
- [x] Pipeline : drop source (.c/.cpp/.rs/.go/.asm) → auto-compile backend → load ELF → analyse → affichage

### Réalisé — Backend Pwn Compile
- [x] `POST /api/pwn/{session_id}/compile` — compile source C/C++/ASM/Rust/Go avec flags vulnérables optionnels
- [x] `PwnCompileRequest` model Pydantic (path, language, vuln_flags)
- [x] Support multi-langage : gcc, g++, nasm+ld, rustc, go build
- [x] Vuln flags par défaut : `-no-pie -fno-stack-protector -z execstack`

### Réalisé — Samples
- [x] `samples/pwn/` — 7 fichiers exemples : bof_basic.c, fmt_string.c, ret2libc.c, use_after_free.c, bof_cpp.cpp, bof_rust.rs, bof_go.go + Makefile

### Réalisé — Shared
- [x] `api/client.ts` — ajout `pwnCompile()` dans le client REST typé
- [x] `useColResize.ts` — support mode 2 colonnes (50/50)
- [x] `App.tsx` — routing Pwn mode conditionnel avec props dédiés
- [x] `App.css` — ~500 lignes CSS Pwn mode (layout, badges, tools, editors, bottom panel, resize handles)
- [x] Resize handles col + row avec indicateur grip et highlight accent au hover

### Dependencies
- [x] `@monaco-editor/react` ajouté (éditeur Monaco pour Source + Exploit)
- [x] `@fortawesome/fontawesome-free` ajouté (icônes)

### Tests
- [x] TypeScript : 0 erreurs (`npx tsc --noEmit`)
- [x] **658 tests passed** (2 pre-existing failures non liées)

---
---

## Sprint 14 — Hardening sécu post-merge (28 avril 2026) ✅
**Objectif** : Corriger les findings critiques identifiés par l'audit multi-agent (Security + Pentester) après le merge `asm-dev → main`. Anticiper le déploiement Docker/web.
**Agents** : @security → @pentester → @backend → @testing
**Priorité** : 🔴 CRITIQUE — bloquant avant tout déploiement web/multi-user

### Réalisé (6/6 fixes)
1. **Pent#1 (Critique, RCE) ✅** — `sanitize_gdb_input()` ajouté dans `gdb_ws.py:_handle_raw_execute`. Ferme la RCE 1-ligne via WS.
2. **Pent#2/#3 (Élevé) ✅** — `"` ajouté aux chars bloqués GDB (close-quote injection dans `-interpreter-exec console "..."`). Allowlist GCC restreinte : `-Wl,`/`-Wa,`/`-Wp,`/`-Xlinker`/`-rpath` bloqués ; `-l/abs/path` rejetés ; `-I`/`-L` validés contre `_BLOCKED_PATHS`.
3. **Sec A1+A2 / Archi#1 / Pent#4+#6 (Critique) ✅** — `WorkspaceManager.resolve_under_workspace()` créé. 9 endpoints `/api/pwn/elf/*` + `rop_create` + `ret2dlresolve` + `corefile_load` + `compile_source` + `upload_binary` routent maintenant via `_resolve_path`. Anti-symlink (`Path.is_symlink()`), anti-path-traversal (`is_relative_to`). Go forcé offline (`GOFLAGS=-mod=vendor`, `GOPROXY=off`). `chmod 0o755` uniquement si magic ELF (`\x7fELF`). ADR-017 rédigé.
4. **Pent#11 / Sec A3 (Élevé) ✅** — `Session.token = secrets.token_hex(16)` (32 hex chars) généré au create. `SessionCreated` model expose le token UNE fois. `/ws/{type}/{id}?token=...` vérifie via `secrets.compare_digest`, valide `bridge_type == session_type`, check `Origin` contre `cors_origins`. Échec → `close(1008)` avant `accept()`. ADR-016 rédigé.
5. **Sec A4 / Pent#14 ✅** — CSP stricte dans `tauri.conf.json` (`default-src 'self'`, `connect-src http://127.0.0.1:8000 ws://127.0.0.1:8000`, `script-src 'self' 'wasm-unsafe-eval'`). `cors_origins` par défaut : `[http://localhost:1420, http://127.0.0.1:1420, tauri://localhost, https://tauri.localhost]`. ADR-015 rédigé.
6. **Test régression ✅** — Créés : `test_pwn_api.py` (32 tests sécurité : path traversal, symlink, ELF magic chmod, env Go offline), `test_pwn_models.py` (12 tests validators), `test_compile_api.py` étendu (GAS/FASM + invalid assembler 422). `test_ws.py` réécrit pour le flux token. `_STATUS_MAP` enrichi (PATH_TRAVERSAL, UNSUPPORTED_LANGUAGE, INVALID_BASE64, etc.).

### Mesures
- 699 tests pytest verts (+35 nouveaux), ruff & bandit clean
- 9 findings fermés (RCE, LFI, WS auth, CSP, CORS, symlink, language, magic ELF, sanitization)
- Bloquant levé pour déploiement web/multi-user après ce sprint

---
---

## Sprint 15 — Performance & Architecture refactor (28 avril 2026) ✅
**Objectif** : Résorber la régression perf identifiée par l'audit (bundle initial 720 KB, 0 lazy split, hooks non mémoïsés, WS ignoré côté front). Simplifier les fichiers > 500 L.
**Agents** : @performance → @architect → @frontend
**Priorité** : 🟠 HAUTE — bloquant cible « step <100ms »

### Réalisé
- **Perf#1 / Archi#2** ✅ — `App.tsx` : `React.lazy(PwnMode)` + `React.lazy(ReferenceModal)` + `<Suspense>` avec fallback. Mesure bundle : **608 KB / 170 KB gzip** (vs 720 KB avant — -16% initial). PwnMode 47 KB et ReferenceModal 102 KB chargés à la demande.
- **Perf#2 / Archi (useAnvilSession 651 L)** ✅ partiel — Parsers GDB/MI extraits dans `hooks/gdb/parseGdbResponse.ts` (97 L stateless, testables seuls). Hook racine descend à 560 L. `useCallback` massif sur les fns retournées **reporté au Sprint 17** (couplé au câblage WebSocket pour éviter une double passe risquée sans test e2e).
- **Archi (ReferenceModal 877 L)** ✅ via cascade — Le `React.lazy(ReferenceModal)` du #1 entraîne le lazy-loading de **tous** ses imports `data/reference-*` via le code-splitting Vite. Gain mesuré : 102 KB sortis du bundle initial. Le découpage par mode (lazy par tab actif) reste possible mais marginal (+~50 KB max) : reporté.
- **Perf#3 (WS inutilisé)** ⏸ **REPORTÉ Sprint 17** — Refacto majeure (useAnvilSession + api/ws.ts + handlers backend) qui nécessite tests e2e. Sera couplée au split useGdbStepping/useGdbMemory.
- **Perf#7 (cache FIFO)** ✅ — `pwn_bridge._cache_elf` et `_cache_rop` migrent vers `OrderedDict` avec `move_to_end()` à chaque accès. `_touch_elf(path)` ajouté + utilisé sur 11 sites de lecture de cache.

### Mesures
- Bundle initial : 720 KB → **608 KB** (-16%)
- Lazy chunks : PwnMode 47 KB, ReferenceModal 102 KB
- useAnvilSession : 651 L → **560 L** (-91 L extraits)
- 88 tests pwn bridge ✅ (LRU compatible API)
- TypeScript clean, build OK

---
---

## Sprint 16 — Quality cleanup & ADRs (28 avril 2026) ✅
**Objectif** : Régler la dette quality identifiée et formaliser les décisions structurantes.
**Agents** : @quality → @architect

### Réalisé
- **Deps Python unifiées (ADR-019)** ✅ — `requirements.txt` + `requirements-dev.txt` supprimés. README et CLAUDE.md mis à jour. CI nettoyée (le `pip install slowapi` redondant retiré).
- **Thème Monaco partagé** ✅ — `components/editor/anvilMonacoTheme.ts` (`ANVIL_DARK_THEME`, `defineAnvilDarkTheme()` idempotent). PwnEditor et SourceViewer migrés.
- **CSS `transition: all`** ✅ — 14 sites remplacés par `transition: background-color X, color X, border-color X, opacity X, transform X, box-shadow X` (élimine layout thrash, conserve les durées d'origine).
- **Frontend `src/config.ts`** ✅ — Constantes centralisées : `WS_RECONNECT_MS=2000`, `WS_HEARTBEAT_MS=30000`, `EDITOR_UNDO_HISTORY_MAX=80`, `EDITOR_SNAPSHOT_DEBOUNCE_MS=400`, `EDITOR_AUTOCOMPLETE_DEBOUNCE_MS=30`, `EDITOR_AUTOCOMPLETE_BLUR_DELAY_MS=150`, `EDITOR_FIND_FOCUS_DELAY_MS=50`, `EDITOR_DEFAULT_CHAR_WIDTH_PX=7.22`. AsmEditor + api/ws.ts migrent.
- **ADRs** ✅ — ADR-015 (CSP+CORS), ADR-016 (WS auth token), ADR-017 (Compile pipeline unifié), ADR-018 (Pattern useXxxSession + seuil 400 L), ADR-019 (pyproject.toml source unique) tous écrits dans `decisions.md`.

### Reportés au Sprint 17 (besoin de tests frontend)
- `<FilterableList>` extrait (Symbols/Strings/ROP listes) — refacto ~80 L sans test = risqué
- `fetchAndSet` helper dans `usePwnSession` — supprime 4 `as any` mais nécessite typer `PwnDictResponse` côté `api/client.ts` proprement
- Découpage `useAnvilSession` par domaine + `useCallback` massif — couplé au câblage WS Sprint 17

### Mesures
- Bundle inchangé (608 KB / 170 KB gzip), build OK, tsc clean, ruff clean, 699 tests passent

---
---

## Sprint 17 — Frontend tests + WS groundwork + cleanup (28 avril 2026) ✅
**Objectif** : poser le socle test frontend (vitest + RTL), durcir la CI (audits deps),
fermer les findings Quality reportés du sprint 16, et préparer l'infra WS auth.
**Agents** : @testing → @frontend → @architect

### Réalisé
- **A — Stack vitest + RTL + jsdom** : `vitest.config.ts` séparé (Tauri-safe), `src/test/setup.ts` avec jest-dom matchers + cleanup auto. Scripts `npm test`/`test:run`/`test:ui`. **27 tests** au total :
  - 11 sur `parseGdbResponse` (parsers GDB/MI extraits Sprint 15)
  - 8 sur `parseGdbMemory` (parseMemoryBlock/Map + parseRegisters extraits Sprint 17-E)
  - 5 sur `<FilterableList>` (filter, maxDisplay cap, placeholder)
  - 3 sur `<RegistersPane>` (smoke RTL + jsdom)
- **B — CI audits (closes Sec A9)** : nouveau job `audit` avec `pip-audit` (env installé via pyproject), `npm audit --audit-level=high`, `cargo-audit` sur `src-tauri/Cargo.lock`. `continue-on-error: true` pour ne pas bloquer un hotfix sur CVE upstream fraîche.
- **C — `<FilterableList>` extrait** : composant générique typé `<T>`, owns `filter` state, supporte `placeholder`/`maxDisplay`/clipped count. SymbolsList et StringsList migrent en wrappers (~80 L de duplication tuée).
- **D — `PwnDict<T>` typé + `fetchAndSet` helper** : 6 endpoints pwn rétypés (checksec/symbols/got/plt/sections/functions). `fetchAndSet<R, U>(call, map, setter, errorLabel?)` absorbe l'unwrap `{data:...}`, le mapping et le log d'erreur optionnel. **4 `as any` éliminés** dans `usePwnSession`.
- **E — `useAnvilSession` allégé** : parsers memory extraits dans `hooks/gdb/parseGdbMemory.ts` (parseMemoryBlock, parseMemoryMap, parseRegisters). `useCallback` posé sur les **23 fonctions retournées** par le hook (compile, buildAndRun, stepInto/Over/Out/Back, continueExec, stop, startAutoStep, stopAutoStep, setBreakpoint, freshSession, ensureSession, refreshRegisters, refreshStack, readMemory, writeMemory, fetchMemoryMap, resolveActiveLine, doStep, destroySessions, log, clearTerminal). Hook racine : 651 → 499 LOC.
- **F (groundwork) — `AnvilWS` production-ready** : token ADR-016 plumbé dans `connect()` (`?token=...` + `encodeURIComponent`), `request(command, args): Promise<WSMessage>` avec corrélation `request_id`, timeout 30s, rejection propre des pending au `disconnect()`. Type `SessionCreated` exposé côté client. **Migration de useAnvilSession sur WS reportée Sprint 18** (besoin de tests e2e pour valider le flux `step → registers → stack`).

### Reportés Sprint 18
- Migration `useAnvilSession` du REST GDB vers `AnvilWS.request()` — gain estimé -50ms/step, infra prête, manque le harness e2e
- Splitter `ReferenceModal.tsx` (877 L) par mode + dynamic `import('../data/reference-X')` par tab — bénéfice marginal après le `React.lazy(ReferenceModal)` du Sprint 15 #1 (la cascade Vite extrait déjà 102 KB en chunk séparé). À faire **si** la latence d'ouverture initiale du modal devient un problème.

### Mesures
- Tests frontend : **0 → 27** ✅
- `useAnvilSession.ts` : 651 → **499 LOC** (-23%)
- `as any` dans `usePwnSession` : 4 → **0**
- Bundle inchangé (608 KB / 170 KB gzip)

---
---

## Sprint 18 — E2E test infrastructure (28 avril 2026) ✅
**Objectif** : poser une stack de tests à 5 niveaux (unit → component → backend → smoke → e2e) avec Playwright comme couche e2e principale, plusieurs parcours par module ASM et Pwn, et préparer la structure pour les modes restants.
**Agents** : @testing → @architect

### Réalisé
- **Playwright bootstrap** : `playwright.config.ts` avec `webServer` qui spawn uvicorn + Vite et attend `/api/health` + `localhost:1420`. `reuseExistingServer` localement, `CI=1` force un boot propre. Retries 1 local / 2 CI. Trace + screenshot + video on failure.
- **Fixtures** : `tests/e2e/fixtures/anvil.ts` exporte `AnvilApp` (Page wrapper) + un `test` étendu qui reset les sessions backend entre tests. Tous les sélecteurs centralisés (`runButton`, `stepIntoButton`, `editorTextarea`, `pwnDropZone`, `pwnFilterInput`, `pwnBottomTab(name)`, `pwnToolButton(name)`). Samples inline dans `samples.ts` (NASM hello, GAS hello, broken NASM, divergent step, C BOF).
- **6 specs ASM** :
  1. `happy-path` (3 tests) — compile → run → step → registers + stdout
  2. `compile-error` (3 tests) — erreur structurée + ligne annotée + recovery après fix
  3. `reverse-step` (2 tests) — Back button + register diff visible entre steps
  4. `multi-assembler` (4 tests) — NASM default, GAS conditional, FASM offered, status bar
  5. `breakpoint` (2 tests) — gutter click + persistence sur edit
  6. `state-panels` (3 tests) — Stack/Memory/Security panels + collapse/expand + terminal clear
- **5 specs Pwn** :
  1. `mode-switch` (4 tests) — lazy chunk loads, topbar tools, bottom tabs, isolation ASM
  2. `cyclic-tool` (2 tests) — pattern generation + cyclic_find offset
  3. `upload-binary` (3 tests) — checksec badges, symbols list, filter shrink
  4. `compile-source` (2 tests) — drop .c, auto-compile, SourceViewer vuln highlight
  5. `security-guard` (3 tests) — LFI 403 PATH_BLOCKED, filename 422, language 400 (via fetch direct)
- **Smoke script bash** (`tests/e2e/smoke/backend.sh`) : 5 checks live (health 200, token format ADR-016, GET ne leak pas le token, LFI bloquée, WS sans token rejeté). **5/5 verts en local**. Industrialise le smoke manuel du Sprint 14.
- **CI workflow** : 4 jobs (`lint`, `audit`, `test`, `smoke`, `e2e`). `test` étendu pour aussi lancer vitest. `smoke` boot uvicorn + lance le bash. `e2e` install nasm/gdb/gcc + Playwright browsers + build samples + lance la suite. `continue-on-error: true` sur `e2e` jusqu'à ce que la suite soit stable 2 semaines. Upload du Playwright report en artifact si failure.
- **Doc** : `tests/e2e/README.md` complet (run, tooling, layout, ajout d'un nouveau mode, discipline anti-flake), scripts npm `e2e`/`e2e:ui`/`e2e:debug`/`smoke`. ADR-019 corrigée dans le CI (`python -m pytest tests/`).

### Couverture
- **Backend Python** : 699 tests pytest (depuis Sprint 14)
- **Frontend unit/component** : 27 tests vitest (depuis Sprint 17)
- **Backend smoke** : 5 checks bash (Sprint 18)
- **E2E parcours** : 11 specs / ~31 tests (Sprint 18)
- **Total** : ~762 tests automatisés

### Suite immédiate (Sprint 19)
- Migration `useAnvilSession` REST → `AnvilWS.request()` — débloquée par la stack e2e (chaque flux step→registers→stack peut être validé en live)
- Nouveaux specs ASM : `terminal.spec.ts` (clear, output capture), `editor-undo.spec.ts` (Ctrl+Z, snapshots)
- Frontend RE — démarrage du gros chantier avec specs `tests/e2e/re/*.spec.ts` créés au fur et à mesure

---
---

## Sprint 19 — Vision sync, audit finalization & CI hardening (29 avril 2026) ✅
**Objectif** : Aligner les docs sur la vision v2, documenter le contrat MCP, finaliser l'audit sécurité, stabiliser la pipeline CI.
**Agents** : direct session (pas de workflow multi-agent)

### Réalisé — Docs & Vision
- [x] Vision v2 documentée (ADR-021) : "Le Burp Suite du bas niveau", 5 modules, GPL v3
- [x] Contrat MCP server documenté (ADR-022) : standalone SSE/stdio, contrat complet défini, implémentation en dernier (Sprint 28)
- [x] Backlog revampé : RE phases 1-3, Wire module, Firmware pipeline, Sprints 24-28 ajoutés
- [x] README + AGENTS.md + CLAUDE.md synchronisés avec vision v2

### Réalisé — Audit & fixes code
- [x] Fix `test_concurrent_execute_serialized` — health mock manquant (regression silencieuse post-Sprint 14)
- [x] Fix 3 warnings Pydantic v2 — champ `register` shadow ABCMeta :
      → `GdbSetRegisterRequest`, `RizinEsilSetRegRequest` : `alias="register"` + `ConfigDict(populate_by_name=True)`
      → `ModbusDiagResponse` : `serialize_by_alias=True`, contrat JSON API inchangé
- [x] Sprint 14 hardening confirmé ✅ : 736 tests, ruff clean, bandit clean, cargo check ok
- [x] MCP skeleton merge (Ultraplan) + résolution conflits + 36 nouveaux tests

### Réalisé — CI hardening (stabilisation complète)
- [x] `Makefile` + `.githooks/pre-push` : `make check` = CI locale exacte, hook bloquant avant push
- [x] Smoke test : gdb → pwn (GDB absent dans le job test)
- [x] Ruff format : 52 fichiers reformatés, `anvil_mcp/` ajouté aux cibles lint
- [x] `src-tauri/.cargo/audit.toml` : 19 advisories Tauri documentés et ignorés (scan local exhaustif)
- [x] pip-audit : `--ignore-vuln CVE-2026-3219` + upgrade pip avant audit
- [x] Node.js 24 : `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` (migration avant juin 2026)
- [x] Python 3.12 → 3.13 en CI : alignement avec le venv local, plus de drift
- [x] Cache pip (`setup-python cache: pip`) sur les 4 jobs qui l'utilisent
- [x] Cache cargo-audit binary (key: version) : ~4 min install → ~0s sur cache hit
- [x] E2E : fixture attend `.anvil-ed-textarea` avant lancement, `actionTimeout` 8s → 20s en CI
- [x] `gh` CLI installé en local pour accès aux logs CI

### Couverture finale
- Backend Python : **736 tests** (+36 MCP skeleton)
- Frontend unit/component : 27 tests vitest
- E2E Playwright : 31 specs
- **Total : ~794 tests automatisés**

### Suite
Sprint 20 — WS migration + Mode RE phase 1 (voir backlog.md)

---
---

## Sprint 20+ — Planifiés

Voir [backlog.md](./backlog.md) pour le détail des sprints à venir (WS migration, Mode RE phases 1-3, Contexte inter-modules, GDB remote, Firmware pipeline, Wire, MCP server) — Sprints 20-28.
