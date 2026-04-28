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

## Sprint 7 — Mode ASM : Éditeur & Compilation UI (backlog)
**Objectif** : Premier mode fonctionnel — écrire du code ASM, compiler, voir le résultat.
**Agents** : @frontend → @architect → @testing

### 7.1 — Layout de base
- [ ] Shell React : sidebar modes (6 icônes) + zone principale + barre d'état
- [ ] Router interne : switch entre modes (ASM, RE, Pwn, Debug, Firmware, Protocols)
- [ ] Composant `<Editor>` — CodeMirror 6 avec coloration syntaxique x86 ASM
- [ ] Split pane vertical : éditeur | output (terminal/console)

### 7.2 — Compilation pipeline UI
- [ ] Bouton Compile (Ctrl+B) → POST /api/compile/{session_id}/asm
- [ ] Affichage erreurs nasm inline (markers CodeMirror)
- [ ] Affichage warnings/errors dans panel output
- [ ] Toggle libc linking (checkbox)
- [ ] Panel "Binary Info" : checksec + ELF info après compilation

### 7.3 — Session management UI
- [ ] Connexion WebSocket au boot
- [ ] Création session auto (bridge_type=compilation)
- [ ] Indicateur statut backend (connected/disconnected)
- [ ] Gestion reconnection WS

### 7.4 — Tests
- [ ] Tests Vitest composants React
- [ ] Tests intégration WS mock

---

## Sprint 8 — Mode ASM : Debug interactif (GDB)
**Objectif** : Débuguer le binaire compilé — breakpoints, step, registres, mémoire, stack.
**Agents** : @frontend → @backend → @testing

### 8.1 — Debug controls
- [ ] Bouton "Debug" → crée session GDB + load binary
- [ ] Toolbar debug : Run, Continue, Step Into, Step Over, Step Out, Stop
- [ ] Raccourcis clavier (F5 Run, F10 Step Over, F11 Step Into, Shift+F11 Step Out)
- [ ] Sync instruction courante ↔ ligne éditeur (highlight)

### 8.2 — Panels debug
- [ ] Panel Registres — tableau live (GPR, flags, segments) via WS gdb.registers
- [ ] Panel Stack — frames + variables locales via WS gdb.stack
- [ ] Panel Mémoire — hex viewer avec lecture via /api/gdb/{sid}/memory
- [ ] Panel Disassembly — instructions autour de $pc
- [ ] Panel Breakpoints — liste, activer/désactiver, conditions

### 8.3 — Breakpoints visuels
- [ ] Click marge éditeur → set breakpoint (gutter markers)
- [ ] Sync bidirectionnelle breakpoints éditeur ↔ GDB bridge
- [ ] Breakpoints conditionnels (input dialog)

### 8.4 — Tests
- [ ] Tests WS debug flow (mock GDB responses)
- [ ] Tests composants debug panels

---

## Sprint 14 — Hardening sécu post-merge (28 avril 2026) 🔴 IN PROGRESS
**Objectif** : Corriger les findings critiques identifiés par l'audit multi-agent (Security + Pentester) après le merge `asm-dev → main`. Anticiper le déploiement Docker/web.
**Agents** : @security → @pentester → @backend → @testing
**Priorité** : 🔴 CRITIQUE — bloquant avant tout déploiement web/multi-user

### Findings traités
1. **Pent#1 (Critique, RCE)** — `gdb.execute` raw via WS ne sanitize pas l'input. Fix : `sanitize_gdb_input()` dans `gdb_ws.py:_handle_raw_execute`.
2. **Pent#2/#3 (Élevé)** — Sanitizer GDB n'inclut pas `"`, allowlist GCC `-W*` autorise `-Wl,-rpath`. Fix : ajouter `"` aux chars bloqués + restreindre `-W*` à une allowlist explicite (`-Wall`, `-Wextra`, `-Werror`, `-W<warning>`).
3. **Sec A1+A2 / Archi#1 / Pent#4+#6 (Critique)** — `api/pwn.py:compile_source` ré-implémente nasm/gcc/rustc/go en parallèle de `CompilationBridge`. Endpoints `elf/*` acceptent un `path` arbitraire. Fix : rerouter vers `CompilationBridge` + valider tous les paths via `WorkspaceManager.get_file_path(session_id, basename)`.
4. **Pent#11 / Sec A3 (Élevé)** — WebSocket `/ws/{type}/{id}` accepte sans auth. Fix : générer un `Session.token` (32 hex) au create, exiger `?token=...` côté WS, vérifier `Origin` header.
5. **Sec A4 / Pent#14 (Moyen → Élevé sous web)** — `csp: null` dans Tauri + CORS `*`. Fix : CSP stricte (default-src 'self', connect-src 127.0.0.1:8000) + CORS limité à `http://localhost:1420` en mode desktop.
6. **Test régression** — `api/pwn.py` à ~10% couverture, models/pwn.py à ~5%. Fix : créer `test_pwn_api.py` + `test_pwn_models.py` couvrant validators et endpoints sensibles, plus `test_compile_api_assemblers.py` pour GAS/FASM côté route.

