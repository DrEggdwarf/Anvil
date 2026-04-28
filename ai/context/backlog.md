# Backlog — Anvil

## 🔴 Audit post-merge `asm-dev → main` (28 avril 2026) — Sprints 14-16

> Audit multi-agent complet (Security, Pentester, Architect, Performance, Quality, Testing) sur le merge `asm-dev → main`.
> Verdict global : **fondation saine, dette localisée** — bloquant uniquement pour déploiement web/multi-user.
> Mode desktop local (Docker localhost final) : acceptable temporairement.

### Sprint 14 — Hardening sécu ✅ (28 avril)
- [x] #1 `sanitize_gdb_input` sur `gdb.execute` raw WS (RCE Critique 1 ligne)
- [x] #2 `"` aux GDB chars bloqués + restreindre allowlist GCC `-W*`/`-l/path`/`-D`/`-I`
- [x] #3 Converger `api/pwn.py:compile_source` → `CompilationBridge` + paths via `WorkspaceManager`
- [x] #4 Token + Origin check sur WebSocket `/ws/{type}/{id}` (ADR-016)
- [x] #5 CSP stricte `tauri.conf.json` + CORS limité à `localhost:1420` (ADR-015)
- [x] #6 Tests sécu : `test_pwn_api.py` (32 tests), `test_pwn_models.py` (12 tests), assembler tests

### Sprint 15 — Performance & Architecture refactor ✅ (28 avril)
- [x] `React.lazy(PwnMode + ReferenceModal)` dans `App.tsx` — bundle initial 720 → 608 KB (-16%)
- [x] Parsers GDB extraits dans `hooks/gdb/parseGdbResponse.ts` (-91 L sur useAnvilSession)
- [x] LRU réel `pwn_bridge._cache_elf`/`_cache_rop` via `OrderedDict.move_to_end`
- [→ Sprint 17] `useCallback`/`useMemo` massif sur useAnvilSession (couplé refacto WS)
- [→ Sprint 17] Câbler frontend sur `/ws/gdb/{id}` pour stepping (gain -50ms/step)
- [→ Sprint 17] Splitter `ReferenceModal.tsx` par mode + dynamic data par tab

### Sprint 16 — Quality cleanup & ADRs ✅ (28 avril)
- [x] Supprimer `requirements*.txt` divergents (pyproject.toml seule source) + CI nettoyée
- [x] `editor/anvilMonacoTheme.ts` partagé (PwnEditor + SourceViewer)
- [x] Constantes nommées dans `AsmEditor` + `src/config.ts`
- [x] `transition: all` → propriétés ciblées (14 sites `App.css`)
- [x] ADR-015 à ADR-019 écrits dans `decisions.md`
- [→ Sprint 17] Extraire `<FilterableList>` (Symbols/Strings/ROP) — besoin de tests frontend
- [→ Sprint 17] Helper `fetchAndSet` dans `usePwnSession` — typer `PwnDictResponse` proprement

### Portability checklist (ADR-020) — vérifier à chaque PR
- [ ] Aucun path Linux hardcodé (`grep -rn '/proc/\|/sys/\|/dev/\|/usr/bin' backend/app/ src/`)
- [ ] Tous les subprocess via `SubprocessManager` (pas de `os.system`, `subprocess.run` direct)
- [ ] `src-tauri/src/lib.rs` reste sous 100 LOC, pas de plugin natif OS-specific
- [ ] Outils invoqués par nom (PATH), pas par chemin absolu
- [ ] Capabilities Tauri restent minimales

### Sprint 17 — Frontend tests + WS groundwork + cleanup ✅ (28 avril)
- [x] A — Bootstrap vitest + RTL + jsdom (27 tests)
- [x] B — CI audits (pip-audit + npm audit + cargo audit) — closes Sec A9
- [x] C — `<FilterableList>` extrait (-80 L duplication)
- [x] D — `PwnDict<T>` typé + `fetchAndSet` helper (4 `as any` éliminés)
- [x] E — `useAnvilSession` 651 → 499 L + parsers memory extraits + useCallback ×23
- [x] F (groundwork) — `AnvilWS` production-ready (token ADR-016 + `request()` Promise)

### Sprint 18 — E2E test infrastructure ✅ (28 avril)
- [x] Playwright bootstrap + config + fixtures + samples
- [x] 6 specs ASM (happy/error/reverse/assembler/breakpoint/panels — ~17 tests)
- [x] 5 specs Pwn (mode-switch/cyclic/upload/compile-source/security — ~14 tests)
- [x] Smoke script bash (5 checks live, all green)
- [x] CI workflow : 5 jobs (lint, audit, test, smoke, e2e)
- [x] Doc complète (`tests/e2e/README.md`)

