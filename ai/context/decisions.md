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

## ADR-012b : Modbus full FC coverage (protocol bridge)

**Date** : 19 avril 2026
**Statut** : Accepté
**Note** : ce numéro a temporairement collidé avec ADR-012 (Docker) écrit plus tard ;
renommé `012b` pour préserver les références internes existantes sans renuméroter.

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

---

## ADR-015 : CSP stricte Tauri + CORS restreint

**Date** : 28 avril 2026
**Statut** : Accepté (Sprint 14)

**Contexte** : Audit post-merge a relevé `csp: null` dans `tauri.conf.json` et `cors_origins=["*"]` dans `config.py`. En desktop local mono-user le risque est limité, mais le projet vise Docker localhost et un éventuel mode web. Une XSS dans la WebView (Monaco / xterm / sources C affichés) combinée à un WebSocket sans auth = compromission complète.

**Décision** :
- CSP stricte dans `tauri.conf.json` :
  ```
  default-src 'self';
  script-src 'self' 'wasm-unsafe-eval';
  connect-src 'self' http://127.0.0.1:8000 ws://127.0.0.1:8000;
  style-src 'self' 'unsafe-inline';
  img-src 'self' data:;
  ```
- `cors_origins` restreint à `["http://localhost:1420", "tauri://localhost"]` par défaut, override possible via env `ANVIL_CORS_ORIGINS`.
- `allow_credentials=False` conservé (déjà le cas).

**Conséquences** :
- XSS via Monaco/xterm bloquée même si une CVE upstream apparaissait
- DNS rebinding et CSRF cross-site fermés
- Mode web futur devra explicitement allowlister son origine

---

## ADR-016 : WebSocket auth via session token

**Date** : 28 avril 2026
**Statut** : Accepté (Sprint 14)

**Contexte** : `/ws/{session_type}/{session_id}` accepte toute connexion sans vérifier ni l'existence de la session ni le `session_type` correspondant au bridge. Sur un poste local mono-user c'est OK ; mais dès qu'il y a Docker partagé, conteneur multi-user, ou XSS dans la WebView, n'importe qui sur localhost:8000 peut piloter une session GDB.

**Décision** :
- Au `POST /api/sessions`, générer `session.token = secrets.token_hex(16)` (32 chars).
- Le token est retourné UNE SEULE FOIS au create.
- Le WS exige `?token=...` dans l'URL ; le handler vérifie `session.token == query_token` avant `accept()`.
- Vérification de `Origin` header contre `cors_origins`.
- Vérification que `session_type` matche le bridge attaché à la session.

**Conséquences** :
- Compromission cross-process locale fermée
- Le frontend doit conserver le token côté React state (pas de refresh = re-connect impossible — acceptable, le Tauri shell garde la mémoire)
- En cas de fuite token = compromission jusqu'à expiration session (1h)

---

## ADR-017 : Pipeline de compilation unifié — `CompilationBridge` source unique

**Date** : 28 avril 2026
**Statut** : Accepté (Sprint 14)

**Contexte** : Le merge `asm-dev → main` a introduit `api/pwn.py:compile_source` qui ré-implémente nasm/gcc/g++/rustc/go en parallèle de `bridges/compilation.py`. Conséquences : deux jeux de flags sécurité divergents, deux error parsers, deux mappings extension→langue, deux validations de path. L'audit Security a flagué cela comme cause racine de findings A1, A2 (path arbitraire + Rust/Go avec network).

**Décision** :
- `CompilationBridge` est l'unique point d'entrée pour toute compilation.
- `api/pwn.py:compile_source` délègue à `CompilationBridge.compile_<lang>` (ajouter `compile_cpp`, `compile_rust`, `compile_go` au bridge).
- Tous les paths passent par `WorkspaceManager.get_file_path(session_id, basename)` — plus de `Path` manuel dans `api/pwn.py`.
- `_LANG_MAP` (extension→langue) déplacé dans le bridge ; le frontend reçoit la langue détectée par l'API.
- Rust/Go opèrent en mode offline forcé (`CARGO_NET_OFFLINE=1`, `GOFLAGS=-mod=vendor`) tant qu'un sandbox réseau (nsjail/Docker) n'est pas en place.

**Conséquences** :
- Une seule source de vérité pour les flags sécu (`-fstack-protector-strong`, `-D_FORTIFY_SOURCE=2`, `-pie`, `-Wl,-z,relro,-z,now`)
- Path traversal/symlink centralisé via `WorkspaceManager`
- Rust/Go n'ouvrent plus de connexion réseau au build (anti-SSRF)
- Sprint 14 fix #3 ferme A1, A2, Pent#4, Pent#6

