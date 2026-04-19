# Système Multi-Agents IA — Anvil

## Fonctionnement

Claude Code est l'orchestrateur (le **Manager**). Aucune clé API supplémentaire — utilise votre abonnement Claude Code.

```
  Vous: "Ajouter le mode RE"
       │
       ▼
  Manager (Claude Code)
  ├── Phase 1 : Clarifie la demande (2-4 questions)
  ├── Phase 2 : Sprint plan à valider
  ├── Phase 3 : Exécute les agents (séquentiel/parallèle)
  ├── Phase 4 : Code review automatique
  └── Phase 5 : Documentation & mémoire
```

## Les 12 agents

### Agents de construction

| Agent | Modèle | Responsabilité |
|-------|--------|----------------|
| @pm | haiku | Specs, user stories, critères d'acceptation |
| @architect | sonnet | Architecture, patterns, dépendances |
| @rust | sonnet | Shell Tauri, IPC, subprocess, packaging |
| @backend | sonnet | FastAPI, bridges Python (GDB, rizin, pwntools) |
| @frontend | haiku | React, composants, panels, éditeur, modes |
| @devops | haiku | Docker, CI/CD, packaging desktop |

### Agents de review (phase 4 automatique)

| Agent | Modèle | Responsabilité | Quand |
|-------|--------|----------------|-------|
| @security | sonnet | Audit OWASP, injection commandes, sandbox | Toujours |
| @testing | sonnet | Couverture de tests, cas limites | Toujours |
| @quality | sonnet | Complexité, nommage, DRY, SOLID | Toujours |
| @performance | sonnet | Latence debug, bundle size, Canvas fps | Backend/frontend modifié |
| @a11y | sonnet | WCAG 2.1 AA, contraste, ARIA | Frontend modifié |
| @pentester | sonnet | Tests d'intrusion (localhost uniquement) | Sur demande |

## Fichiers

```
ai/
├── agents/          # Un YAML par agent (rôle, scope, rules, prompt)
│   ├── pm.yml
│   ├── architect.yml
│   ├── rust.yml
│   ├── backend.yml
│   ├── frontend.yml
│   ├── devops.yml
│   ├── security.yml
│   ├── testing.yml
│   ├── quality.yml
│   ├── performance.yml
│   ├── a11y.yml
│   └── pentester.yml
├── workflows/
│   ├── new_feature.yml    # Workflow complet pour une nouvelle feature
│   └── code_review.yml    # Reviewers par contexte (core/rust/backend/frontend/on-demand)
└── context/
    ├── sprint_log.md      # Historique des sprints (mis à jour automatiquement)
    ├── decisions.md       # ADR — décisions d'architecture
    └── backlog.md         # Tâches futures identifiées
```

## Convention Question Relay

Si un agent a besoin d'une décision utilisateur, il termine son output par :

```
QUESTIONS:
1. [question précise]
BLOCKER: true  ← si impossible de continuer sans réponse
```

Le Manager consolide les questions et les pose en une seule fois avant de continuer.

## Différences vs Rails-Boilerplate

| Aspect | Rails-Boilerplate | Anvil |
|--------|-------------------|-------|
| Stack | Rails + React + Inertia | Tauri (Rust) + React + FastAPI (Python) |
| Agent `database` | Migrations SQL, ActiveRecord | **Remplacé par `rust`** (pas de DB) |
| Communication | Inertia props | WebSocket + IPC Tauri |
| Sandbox | N/A | nsjail (web), subprocess isolation (desktop) |
| Modes | N/A | 6 modes (ASM, RE, Pwn, Debug, FW, Protocols) |
| Outils externes | Gems | GDB, rizin, pwntools, binwalk, QEMU, pymodbus... |
