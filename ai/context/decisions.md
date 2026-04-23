# Architecture Decision Records (ADR) — Anvil

## ADR-001 : Tauri v2 comme shell desktop

**Date** : 18 avril 2026
**Statut** : Accepté

**Contexte** : Anvil nécessite un accès filesystem, réseau et ports série pour les modes RE, Pwn, Firmware et Protocols. Un navigateur web ne peut pas fournir ces accès.

**Décision** : Utiliser Tauri v2 (Rust) comme shell desktop. Le frontend React est embarqué dans le WebView natif. Le backend FastAPI est lancé comme subprocess.

**Conséquences** :
- App légère (~15 MB vs ~150 MB Electron)
- Pas de Chromium embarqué (WebView natif)
- Le Rust ne contient pas de logique métier — c'est un shell
- Double déploiement : web (mode ASM) + desktop (tous les modes)

---

## ADR-002 : rizin + r2ghidra pour le reverse engineering

**Date** : 18 avril 2026
**Statut** : Accepté

**Contexte** : Le mode RE nécessite un moteur de décompilation. Ghidra (Java, ~500 MB, JVM) vs rizin + r2ghidra (~50 MB, natif, JSON API, startup 1s).

**Décision** : Utiliser rizin + r2ghidra via rzpipe (Python binding). Même moteur de décompilation que Ghidra, mais natif et léger.

**Conséquences** :
- API JSON native (rzpipe) → pas de parsing custom
- Startup < 1s vs Ghidra ~10-30s
- ~50 MB vs ~500 MB
- Toutes les commandes r2 disponibles via pipe

---

## ADR-003 : Agent `rust` remplace `database` dans le système multi-agent

**Date** : 18 avril 2026
**Statut** : Accepté

**Contexte** : Le boilerplate Rails avait un agent `database` pour les migrations SQL. Anvil n'a pas de base de données — les données sont en mémoire (sessions GDB, RE) ou sur le filesystem.

**Décision** : Remplacer l'agent `database` par un agent `rust` spécialisé dans le shell Tauri (IPC, subprocess, packaging).

**Conséquences** :
- 12 agents total (pm, architect, rust, backend, frontend, devops, security, testing, quality, performance, a11y, pentester)
- L'agent `rust` couvre : IPC Tauri, subprocess FastAPI, file dialogs, serial port, packaging

---

## ADR-004 : Architecture 3 couches

**Date** : 18 avril 2026
**Statut** : Accepté

**Contexte** : Anvil a 3 langages (Rust, TypeScript, Python) avec des responsabilités distinctes.

**Décision** :
```
src-tauri/ (Rust)  — Shell : IPC, subprocess, file dialogs, serial, packaging
src/ (React/TS)    — UI : composants, panels, éditeur, modes, WebSocket client
backend/ (Python)  — Logique : FastAPI, bridges (GDB, rizin, pwntools, binwalk, pymodbus)
```

**Communication** :
- Frontend ↔ Backend : WebSocket (localhost, streaming debug/console) + REST (requêtes simples)
- Tauri ↔ Frontend : IPC invoke (file dialogs, serial port, dependency check)

**Conséquences** :
- Séparation claire des responsabilités
- Le web mode ne charge que le frontend + backend (pas de Tauri)
- Le desktop mode ajoute Tauri comme shell

---

## ADR-005 : CSS pure avec prefix `anvil-`

**Date** : 18 avril 2026
**Statut** : Accepté

**Contexte** : ASMBLE utilisait CSS pure avec prefix `asm-` (90+ variables, thème dark/light). Pas de CSS-in-JS, pas de Tailwind.

**Décision** : Conserver l'approche CSS pure. Renommer le prefix en `anvil-`. Design tokens via CSS custom properties.

**Conséquences** :
- Cohérence avec ASMBLE (migration facilitée)
- Performance (pas de runtime CSS-in-JS)
- Thème dark/light via variables CSS

---

## ADR-006 : API Engine First — Backend avant Frontend

**Date** : 19 avril 2026
**Statut** : Accepté

**Contexte** : Anvil est un wrapper d'outils (GDB, rizin, pwntools, binwalk, pymodbus, nasm, gcc).
Chaque mode UI dépend d'un bridge backend fiable. Un backend fragile = une app inutilisable.

