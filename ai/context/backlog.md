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

### Sprint 19 — Vision sync & audit finalization ✅ (29 avril)
- [x] ADR-021 Vision v2 + ADR-022 MCP contrat (decisions.md)
- [x] Fix test `test_concurrent_execute_serialized` (health mock) + 3 warnings Pydantic v2 (register alias)
- [x] Backlog revampé avec vision v2, Sprints 24-28 ajoutés
- [x] Sprint 14 hardening confirmé : 700/700 tests, ruff/bandit/cargo clean

### Sprint 20 — Mode RE phase 1 + Decompiler capability + Docker ✅ (3 mai 2026)

**A — Mode RE phase 1** :
- [x] Layout 3 panneaux : sidebar (functions/strings/imports/exports) | CFG | right panel (decompile/disasm)
- [x] Hook `useRizinSession` rewrite avec auto-analyze pipeline
- [x] `ReEmptyState` (Tauri/browser-aware), `ReLoadingBar`, `ReTopBar`
- [x] CFG @xyflow/react + dagre, alignement T/F, back-edges, hover border violet
- [x] `rizin.analyze()` et `decompile()` → dicts structurés (ADR-022 conforme)
- [x] `rizin_bridge.start()` deferred (fix hang `rzpipe.open("")`)

**B — Decompiler capability** :
- [x] `decompile()` raise `DECOMPILER_MISSING` (HTTP 422) quand pdg/pdd absent
- [x] `client.ts` propage `error.code` + `error.status`
- [x] `DecompileView.onMissing` callback → `REMode` masque l'onglet
- [x] Tab par défaut : `disasm` (universellement dispo)

**C — Docker** :
- [x] `docker/Dockerfile.backend` basé `kalilinux/kali-rolling`
- [x] rizin + rz-ghidra + binwalk + gdb + nasm/gcc préinstallés
- [x] User non-root, HEALTHCHECK, sanity check rz-ghidra plugin

**D — WS migration (REPORTÉ Sprint 22+)** :
- [ ] Migrer `useAnvilSession` REST → `AnvilWS.request()` — pas bloquant, gain marginal

