# Wiki Git Backend — Design

## Objectif

Permettre au dossier `wiki/` d'être un dépôt git indépendant, de façon optionnelle. Chaque ingestion et chaque édition manuelle crée un commit. Le push vers un remote est configurable (`auto_push`).

## Fichiers modifiés

- `backend/app/services/git_service.py` — NOUVEAU
- `backend/app/api/git.py` — NOUVEAU
- `backend/app/main.py` — enregistrement du router git
- `backend/app/services/ingest_service.py` — appel `git_service.commit_ingest()` en fin d'ingestion
- `backend/app/api/pages.py` — appel `git_service.commit_edit()` après write/delete
- `backend/app/models/settings.py` — ajout modèle `GitSettings`
- `backend/app/core/config_store.py` — ajout section `git`
- `data/config.json` — ajout section `git`

## Architecture

```
wiki/                        ← dépôt git séparé (son propre .git)
├── .git/
├── .gitignore
├── concept/
├── entity/
├── imports/
└── index.md, log.md, schema.md

backend/app/services/
├── wiki_manager.py          ← inchangé
├── wiki_service.py          ← inchangé
└── git_service.py           ← NOUVEAU

backend/app/api/
└── git.py                   ← NOUVEAU
```

## Flux d'appel

```
ingest_service.py
  → wiki_manager.apply_updates()   (écriture fichiers, inchangé)
  → wiki_manager.rebuild_index()   (inchangé)
  → wiki_manager.append_log()      (inchangé)
  → git_service.commit_ingest()    ← appelé en fin d'ingestion si git activé

api/pages.py (CRUD manuel)
  → wiki_manager.*(écriture)       (inchangé)
  → git_service.commit_edit()      ← appelé après chaque write/delete si git activé
```

## Configuration

Nouvelle section dans `data/config.json` :

```json
"git": {
  "enabled": false,
  "auto_push": false,
  "remote_url": "",
  "branch": "main"
}
```

- `enabled` : active/désactive tout le comportement git
- `auto_push` : push automatique après chaque commit
- `remote_url` : URL remote (SSH ou HTTPS), vide = pas de push
- `branch` : branche cible pour le push

## API — Endpoints `git.py`

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/git/init` | `git init` dans `wiki_path`, crée `.gitignore`, commit initial |
| `GET` | `/git/status` | Retourne `enabled`, `initialized`, dernier commit, nb fichiers modifiés |
| `POST` | `/git/push` | Push manuel vers le remote configuré |
| `GET` | `/git/log` | 10 derniers commits (hash court, message, date) |

## `git_service.py` — Interface

```python
def is_initialized() -> bool
def init_repo() -> None
def commit_ingest(source: str, written: list[str], deleted: list[str]) -> str | None
def commit_edit(slug: str, action: str) -> str | None
def push() -> None
def get_status() -> dict
def get_log(limit: int = 10) -> list[dict]
```

Implémentation via `subprocess` (stdlib, pas de dépendance externe). Toutes les commandes s'exécutent dans `settings.wiki_path`.

## Format des messages de commit

```
feat(wiki): ingest reclamation-rag — 3 pages créées, 1 supprimée
edit(wiki): update concept--reclamation-produit-abime
delete(wiki): entity--stephanie
create(wiki): concept--nouveau-concept
chore(wiki): init
```

## Gestion d'erreurs

- **git non installé** : `GitNotAvailableError` loggée en warning, l'écriture wiki continue (fail silencieux sur le commit).
- **push échoue** (réseau, auth) : loggé en warning, pas d'exception remontée. Le commit local est acquis.
- **`enabled=false`** : toutes les fonctions de `git_service` sont des no-ops immédiats.
- **repo non initialisé** : si un commit est tenté sans `git init` préalable, warning + skip. L'init est une action explicite via `POST /git/init`.

## Décisions prises

- Dépôt **séparé** (pas le repo principal `open-wiki-llm`) pour que le wiki soit autonome et poussable vers un remote dédié.
- Commit **par ingestion** (groupé) plutôt que par page, pour un historique lisible.
- **`subprocess`** plutôt que `gitpython` pour rester sans dépendance externe.
- Init **explicite** via API, pas automatique au démarrage du serveur.

## Limites connues

- Pas de gestion de conflits git (le wiki est considéré comme source unique de vérité).
- Authentification SSH/HTTPS pour le push laissée à la configuration système (clés SSH, credential helper).
- Pas d'interface UI pour le git dans cette itération (API uniquement).

## Prochaines étapes

- Interface frontend : onglet Git dans les settings (status, init, push, log)
- Support de branches par ingestion (`feat/ingest-{source}`)