---

## ADR-018 : Pattern `useXxxSession` + seuil dur 400 LOC frontend

**Date** : 28 avril 2026
**Statut** : Accepté (Sprint 15)

**Contexte** : `useAnvilSession.ts` (651 L) et `ReferenceModal.tsx` (877 L) violent la règle Quality des 400 L. Mélangent plusieurs responsabilités : parsing GDB/MI + lifecycle + step + memory + compile pour le hook ; 6 vues mode-spécifiques pour le modal.

**Décision** :
- **Seuil dur** : tout fichier React > 400 L doit être éclaté ; > 500 L est bloquant pour merge.
- **Pattern hook session** : chaque mode introduit un `useXxxSession` strictement responsable du lifecycle session + appels API. Les sous-domaines (parsing, stepping, memory, compile) vivent dans `hooks/<mode>/<domain>.ts` et sont composés par le hook racine.
- Contrat minimal d'un `useXxxSession` : `{ sessionId, ensureSession(), destroySession(), log[], clearLog() }`.

**Conséquences** :
- Hooks plus petits = testables individuellement (vitest)
- Re-renders limités par découpage des states dans des hooks dédiés
- ReferenceModal éclaté par mode = lazy-load possible par tab actif

---

## ADR-019 : `pyproject.toml` source unique des deps Python

**Date** : 28 avril 2026
**Statut** : Accepté (Sprint 16)

**Contexte** : `backend/requirements.txt` (bundle complet, versions divergentes : pwntools `>=4.0`, binwalk `>=2.3`) coexiste avec `backend/pyproject.toml` (segmenté en optional-deps, versions à jour : pwntools `>=4.12`, binwalk `>=2.4`). Risque de régression lors d'un `pip install -r requirements.txt` qui downgrade les outils.

**Décision** :
- Supprimer `backend/requirements.txt` et `backend/requirements-dev.txt`.
- README pointe sur `pip install -e "backend/[dev,re,pwn,firmware,protocols]"` pour install complète.
- CI inchangée (déjà sur `pip install -e .[dev]`).

**Conséquences** :
- Une seule source de vérité, plus de drift de versions
- Le `pip install -r` historique disparaît — léger breaking change pour devs qui suivent l'ancien README
- Préparation propre pour le Dockerfile (ADR-012) qui consommera `pyproject.toml`

---

## ADR-020 : Portability discipline — Linux-first, Windows-deferred

**Date** : 28 avril 2026
**Statut** : Accepté (Sprint 17)

**Contexte** : Anvil cible un déploiement Linux-first avec un éventuel support Windows
(natif via WSL2 ou via Docker — voir ADR-012 et future ADR sur le runtime detector).
Le choix du runtime Windows n'a **pas besoin d'être tranché maintenant** car il s'agit
d'une décision tactique (~150 LOC Rust + 1 Dockerfile) sans impact structurant sur
l'archi 3-couches existante.

**Décision** : Continuer Linux-first sans bloquer la roadmap, mais s'imposer 5 règles
de portabilité pour ne pas se peindre dans un coin :

1. **Pas de path Linux hardcodé dans le code applicatif.** Pas de `/proc/...`,
   `/sys/...`, `/dev/...` en dur. Toujours passer par les outils (gdb, rizin)
   qui font eux-mêmes l'abstraction.
2. **`SubprocessManager` est l'unique chemin pour spawn un process.** Jamais
   `os.system`, `subprocess.run` direct, ni shell scripts inline.
3. **`src-tauri/src/lib.rs` reste minimal** (~70 LOC actuellement). Pas de plugin
   Rust natif qui ferait des syscalls Linux directs (ptrace, `/proc` parsing).
4. **Outils accessibles via PATH.** Jamais hardcoder `/usr/bin/gdb` ni
   `/usr/local/bin/...` — juste `gdb`, `nasm`, `gcc`, etc.