### Sprint 21bis — RE phase 2 light ✅ DONE
- [x] Build Docker image + verify rz-ghidra (decompile fonctionnel via container)
- [x] Xrefs panel (onglet right panel — `to/from`, click-to-navigate, badges typés)
- [x] Hex viewer (toolbar addr custom + size, dump `px` rizin)
- [x] ASM↔C sync visuel (état partagé `selectedAddr`, click DisasmView highlight + heuristique de matching d'adresse dans Monaco DecompileView)
- [x] E2E specs : `tests/e2e/re/re-phase2.spec.ts` (7 tests : load binary, xrefs to/navigate, hex view + custom addr, disasm select, decompile capability)

**Décisions** :
- Sync ASM↔C reste **best-effort** : pas de mapping pdgj côté backend, l'heuristique cherche le hex de l'adresse dans le pseudo-C (rz-ghidra émet souvent les adresses en commentaires ou litéraux). Le vrai mapping (parser `pdgj` JSON + Monaco decorations stables) est reporté à un sprint dédié si le besoin se confirme.
- Hex viewer non virtualisé : `read_hex_text` (commande `px` rizin) renvoie un dump déjà formaté ; suffisant ≤ 4 KB. Virtualisation reportée si paginations longues nécessaires.

### Sprint 22 — Agent IA in-app 🎯 PROCHAIN

> ADR-023 ratifié. Sprint **unique de bout en bout** — pas de découpage incrémental : la feature livrée est complète, utilisable, persistée, multi-provider.

**Objectif** : un agent IA contextuel intégré, déclenchable par FAB ✦ ou ⌘K, qui agit via les tools MCP existants (ADR-022) en réutilisant `anvil_mcp.tools.*` en in-process.

**Livrables backend** :
- [ ] `backend/app/agent/runtime.py` — orchestrator (boucle messages ↔ tools, SSE)
- [ ] `backend/app/agent/providers/{anthropic,openai,openrouter,ollama}.py` — interface commune `stream(messages, tools) → AsyncIterator[Chunk]`
- [ ] `backend/app/agent/tools.py` — dispatcher import in-process de `anvil_mcp.tools.*` + allowlist (Strict mode) + flag destructif
- [ ] `backend/app/agent/storage.py` — SQLite (`aiosqlite`) `~/.anvil/agent.db`
- [ ] `backend/app/agent/audit.py` — append-only log `~/.anvil/agent.log`
- [ ] `backend/app/api/agent.py` — `POST /api/agent/chat` (SSE), `GET/DELETE /api/agent/sessions[/{id}]`, `GET/POST /api/agent/settings`, `GET /api/agent/providers/test`
- [ ] Pydantic models : `AgentChatRequest`, `AgentChunk`, `AgentSession`, `AgentToolCall`, `AgentSettings`
- [ ] Groupe `[agent]` dans `backend/pyproject.toml` (`anthropic`, `openai`, `aiosqlite`)

**Livrables frontend** :
- [ ] `src/components/agent/AgentFab.tsx` — bouton bas-droite + tooltip 3 actions
- [ ] `src/components/agent/AgentWidget.tsx` — overlay d'entrée (chips + historique 3 + textarea)
- [ ] `src/components/agent/AgentChat.tsx` — overlay chat (hauteur dynamique, resizable, header avec toggle write/exec)
- [ ] `src/components/agent/AgentMessage.tsx` — markdown progressif (`react-markdown` + `remark-gfm` + `rehype-highlight`)
- [ ] `src/components/agent/ToolCallCard.tsx` — carte expandable + Approve/Reject inline
- [ ] `src/components/agent/ContextChips.tsx` — chips module(s) coché(s)
- [ ] `src/components/agent/AgentSettings.tsx` — page providers + comportement + historique + audit log
- [ ] `src/hooks/useAgentSession.ts` — état session + SSE EventSource + tool calls
- [ ] `src/hooks/useGlobalShortcut.ts` — capture ⌘K (priorité Monaco)
- [ ] `src/api/client.ts` — `agentChat`, `agentSessions`, `agentSettings`, `agentTestProvider`
- [ ] `src/styles/agent.css` — border-pulse couleur module, dim layer, drag-handle
- [ ] Routing/montage dans `App.tsx` (overlay racine, écoute changements `data-cat`)

**Tests** :
- [ ] `tests/test_agent_api.py` — SSE, providers (mocks), allowlist, persistence
- [ ] `tests/test_agent_tools.py` — dispatcher + safeguards (lecture seule, Strict mode)
- [ ] `tests/test_agent_storage.py` — SQLite CRUD, audit log append-only
- [ ] `src/components/agent/__tests__/AgentChat.test.tsx` — vitest streaming + tool call card
- [ ] `tests/e2e/agent/agent.spec.ts` — Playwright : ⌘K, send message, tool call approve, persistence après reload

**Critères d'acceptation** :
- ⌘K depuis n'importe quel module → widget ouvre avec chip module pré-sélectionné, border-pulse couleur correspondante
- 4 providers fonctionnels (mocks en CI), switch Settings sans reload
- Tool call lecture pure → exécution directe inline
- Tool call destructif → bouton Approuver/Refuser avant exécution
- Refresh navigateur → dernière session restaurée
- Esc ferme sans perdre l'historique (visible dans FAB tooltip)
- Audit log présent pour chaque tool call

**Estimation** : ~5j pleins (sprint complet, pas de découpage en phases)

### Sprint Idées post-22

- **Inline actions** : "✨ Explain this" clic-droit sur asm/fonction RE/payload pwn → ouvre chat pré-rempli (extension naturelle de Sprint 22)
- **CTF mode** : prompt système autonome qui résout un binaire CTF seul (réutilise tout Sprint 22)
- **Walk me through** : mode tutoriel step-by-step (variante system prompt)

### Sprint 21 — Mode RE phase 2 ⏸ PLANIFIÉ
- [ ] Build Docker image + valider decompile fonctionnel (rz-ghidra Kali)
- [ ] Décompilation pseudo-C via `r2ghidra pdg` côte à côte avec le désassemblage
- [ ] Synchronisation ASM ↔ C (clic ligne ASM → highlight C correspondant)
- [ ] Hex viewer virtualisé
- [ ] Xrefs panel
- [ ] Specs e2e RE phase 2 : `decompile`, `hex-view`, `xrefs`

### Sprint 22 — GitHub & release engineering ⏸ PLANIFIÉ (~9h, 3 phases)

> Anvil n'a quasiment aucun outillage GitHub standard. Ce sprint comble l'écart
> avant tout déploiement public ou première release. À découper si nécessaire.

**Décisions prises** : Licence **GPL v3** (ADR-021).

**Décisions à prendre avant de démarrer** :
- Email contact sécurité pour `SECURITY.md` (mailto: ou @PGP key)

#### Phase A — Indispensable (~2h, bloquant déploiement public)
- [ ] `LICENSE` à la racine
- [ ] `SECURITY.md` — politique de divulgation responsable, scope desktop/web,
      délai de réponse, contact (mail + PGP optionnel)
- [ ] `CONTRIBUTING.md` — pointer vers `CLAUDE.md` + workflow git + format de commit
      + lancement de la stack tests + comment ajouter un mode
- [ ] `.github/dependabot.yml` — auto-PR hebdo pour pip, npm, cargo, github-actions
      (groupage par écosystème, ignorer les majeures pour ne pas bruiter)

#### Phase B — Robustesse CI (~3h)
- [ ] `.github/ISSUE_TEMPLATE/bug.yml` — formulaire (mode, version, repro, logs)
- [ ] `.github/ISSUE_TEMPLATE/feature.yml` — formulaire (mode cible, use case, scope)
- [ ] `.github/ISSUE_TEMPLATE/security.yml` — redirige vers `SECURITY.md` (jamais d'issue publique)
- [ ] `.github/pull_request_template.md` — checklist (tests ajoutés, ADR, screenshot UI, breaking change)
- [ ] `CODEOWNERS` — auto-assign reviewers par chemin (`/src/` → frontend, `/backend/` → backend, `/.github/` → infra)
- [ ] Coverage reporting : `pytest --cov` → upload artifact + badge README
- [ ] `.pre-commit-config.yaml` — ruff format + ruff check + tsc --noEmit + prettier en local
- [ ] CI gating : promouvoir `e2e` + `audit` en `required` après 2 semaines verts ;
      ajouter job `build` (`npm run build` + `cargo check src-tauri`)
- [ ] Documenter les **branch protection rules** recommandées dans `CONTRIBUTING.md`
      (require PR review, require status checks, no direct push to main)

#### Phase C — Release engineering (~4h, à faire avant 1ère release publique)
- [ ] `CHANGELOG.md` automatisé via `git-cliff` ou `release-please`
- [ ] `.github/workflows/release.yml` — sur tag `v*` :
  - [ ] Build Tauri Linux (AppImage + .deb)
  - [ ] Build Tauri Windows (MSI) — conditionnel si Sprint runtime detector clos
  - [ ] Build + push Docker image sur `ghcr.io/dreggdwarf/anvil-backend:vX.Y.Z`
  - [ ] Crée GitHub Release avec assets + changelog auto
- [ ] Badges README : CI status, coverage %, license, latest release, Docker pulls
- [ ] (optionnel) Stale bot — auto-close issues inactives 60+ jours

#### Reportés / hors scope
- Bug bounty / disclosure program payant — trop tôt
- PR auto-labeling par chemin — gadget, peu de valeur sur repo solo
- Branch protection rules — config UI GitHub, pas dans le repo (juste documenté)

### Sprint 23 — Resilience & UX hardening ⏸ PLANIFIÉ (~3-4 jours)

> Ferme les angles morts opérationnels qui apparaissent dès qu'un user externe
> teste Anvil ou qu'un bug remonte. Pas de feature visible nouvelle, mais l'app
> devient *réellement utilisable au quotidien* au lieu de "marche si tu es prudent".

#### Indispensables (~2 jours)
- [ ] **Error boundaries React** — un crash dans un mode ne doit pas tuer toute l'app.
      `<ErrorBoundary>` par mode (ASM/Pwn/RE/...) + fallback racine. ~30 LOC, hook `useErrorBoundary`.
- [ ] **Logging structuré backend** — `structlog` ou `loguru` avec champs corrélés
      (`session_id`, `bridge_type`, `request_id`). Rotation `~/.anvil/logs/anvil-YYYY-MM-DD.log`
      capés à 100 MB. Niveau configurable via env `ANVIL_LOG_LEVEL`.
- [ ] **Capture erreurs frontend** — `window.onerror` + `unhandledrejection` →
      POST `/api/telemetry/error` avec opt-in (toggle dans settings).
      **Privacy-first** : pas de payload utilisateur, juste stack + URL + version.
- [ ] **Settings persistés (`localStorage`)** — hook `usePersistedState<T>(key, default)`
      réutilisable. Persiste : theme, mode actif, col/row widths, breakpoints,
      draft du code éditeur (auto-save debounce).

#### Important (~1.5 jours, à faire dans le même sprint pour cohérence UX)
- [ ] **Toast notifications** — composant `<Toaster>` global, hook `useToast()`.
      Remplace les `log('error', ...)` qui finissent dans le terminal en bas
      par une notif visible quel que soit l'écran utilisateur.
- [ ] **Loading states uniformes** — composant `<Spinner>` + skeleton screens
      pour les listes (FilterableList, panels). Aujourd'hui mix de "compiling..."
      texte / spinner FontAwesome / rien.
- [ ] **Auto-save éditeur** (localStorage debounced 2s) — recovery après crash navigateur

#### Optionnel / à étoffer ensuite (~0.5 jour si combiné)
- [ ] **Page `/diagnostics`** — status backend + versions outils détectés + sessions
      actives + capabilities. Accessible via raccourci ou status bar. Aide debug user.
- [ ] **Bundle analyzer** (`rollup-plugin-visualizer`) — un job CI qui produit
      un treemap pour identifier ce qui pèse dans les 608 KB. Output en artifact.
- [ ] **Cleanup workspace orphelins** — script `cleanup_orphans.py` lancé au start
      lifecycle (workspaces sans session active + > 24h)

#### Reportés / triggers d'activation
- **a11y (Phase H)** — audit WCAG, navigation clavier complète, ARIA. Activer si
  user externe / contributeur a11y signale un blocage, ou avant release publique.
- **i18n (Phase H)** — strings actuellement mix FR/EN. Activer quand le projet vise
  un public anglophone explicitement.
- **Plugin system (Phase H)** — extension third-party. Activer si demande forte.

### Sprint 24 — Contexte partagé inter-modules ⏸ PLANIFIÉ

> Fondement QoL de la vision v2. Sans ce sprint, changer de module = recommencer à zéro.

- [ ] `SessionContext` React (binary, arch, source, workspace_id) dans Context API global
- [ ] Persistance sur changement de mode (ASM → Pwn → RE = même binaire chargé)
- [ ] Toasters globaux : `<Toaster>` + `useToast()` — compilation réussie/échouée, session expirée, archi détectée
- [ ] Actions rapides contextuelles : BOF pattern détecté → "Générer cyclic" inline, ELF trouvé → "Ouvrir en RE", firmware extrait → "Analyser les ELF"

### Sprint 25 — GDB remote dans ASM ⏸ PLANIFIÉ

> Extension d'ASM, pas un nouveau module — même protocole RSP.

- [ ] Remplacer `gdb` → `gdb-multiarch` dans le bridge
- [ ] Sélecteur d'archi dans l'UI ASM (x86, ARM, MIPS, PowerPC)
- [ ] Connexion GDB remote via protocole RSP : `qemu-arm-static -g 1234`, `gdbserver`, OpenOCD
- [ ] Cross-compilers : `arm-linux-gnueabihf-gcc`, `mips-linux-gnu-gcc` dans `CompilationBridge`
- [ ] Bare metal via OpenOCD (gratuit si remote est implémenté — même protocole)
- [ ] Specs e2e : `remote-connect`, `cross-compile`, `qemu-step`

### Sprint 26 — Firmware pipeline ⏸ PLANIFIÉ

> Pipeline 4 étapes : détection → extraction → triage → passerelle.

- [ ] Visualisation entropie couleur (zones plaintext / compressées / chiffrées)
- [ ] Magic bytes, format, archi probable détectés automatiquement
- [ ] Binwalk récursif (`-eM`) orchestré visuellement — arbre d'extraction par niveau
- [ ] Support SquashFS, JFFS2, CRAMFS (unsquashfs, jefferson)
- [ ] Triage automatique firmwalker-like : credentials hardcodés, clés privées, services dangereux, IPs, tokens — classés high/med/low
- [ ] File browser du filesystem extrait avec badges findings sur fichiers intéressants
- [ ] ELF trouvé → "Ouvrir en RE" ou "Ouvrir en Pwn" en un clic
- [ ] Crypto basique : XOR bruteforce, détection AES-CBC IV fixe
- [ ] `firmware_scan()` et `firmware_extract()` → dicts structurés (requis ADR-022 MCP)

### Sprint 27 — Wire (pcap + Modbus Repeater) ⏸ PLANIFIÉ

> Wireshark affiche les trames ICS ; Anvil les rend exploitables.

**3 modes par ordre de priorité** :

**Phase 1 — pcap** (zéro dépendance hardware, testable offline) :
- [ ] Drop `.pcap`/`.pcapng` → décodage humain immédiat (pas des bytes bruts)
- [ ] Filtrage (`modbus.func == 3`, etc.)
- [ ] Code couleur : sent / recv / error
- [ ] Champs nommés et expliqués ("function code 0x06 — Write Single Register")
- [ ] Notes contextuelles automatiques ("Write sans authentification détecté")
- [ ] Vue hex synchronisée

**Phase 2 — TCP Repeater** :
- [ ] Repeater : clic trame capturée → importée pré-remplie → modifier champs → envoyer
- [ ] Replay ×N, fuzzing de registres
- [ ] Connexion TCP (host:port) — testable avec simulateur logiciel Modbus

**Phase 3 — UART/RTU** (en dernier) :
- [ ] Série physique via Tauri serial port natif
- [ ] `wire_*` tools → dicts structurés (requis ADR-022 MCP)

### Sprint 28 — MCP server ⏸ PLANIFIÉ (après que les 5 modules soient prêts)

> Voir ADR-022 pour le contrat complet. Ce sprint est le dernier de la roadmap.

- [ ] `pip install -e "backend/[mcp]"` — groupe optionnel pyproject.toml
- [ ] `mcp/server.py` standalone (stdio + SSE) — client HTTP du backend FastAPI
- [ ] `mcp/tools/` : session, asm (gdb_*), pwn (pwn_*), re (rizin_*), firmware (firmware_*), wire (wire_*)
- [ ] `mcp/resources/session.py` : `session://list`, `session://{id}/binary`, `session://{id}/workspace`
- [ ] `mcp/prompts/pipelines.py` : `exploit_pipeline`, `firmware_audit`, `ctf_binary`
- [ ] Intégration Claude Desktop + Cursor testée
- [ ] Tests : stubs vérifient toutes les signatures, smoke test pipeline complet

---

## Sprints futurs sans planning fixe (déclencheurs documentés)

### Hardening sécu runtime ⏸ TRIGGER : déploiement web ou multi-user
> Aucun de ces items n'a de valeur en mode desktop solo localhost.
- Sandbox subprocess (`nsjail` / `firejail`) pour isoler GDB/pwntools/gcc par session
- Authentification utilisateur (au-delà du WS token de session ADR-016)
- Quotas par user (CPU, RAM, sessions, subprocesses)
- Audit trail des actions sensibles (compile, write_memory, exec)
- TLS WebSocket (`wss://`) + cert management
- Signature/integrity check des binaires uploadés (anti-tampering workspace)

### Qualité code avancée ⏸ TRIGGER : >2 contributeurs ou bugs subtils répétés
- `mypy --strict` côté Python (type-checking réel, pas juste hints)
- `hypothesis` (property-based testing) — sanitization stress-tested avec inputs random
- `mutmut` (mutation testing) — détecter les tests de complaisance
- OpenAPI versionné + Postman collection (onboarding contributeurs)

### Infrastructure SaaS ⏸ TRIGGER : passage à un service hébergé
- Prometheus/Grafana metrics
- Backup/export workspaces
- Multi-user shared instance avec isolation forte
- Billing/quotas si modèle commercial

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