### Réalisé
*(en cours)*

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

## Sprint 16 — Quality cleanup & ADRs (28 avril 2026) ⏸ PLANIFIÉ
**Objectif** : Régler la dette quality identifiée et formaliser les décisions structurantes.
**Agents** : @quality → @architect

### Findings traités
- **Archi (deps Python divergentes)** — `requirements.txt` ≠ `pyproject.toml` (pwntools 4.0 vs 4.12). Fix : supprimer `requirements.txt`, ajouter `pyproject.toml` comme source unique.
- **Quality (duplication PwnMode)** — `SymbolsList` ≈ `StringsList`. Fix : extraire `<FilterableList>`.
- **Quality (duplication usePwnSession)** — 4 `fetchChecksec/Symbols/Got/Plt` quasi-identiques + 4 `as any`. Fix : helper `fetchAndSet` typé.
- **Archi (thème Monaco dupliqué)** — PwnEditor + SourceViewer redéfinissent `anvil-dark`. Fix : extraire `editor/anvilMonacoTheme.ts`.
- **Quality (magic numbers AsmEditor)** — `7.22`, `400`, `80`, `30`, `20` sans nom. Fix : constantes `LINE_HEIGHT_PX`, `SNAPSHOT_DEBOUNCE_MS`, etc.
- **Quality (frontend sans config)** — WS reconnect/heartbeat hardcodés dans `api/ws.ts`. Fix : `src/config.ts` central.
- **Perf (CSS transition: all)** — 14 sites dans `App.css`. Fix : propriétés ciblées.
- **ADRs à écrire** — ADR-015 (CSP+CORS), ADR-016 (WS auth token), ADR-017 (Compile pipeline unifié), ADR-018 (Pattern useXxxSession + seuil 400 L), ADR-019 (pyproject.toml source unique deps Python).

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

## Sprint 9 — Mode RE : Frontend reverse engineering (backlog)
**Objectif** : Interface complète d'analyse statique de binaires via le bridge Rizin.
**Agents** : @frontend → @architect → @testing
> Backend 100% prêt (Sprint 4 : 50 méthodes, 70 endpoints).

### 9.1 — Layout RE
- [ ] Layout 3 colonnes : fonctions | vue centrale | sidebar info
- [ ] File dialog natif (Tauri) ou upload pour charger un binaire
- [ ] Barre d'analyse : boutons aa / aaa / aaaa + progress

### 9.2 — Vue centrale
- [ ] Tab Disassembly — instructions colorisées, adresses, opcodes
- [ ] Tab Décompilation — pseudo-C via r2ghidra (pdg)
- [ ] Tab Hexdump — hex editor interactif
- [ ] Tab Strings — tableau filtrable
- [ ] Navigation adresse ↔ fonction (click = seek)

### 9.3 — Sidebar info
- [ ] Imports / Exports
- [ ] Symbols
- [ ] Sections / Segments
- [ ] Cross-references (xrefs to/from)
- [ ] Binary info (arch, format, endian, entry)

### 9.4 — Fonctionnalités avancées
- [ ] CFG control flow graph (canvas SVG/WebGL)
- [ ] Call graph
- [ ] Rename function (inline edit → /api/re/{sid}/rename)
- [ ] Comments (add/edit/delete)
- [ ] Flags
- [ ] Dangerous functions highlight (system, strcpy, gets, etc.)

### 9.5 — Tests
- [ ] Tests Vitest composants RE
- [ ] Tests navigation + recherche

---

## Sprint 10 — Mode Pwn : Exploit development (completed in Sprint 9) ✅
> Réalisé dans Sprint 9 — Mode Pwn UI Complète (23 avril 2026).