5. **Capabilities Tauri minimales** (`core:default` + `opener:default` aujourd'hui).
   Pas de `tauri-plugin-shell` ni autre plugin OS-specific.

**Features qui forceraient à trancher le runtime** :
- Plugin Tauri natif Rust avec syscalls Linux → bloquerait Windows pur
- Hardware temps réel (USB-RS485, USB-JTAG, SDR) en feature standard → demande
  passthrough Docker `--device` ou drivers Windows natifs
- Heavyweight binary integré (Ghidra/IDA) → souvent licensing Linux-only

Aucun de ces points n'est dans la roadmap actuelle (Phases C-G du backlog).

**Conséquences** :
- La roadmap Linux-first peut continuer sans bloqueur jusqu'au prochain
  packaging public Windows
- Quand le runtime Windows sera tranché (probablement Sprint 21+ avec WSL/Docker),
  zéro régression à corriger dans le code applicatif tant que les 5 règles ont été
  respectées
- Cette discipline est **vérifiable mécaniquement** : `grep -rn "/proc/\|/sys/\|/dev/\|/usr/bin"`
  dans `backend/app/` et `src/` doit rester vide hors commentaires.

---

## ADR-021 : Vision v2 — "Le Burp Suite du bas niveau"

**Date** : 29 avril 2026
**Statut** : Accepté

**Contexte** : Anvil a grandi sprint par sprint sans vision formalisée. Risque de devenir une collection d'outils disparates plutôt qu'un produit cohérent.

**Décision** :
- Anvil = wrapper généraliste, beau et fonctionnel, sur les outils bas niveau existants (GDB, rizin, pwntools, binwalk)
- UX = feature principale — zéro friction, infos critiques toujours visibles, actions fréquentes en un clic
- 5 modules précisément, pas un de plus : ASM, Pwn, RE, Firmware, Wire
- Fil rouge : pipeline d'attaque d'un système embarqué — dump firmware → analyse → identification vulns → exploitation
- Linux/macOS uniquement assumé (ADR-020), Windows reporté
- Licence GPL v3 (cohérence écosystème rizin LGPL v3, protège contre distribution propriétaire)
- Wire remplace le module Protocols — focus pcap + décodage humain + Repeater Modbus (Wireshark lit, Anvil interagit)
- Module Debug retiré — ASM couvre déjà le debug local complet ; GDB remote = extension d'ASM (même protocole RSP)
- RE en 3 phases : navigable texte (phase 1) → décompilateur (phase 2) → CFG/call graph (phase 3)

**Conséquences** :
- Firmware pipeline = 4 étapes : détection → extraction récursive → triage automatique → passerelle RE/Pwn
- GDB remote dans ASM débloque QEMU, bare metal, OpenOCD (protocole RSP commun, pas de nouveau module)
- RE phase 1 = valeur immédiate (~1 semaine) ; phases 2-3 = chantier progressif
- Toasters + contexte partagé inter-modules = couche QoL fondamentale qui colle les modules ensemble
- Anvil n'est pas un concurrent de IDA, Ghidra, pwntools, rizin — c'est un wrapper qui les rend accessibles

---

## ADR-022 : MCP server — contrat défini maintenant, implémentation en dernier

**Date** : 29 avril 2026
**Statut** : Accepté

**Contexte** : Un serveur MCP permettrait à Claude d'orchestrer le pipeline firmware→RE→Pwn en autonomie ("charge ce firmware, analyse-le, génère un exploit"). Mais implémenter le MCP avant que les 5 modules existent serait prématuré.

**Décision** :
- Architecture : serveur standalone Python (SDK `mcp`, stdio ou SSE) → client HTTP du backend FastAPI
- Aucune modification de FastAPI — le MCP server est un consumer du backend REST existant
- Contrat complet défini maintenant (tools, resources, prompts), implémenté en dernier (Sprint 28)
- Règle architecturale pour chaque nouveau module : tout endpoint destiné MCP retourne un dict structuré (pas de string brute), avec champ `summary` LLM-friendly
- Structure : `mcp/server.py`, `mcp/tools/{session,asm,pwn,re,firmware,wire}.py`, `mcp/resources/session.py`, `mcp/prompts/pipelines.py`, `mcp/client.py`

**Conséquences** :
- Sessions UUID existantes = MCP-compatibles sans modification
- Fix immédiat : `rizin.analyze()` et `decompile()` devront retourner des dicts (actuellement strings brutes) — à corriger lors de l'implémentation RE
- Tools exposés : `gdb_*`, `rizin_*`, `pwn_*`, `firmware_*`, `wire_*`, `session_*`
- Resources : `session://list`, `session://{id}/binary`, `session://{id}/workspace`
- Prompts orchestrés : `exploit_pipeline` (firmware→RE→Pwn), `firmware_audit`, `ctf_binary`
- Dépendance optionnelle : `pip install -e "backend/[mcp]"` (groupe `mcp` dans pyproject.toml)