**Décision** : Construire le moteur d'API en priorité absolue (Phase 0, Sprints 1-6) avant toute feature UI.
L'architecture backend doit être :
- **Modulaire** : core/ bridges/ sessions/ api/ models/
- **Testée** : 90%+ coverage sur le code critique, mocks pour tous les outils externes
- **Robuste** : subprocess lifecycle managé, sessions avec timeout, cleanup auto
- **Typée** : Pydantic v2 partout, exception hierarchy, error middleware
- **Sécurisée** : input validation, rate limiting, sandbox (mode web)

**Principes** :
1. BaseBridge ABC → chaque bridge hérite et implémente le même contrat
2. Session Manager → isolation des sessions, pas de state global partagé
3. Subprocess Manager → aucun process orphelin, jamais
4. WebSocket protocol typé → messages JSON avec schema, pas de strings libres
5. Tests avec mocks → CI tourne sans GDB/rizin/pwntools installés

**Conséquences** :
- Le frontend ne peut pas avancer tant que les routes API n'existent pas
- Tous les bridges suivent le même pattern (DRY, prédictible)
- La CI est autonome (mocks, pas de dépendances système)
- L'API est documentée OpenAPI dès le départ

---

## ADR-007 : rizin_bridge.py (pas re_bridge.py)

**Date** : 19 avril 2026
**Statut** : Accepté

**Contexte** : Le sprint plan initial nommait le bridge rizin `re_bridge.py` (pour Reverse Engineering). Mais le bridge wrappe spécifiquement rizin/rzpipe, pas un concept abstrait de RE.

**Décision** : Nommer le fichier `rizin_bridge.py` pour être cohérent avec `gdb_bridge.py` (nommé d'après l'outil, pas le mode).

**Conséquences** :
- Cohérence : chaque bridge porte le nom de l'outil wrappé (gdb_bridge, rizin_bridge, compilation)
- Les routes REST restent sous `/api/re/` (nom du mode) — distinction bridge/API

---

## ADR-008 : Tests 100% mocks — CI sans outils externes

**Date** : 19 avril 2026
**Statut** : Accepté

**Contexte** : Les bridges wrappent des outils système (gdb, rizin, nasm, gcc, readelf, nm, objdump, ldd). La CI ne peut pas installer tous ces outils.

**Décision** : Tous les tests utilisent des mocks complets. Aucun test ne dépend d'un outil système installé. pygdbmi.GdbController, rzpipe.open(), SubprocessManager.execute() sont systématiquement mockés.

**Conséquences** :
- CI rapide (~2s pour 388 tests)
- Aucune dépendance système en CI
- Les tests valident la logique du bridge, pas l'outil externe
- Tests d'intégration réels possibles en local mais pas en CI

---

## ADR-009 : Routes REST /api/re/ pour le bridge rizin

**Date** : 19 avril 2026
**Statut** : Accepté

**Contexte** : Le bridge s'appelle `rizin_bridge.py` mais les routes API doivent-elles être `/api/rizin/` ou `/api/re/` ?

**Décision** : Routes sous `/api/re/{session_id}/*` — le préfixe API correspond au **mode utilisateur** (Reverse Engineering), pas à l'outil sous-jacent.

**Conséquences** :
- Cohérence avec `/api/gdb/` (même pattern : mode = préfixe API)
- Si on remplace rizin par un autre moteur RE, les routes ne changent pas
- ~70 endpoints couvrent : analyse, fonctions, disassembly, décompilation, strings, imports/exports, symboles, sections, segments, relocations, xrefs, search, flags, comments, ESIL, graphs, projets, patching

---

## ADR-010 : Binary data I/O en hex strings (pwntools bridge)

**Date** : 19 avril 2026
**Statut** : Accepté

**Contexte** : pwntools manipule des bytes (shellcode, payloads, packing). JSON REST ne supporte pas le binaire brut.

**Décision** : Toutes les données binaires sont transmises en hex strings (e.g. "9090" pour `\x90\x90`). Le bridge convertit hex→bytes en entrée et bytes→hex en sortie.

