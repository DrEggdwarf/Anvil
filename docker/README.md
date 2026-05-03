# Anvil — Docker

## Backend image

Image FastAPI + tous les outils bas niveau préinstallés (rizin, rz-ghidra,
binwalk, gdb, nasm/gcc, pwntools).

### Build

```bash
# From repo root
docker build -f docker/Dockerfile.backend -t anvil-backend:dev .
```

### Run

```bash
docker run --rm -p 8000:8000 anvil-backend:dev
# Health check
curl http://localhost:8000/api/health
```

### Why Debian + multi-stage build ?

- **Debian trixie-slim** = base propre, légère (~80 MB), neutre — pas de "Anvil tourne dans Kali"
- **Stage 1 (builder)** : compile rz-ghidra v0.8.0 contre librizin-dev (depuis sources upstream, pinned tag)
- **Stage 2 (runtime)** : seuls les `.so` plugins sont copiés. Image finale ≈ 250 MB
- Premier build ~10 min (compilation Ghidra sleigh decompiler) ; rebuilds ultérieurs cachés

Source rizin : repo OBS officiel `home:RizinOrg/Debian_Testing` — packages signés
maintenus par l'équipe rizin elle-même, alignés avec la version stable upstream.

Alternatives écartées :
- **Kali base** : ~700 MB, surface d'attaque large, mauvais signal pour un produit pédagogique
- **Debian sans rz-ghidra** : pseudo-code indisponible (le frontend masque l'onglet auto)