### Sprint 19 — WS migration + Mode RE phase 1 ⏸ PLANIFIÉ
- [ ] **F.2** Migrer `useAnvilSession` REST → `AnvilWS.request()` (-50ms/step) — débloqué par la stack e2e
- [ ] **Mode RE phase 1** : layout 3 cols (fonctions | disasm | info), liste fonctions filtrable, viewer disasm, panels strings/imports/exports
- [ ] Specs e2e RE : `mode-switch`, `analyze`, `function-list`, `disasm-view`
- [ ] **G** ReferenceModal split par mode (si triggers atteints — backlog Sprint 17)

### Sprint 20 — Mode RE phase 2 ⏸ PLANIFIÉ
- [ ] Décompilation pseudo-C via `r2ghidra pdg`
- [ ] CFG canvas (call graph, function graph)
- [ ] Xrefs panel
- [ ] Specs e2e RE phase 2 : `decompile`, `cfg-canvas`, `xrefs`

---

## Phase 0 — API Engine (Sprints 1-6) 🔴 CRITIQUE
> Le moteur d'API est le socle de TOUT. Chaque mode/feature en dépend.
> Aucune feature UI ne doit démarrer avant que le core API soit testé à 90%+.

### Sprint 1 — Core Engine ✅
- [x] Architecture backend modulaire (core/, bridges/, sessions/, api/, models/)
- [x] Subprocess Manager (spawn, execute, kill, cleanup_all)
- [x] BaseBridge ABC (start, stop, health, execute) + Registry
- [x] Session Manager (create, get, destroy, timeout, concurrent limits)
- [x] WebSocket infra (typed messages, dispatcher, heartbeat, error handling)
- [x] Exception hierarchy + error middleware JSON
- [x] Settings Pydantic (env vars, ANVIL_ prefix, limites configurables)
- [x] 97 tests, 95% coverage