**Conséquences** :
- Compatible JSON sans encodage base64 (plus lisible)
- Le frontend peut afficher les hex directement
- Cohérent pour tous les types : shellcode, payloads, ELF data, packed values

---

## ADR-011 : binwalk v3 CLI préféré, v2 Python fallback

**Date** : 19 avril 2026
**Statut** : Accepté

**Contexte** : binwalk v3 est une réécriture Rust sans API Python. v2 a un module Python. Les deux sont en usage.

**Décision** : Le firmware bridge auto-détecte la version au start(). v3 CLI avec `--log=-` (JSON output) est préféré. Si v3 absent, fallback sur v2 Python `import binwalk`.

**Conséquences** :
- Fonctionne avec v2 ou v3 sans configuration
- v3 JSON output est plus fiable que le parsing v2
- 111 signatures supportées (v3)

---

## ADR-012 : Docker container pour cross-platform (Tauri + Docker)

**Date** : 23 avril 2026
**Statut** : Planifié

**Contexte** : Les outils backend (nasm, ld, gdb, rizin, pwntools, binwalk) sont Linux-only. Un binaire Tauri cross-platform ne suffit pas — le backend ne tourne pas nativement sur Windows.

**Décision** : Packager le backend FastAPI + tous les outils dans un container Docker Linux. Tauri lance le container au démarrage (`docker run`) et le kill à la fermeture. Le frontend communique toujours via localhost:8000.

**Architecture** :
```
Tauri (natif Win/Linux) → docker run anvil-backend → FastAPI + outils Linux
React frontend ↔ localhost:8000 (HTTP/WS)
```

**Conséquences** :
- Fonctionne identiquement sur Linux et Windows (Docker Desktop + WSL2)
- Prérequis Windows : Docker Desktop installé
- Image Docker ~500 MB (une seule fois, pull au premier lancement)
- Startup container ~2s
- Garde les features Tauri natives (file dialogs, serial port)
- Un seul Dockerfile à maintenir

---

## ADR-012 : Modbus full FC coverage (protocol bridge)

**Date** : 19 avril 2026
**Statut** : Accepté

**Contexte** : ICS/OT security testing nécessite un accès complet au protocole Modbus, pas seulement read/write basiques.

**Décision** : Implémenter TOUS les function codes Modbus : FC01-07, FC11-12, FC15-17, FC20-24, FC43 (MEI), FC08 (diagnostics 0x00-0x15). Plus : data type conversion, scan discovery, simulator server.

**Conséquences** :
- Couverture complète pour pentesting ICS
- Write operations marquées ⚠️ (danger pour systèmes réels)
- Simulator intégré pour tests sans hardware

---

## ADR-013 : Input sanitization at bridge level

**Date** : 19 avril 2026
**Statut** : Accepté

**Contexte** : GDB/MI and Rizin accept commands that can escape to host shell (GDB `shell`, `-interpreter-exec console "shell cmd"`; Rizin `!cmd`). User input is f-stringed into these commands.

**Décision** : Sanitize at bridge level (not API routes). Central `core/sanitization.py` module with validators for GDB, Rizin, paths, GCC flags. Bridges call sanitizers before executing. `$` allowed in GDB (needed for `$rax`), `|` allowed (only `pipe` command blocked). `;`, `` ` ``, `\n` blocked universally.

**Conséquences** :
- Defense in depth — sanitization applies whether called from REST, WS, or directly
- No false positives on valid GDB expressions
- Path validation blocks /etc, /proc, /sys, /dev + enforces allowed_dirs

---

## ADR-014 : slowapi rate limiting + subprocess concurrency semaphore

**Date** : 19 avril 2026
**Statut** : Accepté

**Contexte** : No rate limiting was active despite config existing. SubprocessManager had no concurrency limit.

**Décision** : Add slowapi middleware (global 120/min from config). Add asyncio.Semaphore(20) in SubprocessManager to cap concurrent subprocesses. Enforce output size truncation at `subprocess_max_output_bytes`.

**Conséquences** :
- Prevents API abuse and DoS via subprocess flooding
- Output truncation prevents OOM from large process output
- Semaphore released in both kill() and execute() cleanup paths