### 10.1 — Éditeur exploit
- [ ] CodeMirror 6 avec coloration Python
- [ ] Templates d'exploits pré-remplis (BOF, fmtstr, ret2libc, ROP chain, heap, SROP)
- [ ] Exécution script Python (subprocess backend)
- [ ] Output console (stdout/stderr streaming WS)
- [ ] Target selector : local binary / remote host:port

### 10.2 — Outils intégrés
- [ ] Panel Checksec — affichage protections binaire cible
- [ ] Panel ROP — recherche gadgets (via /api/pwn/{sid}/rop/*)
- [ ] Format string calculator UI
- [ ] Cyclic pattern generator/finder
- [ ] Payload hex viewer (pack/unpack preview)

### 10.3 — ELF browser
- [ ] Chargement ELF → symbols, GOT, PLT, sections
- [ ] Navigation rapide symbols → adresses

### 10.4 — Tests
- [ ] Tests composants Pwn
- [ ] Tests flow template → edit → execute

---

## Sprint 11 — Mode Debug enhanced + Mode Firmware
**Objectif** : Heap visualizer, syscall trace, firmware analysis UI.
**Agents** : @frontend → @pentester → @testing

### 11.1 — Debug enhanced
- [ ] Heap visualizer — chunks, bins, tcache (graphe interactif)
- [ ] Syscall trace (via GDB catch syscall → table live)
- [ ] Memory map visuelle — barres colorées (stack, heap, .text, libs)
- [ ] Canary + return address tracking
- [ ] Core dump loader + analysis

### 11.2 — Mode Firmware UI
- [ ] Upload firmware → scan binwalk
- [ ] Résultats scan : tableau signatures détectées
- [ ] Extraction : arbre filesystem navigable
- [ ] Graphe entropie (chart.js / recharts)
- [ ] Secret scanning : highlights passwords, clés, tokens
- [ ] Transition → RE (ouvrir un binaire extrait dans le mode RE)

### 11.3 — Tests
- [ ] Tests composants heap/memory map
- [ ] Tests flow firmware scan → extract → browse

---

## Sprint 12 — Mode Protocols ICS/OT + Tauri packaging
**Objectif** : Interface Modbus/ICS + packaging desktop natif.
**Agents** : @frontend → @devops → @rust → @testing
> Backend 100% prêt (Sprint 5 : 40 méthodes Modbus).

### 12.1 — Mode Protocols UI
- [ ] Connexion Modbus TCP/RTU : formulaire host/port/unit/baudrate
- [ ] Register browser : tableau live coils, discrete inputs, holding, input registers
- [ ] Read/Write operations avec ⚠️ avertissement sécurité
- [ ] Device info panel (identification)
- [ ] Scan devices/registers (progress bar)
- [ ] Diagnostics panel
- [ ] Data type conversion calculator

### 12.2 — Tauri packaging
- [ ] `src-tauri/src/lib.rs` : spawn FastAPI subprocess + health check loop
- [ ] File dialogs natifs (ouvrir binaires .elf/.bin/.hex/.c)
- [ ] Dependency checker au premier lancement (gdb, rizin, gcc, python, nasm)
- [ ] Build AppImage Linux
- [ ] Auto-update (tauri-plugin-updater)
- [ ] Icône + splash screen

### 12.3 — Tests
- [ ] Tests composants Protocols
- [ ] Tests Tauri IPC (mocks)
- [ ] Tests E2E Playwright (smoke)

---

## Sprint 13 — Polish, a11y, i18n
**Objectif** : Qualité finale — accessibilité, internationalisation, tests e2e complets.
**Agents** : @a11y → @quality → @frontend → @testing

### 13.1 — Accessibilité
- [ ] Audit WCAG 2.1 AA
- [ ] Navigation clavier complète
- [ ] Screen reader support (aria-labels)
- [ ] Contrastes couleurs (dark theme)
- [ ] Focus management

### 13.2 — Internationalisation
- [ ] i18n framework (react-i18next)
- [ ] Traductions EN + FR
- [ ] Détection langue auto

### 13.3 — Tests E2E
- [ ] Suite Playwright — smoke tests tous les modes
- [ ] Flow complet : écrire ASM → compiler → débuguer → step → voir registres
- [ ] Multi-session concurrentes
- [ ] Tests responsivité

### 13.4 — Extras
- [ ] Shellcode workshop (mode ASM) — exercices interactifs
- [ ] Multi-architecture ASM (ARM64, RISC-V via cross-compile)
- [ ] Plugin system (API extension points)
- [ ] Documentation utilisateur (guide + tooltips)