### Sprint 2 — GDB Bridge (référence) ✅
- [x] gdb_bridge.py via pygdbmi (step, continue, registers, memory, stack)
- [x] Routes REST /api/gdb/* (14 routes)
- [x] WebSocket /ws/gdb/{session_id} (14 handlers)
- [x] 171 tests, 97% coverage (mock pygdbmi)

### Sprint 3 — Compilation Pipeline ✅
- [x] Compilation ASM (nasm+ld) et C (gcc) avec flags sécurité
- [x] Checksec binaire + binary info + ELF sections
- [x] File management (workspace isolé, validation, path traversal protection, cleanup)
- [x] 243 tests, 97% coverage (mock subprocess)

### Sprint 4 — RE Bridge + Feature Completion ✅
- [x] rizin_bridge.py via rzpipe (~50 méthodes : analyse, fonctions, décompilation, strings, xrefs, ESIL, patching, search, graphs)
- [x] Routes REST /api/re/* (~70 endpoints)
- [x] GDB bridge étendu (~15 → ~45 commandes) + binary analyzer (~3 → ~20 méthodes)
- [x] 388 tests, 0 failures (mock rzpipe + mock subprocess)

### Sprint 5 — Bridges Pwn, Firmware, Protocols ✅
- [x] pwn_bridge.py (~40 méthodes : context, cyclic, pack, asm, shellcraft, ELF, ROP, fmtstr, SROP, ret2dl, encoding, hashing, constants, corefile)
- [x] firmware_bridge.py (~20 méthodes : scan, extract, entropy, strings, opcodes, raw search, secrets, auto v3/v2)
- [x] protocol_bridge.py (~40 méthodes : Modbus TCP/UDP/Serial/TLS, all FCs, diagnostics, device info, conversion, scan, server)
- [x] Routes REST + Pydantic models pour les 3 bridges
- [x] 586 tests, 0 failures

### Sprint 6 — Hardening & Integration ✅
- [x] Input sanitization module (GDB, Rizin, paths, GCC flags, session ID)
- [x] Rate limiting (slowapi, 120/min)
- [x] CORS hardened (explicit methods/headers)
- [x] Subprocess concurrency limit (semaphore, max 20) + output size enforcement
- [x] Pydantic max_length on all string fields
- [x] Workspace moved to ~/.anvil/workspaces
- [x] CI pipeline (.github/workflows/ci.yml: ruff + bandit + pytest)
- [x] Security tests (30 unit + E2E API injection/traversal tests)
- [x] 631 tests, 0 failures

### Sprint 7 — ASM Debugger UI ✅
- [x] Frontend mode ASM fonctionnel (éditeur, registres, stack, terminal)
- [x] Step into/over/out/back via GDB/MI
- [x] Reverse debugging (GDB `record` + `reverse-stepi`)
- [x] GDB/MI output parsing (program stdout extraction, protocol stripping)
- [x] Triple fallback active line resolution (frame → stack → info line *$pc)
- [x] 639 tests, 0 failures

---

## Phase A — Pwn lite web (mode ASM étendu)
- [ ] Upload fichier C (handler WS `upload_c`)
- [ ] Compilation gcc avec flags configurables (UI checkboxes)
- [ ] Checksec auto du binaire C compilé
- [ ] GDB stepping sur binaire C (adapter entry point)
- [ ] VMmap, GOT, ROP, cyclic sur binaire C

## Phase B — Tauri packaging + Docker cross-platform
- [ ] Dockerfile backend (Python 3.12 + FastAPI + nasm/ld/gcc/gdb/rizin/pwntools/binwalk/pymodbus)
- [ ] Tauri : détecter Docker, pull image au premier lancement, `docker run` au start, kill au close
- [ ] Fallback : subprocess local si Linux natif (pas de Docker requis)
- [ ] File dialogs natifs (ouvrir .c / .bin / .elf / .hex)
- [ ] Dependency checker au premier lancement (Docker ou outils natifs)
- [ ] Build AppImage Linux + MSI Windows
- [ ] Auto-update (tauri-plugin-updater)
- [ ] Volume mount ~/.anvil/workspaces pour persistance entre sessions Docker

## Phase C — Mode RE
> Note : Le bridge backend (`rizin_bridge.py`) est terminé depuis Sprint 4. Cette phase concerne le **frontend** RE.
- [x] `rizin_bridge.py` — wrapper rzpipe (50 méthodes, Sprint 4)
- [x] Routes REST /api/re/* (70 endpoints, Sprint 4)
- [ ] Frontend layout 3 colonnes (fonctions | décompilé | info)
- [ ] Décompilation pseudo-C (r2ghidra pdg)
- [ ] Liste des fonctions filtrable
- [ ] CFG et call graph (canvas)
- [ ] Strings, imports/exports, xrefs
- [ ] Binary patching
- [ ] Hexdump interactif
- [ ] Dangerous functions highlight

## Phase D — Mode Pwn complet
- [ ] Éditeur Python (CodeMirror 6)
- [ ] Exécution script Python
- [ ] Templates d'exploits (BOF, fmtstr, ret2libc, ROP, heap, SROP)
- [ ] Target local/remote toggle
- [ ] ROP builder drag & drop
- [ ] Format string calculator
- [ ] Payload hex viewer
- [ ] Libc database + patchelf + one_gadget
- [ ] File explorer + notes markdown

## Phase E — Mode Debug enhanced
- [ ] Heap visualizer (chunks, bins, tcache)
- [ ] Syscall trace (strace-like)
- [ ] Canary + return address tracking
- [ ] Core dump analysis
- [ ] Memory map visuelle (barres colorées)
- [ ] Cross-arch debug (QEMU + gdb-multiarch)

## Phase F — Mode Firmware
- [ ] Firmware extraction (binwalk)
- [ ] Entropy analysis (graphe)
- [ ] Filesystem browser
- [ ] Secret scanning (passwords, clés, tokens)
- [ ] Transitions → RE, → Debug
- [ ] Multi-arch (ARM, MIPS, PowerPC)

## Phase G — Mode Protocols ICS/OT
- [ ] Modbus TCP/RTU (pymodbus)
- [ ] S7comm (python-snap7)
- [ ] OPC-UA (opcua-asyncio)
- [ ] Device discovery/scan
- [ ] Register read/write avec avertissement sécurité
- [ ] Protocol decode (trames)
- [ ] Replay + fuzzer
- [ ] UART/Serial (crate serialport)

## Phase H — Polish & extras
- [ ] Shellcode workshop (mode ASM)
- [ ] Exercices intégrés avec validation auto
- [ ] i18n EN/FR
- [ ] Multi-architecture ASM (ARM64, RISC-V)
- [ ] Tests Playwright e2e
- [ ] Accessibilité (a11y)
- [ ] Plugin system

## Bugs Anvil à corriger
- [ ] B10: ~~CALL step-into cassé~~ Fixed (reverse-step + record ajoutés)
- [ ] B11: Tokens QWORD/DWORD/WORD/BYTE/PTR manquants
- [ ] B12: Auto-close crochet `[` → `[]`
- [ ] B13: Fidélité valeurs stack vs GDB

## Idées à évaluer (pas planifiées, gardées pour réflexion)

- [ ] **Migration AsmEditor → Monaco** — l'éditeur custom (525 L) est un héritage ASMBLE.
  Avantages migration : multi-cursor, find&replace plus puissant, grammaires multi-arch
  (ARM/RISC-V) gratuites, bundle Monaco déjà chargé pour le mode Pwn.
  Coût : ~2-3 jours, ~600 LOC à porter (breakpoint gutter via `glyphMarginWidget`,
  active line via `deltaDecorations`, jump arrows via `addContentWidget`).
  À évaluer **quand** : ajout multi-architecture ASM (Phase H), ou intro de features
  type LSP (rename label, find references), ou ciblage mode web.
  À NE PAS faire tant que ces déclencheurs ne sont pas là — risque de perte de
  contrôle CSS fin et complication de la synchro GDB pour zéro feature visible.
