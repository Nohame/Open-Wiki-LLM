# 2026-05-12 — Initialisation du projet

## Contexte

Mise en place de la structure complète du projet OpenWikiLLM (Task 1 / 6).

## Ce qui a été fait

- Création de la structure des dossiers `backend/app/{api,core,models,services,storage,mcp}`
- Configuration FastAPI minimale avec `GET /health`
- Middleware d'authentification `X-API-Key` désactivable (si `API_KEY` vide)
- Configuration Pydantic Settings avec préfixe `OPENWIKILLM_` + aliases pour les variables sans préfixe (`OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `API_KEY`)
- Docker Compose + `docker.sh` utilitaire
- Tests unitaires : 3 / 3 PASSED

## Décisions techniques

- Préfixe `OPENWIKILLM_` pour les variables de configuration applicatives
- Variables Ollama et `API_KEY` sans préfixe pour faciliter l'interopérabilité
- `hatchling` comme build backend avec `packages = ["app"]` explicite
- Venv dédié dans `backend/.venv` (non commité)

## Problèmes rencontrés

- Hatchling ne trouve pas le package automatiquement (nom du projet `openwikillm` != dossier `app`) → résolu avec `[tool.hatch.build.targets.wheel] packages = ["app"]`
