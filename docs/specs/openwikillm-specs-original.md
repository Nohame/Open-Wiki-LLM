# Spécifications projet — OpenWikiLLM

## 1. Objectif du projet

Créer un service nommé **OpenWikiLLM** : une plateforme open source inspirée d’OpenRAG, mais orientée **Wiki LLM**.

Le but est de transformer des sources brutes en un **wiki Markdown structuré, lisible, versionnable et consultable par des agents IA** via :

- une API REST ;
- un serveur MCP ;
- une interface web simple ;
- un stockage Markdown local ;
- un moteur de recherche texte simple.

Le projet doit permettre à un agent IA de consulter, enrichir et maintenir une base de connaissances structurée, tout en gardant une trace claire de chaque action réalisée.

---

## 2. Philosophie du projet

OpenWikiLLM ne doit pas être un simple RAG classique.

Un RAG classique fonctionne souvent ainsi :

```txt
documents → chunks → embeddings → recherche vectorielle → réponse
```

OpenWikiLLM doit fonctionner plutôt ainsi :

```txt
sources brutes → extraction → pages Markdown → liens wiki → validation → consultation par agents IA
```

La connaissance doit être :

- lisible par un humain ;
- modifiable manuellement ;
- versionnable avec Git ;
- consultable par un agent IA ;
- documentée clairement ;
- traçable ;
- validable avant usage en production.

---

## 3. Règles générales pour Claude Code

Claude Code doit respecter strictement les règles suivantes.

### 3.1 Documentation obligatoire

À chaque modification significative, Claude Code doit documenter ce qui a été fait.

La documentation doit permettre de comprendre :

- pourquoi la modification a été faite ;
- quels fichiers ont été modifiés ;
- quelles décisions techniques ont été prises ;
- quels choix ont été écartés ;
- quelles limites restent connues ;
- quels tests ont été effectués ;
- ce qu’il reste à faire.
- utiliser un fichier CHANGLOG.md
- Claude doit utiliser le skill superpower

Claude Code doit maintenir une trace claire dans le dossier :

```txt
docs/
```

Structure attendue :

```txt
docs/
├── decisions/
├── specs/
├── changelog/
├── dev-notes/
└── architecture/
```

### 3.2 Trace de travail obligatoire

Pour chaque tâche importante, Claude Code doit créer ou mettre à jour une note dans :

```txt
docs/dev-notes/
```

Format recommandé :

```txt
docs/dev-notes/YYYY-MM-DD-nom-de-la-tache.md
```

Exemple :

```txt
docs/dev-notes/2026-05-11-initialisation-docker.md
```

Chaque note doit contenir :

```md
# Titre de la tâche

## Objectif

## Fichiers modifiés

## Décisions prises

## Implémentation

## Tests effectués

## Limites connues

## Prochaines étapes
```

### 3.3 Demande obligatoire avant commit

Claude Code ne doit **jamais faire de commit sans validation explicite de l’utilisateur**.

Avant chaque commit, Claude Code doit :

1. résumer les changements ;
2. lister les fichiers modifiés ;
3. proposer un message de commit ;
4. demander explicitement l’autorisation.

Exemple obligatoire :

```txt
Voici les changements prêts à être commités :

- ajout du docker-compose.yml
- ajout du docker.sh
- ajout de la structure backend
- ajout de la documentation initiale

Message de commit proposé :
[add] initialisation du projet OpenWikiLLM

Est-ce que je peux faire le commit ?
```

Claude Code doit attendre une réponse explicite du type :

```txt
oui
ok
tu peux commit
commit
```

Sans cette validation, aucun commit ne doit être effectué.

### 3.4 Style de code

Le code doit rester :

- simple ;
- clair ;
- maintenable ;
- typé quand c’est possible ;
- documenté uniquement quand cela apporte une vraie valeur ;
- sans duplication inutile ;
- aligné avec les conventions du projet.

Claude Code doit éviter les solutions complexes au départ.

Le MVP doit être privilégié.

---

## 4. Stack technique cible

### 4.1 Backend

Le backend doit être en Python.

Stack conseillée :

- Python 3.11 ou supérieur ;
- FastAPI pour l’API REST ;
- FastMCP pour le serveur MCP ;
- SQLite pour le stockage local ;
- SQLite FTS5 pour la recherche texte ;
- Pydantic pour les schémas ;
- python-frontmatter pour les fichiers Markdown ;
- Markdown standard pour les pages wiki.

### 4.2 Frontend

Le frontend pourra être ajouté dans une phase suivante.

Stack recommandée :

- Nuxt 3 ou Nuxt 4 ;
- TailwindCSS ;
- shadcn-vue ;
- rendu Markdown ;
- interface simple de consultation du wiki.

Le frontend n’est pas obligatoire dans le premier MVP.

### 4.3 Infrastructure locale

Le projet doit fonctionner avec Docker Compose.

Les commandes de base doivent passer par un script :

```txt
docker.sh
```

Commandes obligatoires :

```bash
./docker.sh start
./docker.sh stop
./docker.sh restart
./docker.sh ssh
```

---

## 5. Structure du projet attendue

Structure cible :

```txt
openwikillm/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── mcp/
│   │   ├── models/
│   │   ├── services/
│   │   ├── storage/
│   │   └── main.py
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── raw/
├── wiki/
├── data/
├── docs/
│   ├── architecture/
│   ├── changelog/
│   ├── decisions/
│   ├── dev-notes/
│   └── specs/
├── docker-compose.yml
├── docker.sh
├── .env.example
├── README.md
└── CHANGELOG.md
```

---

## 6. Dossiers fonctionnels

### 6.1 Dossier `raw/`

Le dossier `raw/` contient les sources brutes.

Exemples :

```txt
raw/
├── pdf/
├── markdown/
├── html/
├── txt/
└── imports/
```

Règles :

- les sources brutes ne doivent pas être modifiées automatiquement ;
- toute transformation doit produire une page dans `wiki/` ;
- chaque source doit être identifiable ;
- les fichiers doivent pouvoir être réindexés.

### 6.2 Dossier `wiki/`

Le dossier `wiki/` contient les pages Markdown générées ou maintenues.

Structure recommandée :

```txt
wiki/
├── index.md
├── concepts/
├── projects/
├── procedures/
├── decisions/
└── contradictions.md
```

Les pages doivent utiliser des liens wiki :

```md
[[Nom de la page]]
```

### 6.3 Dossier `data/`

Le dossier `data/` contient les fichiers techniques locaux.

Exemples :

```txt
data/
├── openwikillm.db
├── backlinks.json
└── index-cache.json
```

---

## 7. Format des pages Markdown

Chaque page wiki doit contenir un frontmatter YAML.

Exemple :

```md
---
title: Livraison 24h
type: concept
status: draft
confidence: medium
sources:
  - raw/imports/promesse-livraison.md
updated_at: 2026-05-11
tags:
  - livraison
  - transport
  - pegasus
---

# Livraison 24h

## Résumé

## Règles connues

## Sources

## Pages liées

## Points à confirmer
```

Champs recommandés :

| Champ | Rôle |
|---|---|
| `title` | titre lisible de la page |
| `type` | type de page : concept, project, procedure, decision, note |
| `status` | draft, reviewed, validated, deprecated |
| `confidence` | low, medium, high |
| `sources` | fichiers sources utilisés |
| `updated_at` | date de dernière mise à jour |
| `tags` | mots-clés |

---

## 8. API REST attendue

Le backend doit exposer une API REST simple.

Endpoints MVP :

```http
GET  /health
GET  /api/pages
GET  /api/pages/{slug}
POST /api/search
POST /api/ingest/text
POST /api/index/rebuild
```

Endpoints futurs :

```http
POST /api/compile
POST /api/answer
POST /api/audit
POST /api/contradictions/find
POST /api/export/openrag
```

---

## 9. MCP Server attendu

Le projet doit fournir un serveur MCP permettant aux agents IA de consulter le wiki.

### 9.1 Resources MCP

Resources attendues :

```txt
wiki://index
wiki://page/{slug}
wiki://concept/{slug}
wiki://contradictions
```

### 9.2 Tools MCP

Tools MVP :

```txt
wiki_search
wiki_read_page
wiki_list_pages
wiki_rebuild_index
```

Tools futurs :

```txt
wiki_ingest_source
wiki_compile_source
wiki_update_page
wiki_find_contradictions
wiki_answer
```

### 9.3 Prompts MCP

Prompts futurs :

```txt
/wiki-answer
/wiki-ingest
/wiki-audit
/wiki-find-gaps
/wiki-update-page
```

---

## 10. Moteur de recherche

Le MVP doit utiliser SQLite FTS5.

Objectif :

- indexer les pages Markdown ;
- rechercher dans le titre ;
- rechercher dans le contenu ;
- retourner les pages les plus pertinentes ;
- fournir un extrait court.

Table possible :

```sql
CREATE VIRTUAL TABLE wiki_pages_fts USING fts5(
    slug,
    title,
    content,
    tags
);
```

---

## 11. Docker Compose

Le projet doit fonctionner avec Docker Compose.

Exemple attendu :

```yaml
services:
  openwikillm-api:
    build:
      context: ./backend
    container_name: openwikillm-api
    ports:
      - "8088:8088"
    volumes:
      - ./raw:/app/raw
      - ./wiki:/app/wiki
      - ./data:/app/data
      - ./docs:/app/docs
    env_file:
      - .env
```

---

## 12. Script `docker.sh`

Le projet doit obligatoirement fournir un fichier :

```txt
docker.sh
```

Commandes obligatoires :

```bash
./docker.sh start
./docker.sh stop
./docker.sh restart
./docker.sh ssh
```

Comportement attendu :

### `start`

Démarre les services Docker Compose.

```bash
docker compose up -d
```

### `stop`

Arrête les services.

```bash
docker compose down
```

### `restart`

Redémarre les services.

```bash
docker compose down
docker compose up -d
```

### `ssh`

Ouvre un shell dans le conteneur principal.

```bash
docker compose exec openwikillm-api bash
```

Le script doit afficher une aide claire si la commande est inconnue.

Exemple :

```bash
Usage: ./docker.sh {start|stop|restart|ssh}
```

---

## 13. Exemple de `docker.sh`

```bash
#!/usr/bin/env bash

set -e

SERVICE_NAME="openwikillm-api"

case "$1" in
  start)
    docker compose up -d
    ;;

  stop)
    docker compose down
    ;;

  restart)
    docker compose down
    docker compose up -d
    ;;

  ssh)
    docker compose exec "$SERVICE_NAME" bash
    ;;

  *)
    echo "Usage: ./docker.sh {start|stop|restart|ssh}"
    exit 1
    ;;
esac
```

---

## 14. Configuration

Un fichier `.env.example` doit être fourni.

Exemple :

```env
APP_ENV=local
APP_DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=8088

OPENWIKILLM_RAW_PATH=/app/raw
OPENWIKILLM_WIKI_PATH=/app/wiki
OPENWIKILLM_DATA_PATH=/app/data

OPENWIKILLM_DEFAULT_MODE=strict
```

---

## 15. Modes de réponse

Le projet devra gérer plusieurs modes.

| Mode | Description |
|---|---|
| `draft` | l’IA peut proposer des hypothèses clairement marquées |
| `strict` | réponse uniquement depuis le wiki |
| `source_only` | réponse uniquement depuis les sources brutes |
| `validated_only` | réponse uniquement depuis les pages validées |

Pour les agents IA de support, le mode recommandé est :

```txt
validated_only
```

---

## 16. Règle zéro invention

Quand le mode strict ou validated_only est activé, l’IA ne doit pas inventer.

Réponse de fallback obligatoire :

```txt
Je ne trouve pas cette information dans le wiki validé.
```

L’IA peut ensuite proposer une action :

```txt
Il faut ajouter une source, valider une page existante ou demander une précision.
```

---

## 17. Journalisation et traçabilité

Le projet doit garder une trace des actions importantes.

À prévoir :

```txt
logs/
```

Actions à tracer :

- ingestion d’une source ;
- génération d’une page ;
- mise à jour d’une page ;
- reconstruction de l’index ;
- recherche ;
- réponse générée ;
- erreur technique.

Chaque log doit contenir au minimum :

- date ;
- type d’action ;
- statut ;
- fichier ou page concernée ;
- message court.

---

## 18. Changelog

Le fichier `CHANGELOG.md` doit être maintenu.

Format recommandé :

```md
# Changelog

## Non publié

### Ajouté

### Modifié

### Corrigé

### Supprimé
```

Claude Code doit mettre à jour le changelog pour chaque modification importante.

---

## 19. README attendu

Le fichier `README.md` doit expliquer :

- ce qu’est OpenWikiLLM ;
- comment installer le projet ;
- comment démarrer avec Docker ;
- comment utiliser `docker.sh` ;
- comment ajouter une source ;
- comment reconstruire l’index ;
- comment interroger l’API ;
- comment brancher un client MCP ;
- les limites actuelles.

---

## 20. Tests

Le projet doit contenir des tests unitaires au fur et à mesure.

Tests MVP :

- lecture d’une page Markdown ;
- parsing du frontmatter ;
- indexation SQLite FTS5 ;
- recherche ;
- endpoints `/health`, `/api/pages`, `/api/search` ;
- tools MCP principaux si possible.

Commande recommandée :

```bash
pytest
```

---

## 21. Critères d’acceptation du MVP

Le MVP est considéré comme acceptable si :

- `./docker.sh start` démarre le projet ;
- `./docker.sh stop` arrête le projet ;
- `./docker.sh restart` redémarre le projet ;
- `./docker.sh ssh` ouvre un shell dans le conteneur ;
- l’API `/health` répond correctement ;
- des pages Markdown peuvent être placées dans `wiki/` ;
- l’index peut être reconstruit ;
- une recherche retourne des résultats ;
- les pages peuvent être lues via API ;
- le serveur MCP expose au minimum la recherche et la lecture de pages ;
- la documentation de ce qui a été fait est présente dans `docs/dev-notes/` ;
- aucun commit n’est fait sans validation explicite.

---

## 22. Ordre de développement conseillé

Claude Code doit travailler par étapes simples.

### Étape 1 — Initialisation

- créer la structure du projet ;
- ajouter `docker-compose.yml` ;
- ajouter `docker.sh` ;
- ajouter `.env.example` ;
- ajouter un backend minimal ;
- ajouter `/health` ;
- documenter dans `docs/dev-notes/`.

### Étape 2 — Wiki Markdown

- lire les fichiers Markdown dans `wiki/` ;
- parser le frontmatter ;
- exposer `GET /api/pages` ;
- exposer `GET /api/pages/{slug}` ;
- ajouter les tests.

### Étape 3 — Index SQLite FTS5

- créer la base SQLite ;
- indexer les pages ;
- exposer `POST /api/index/rebuild` ;
- exposer `POST /api/search` ;
- ajouter les tests.

### Étape 4 — MCP Server

- ajouter le serveur MCP ;
- exposer `wiki_search` ;
- exposer `wiki_read_page` ;
- exposer `wiki_list_pages` ;
- documenter l’usage.

### Étape 5 — Ingestion simple

- ajouter `POST /api/ingest/text` ;
- enregistrer une source dans `raw/imports/`;
- créer une page draft dans `wiki/`;
- tracer l’action.

### Étape 6 — Préparation IA

- ajouter les prompts de compilation ;
- préparer le mode strict ;
- préparer le mode validated_only ;
- ajouter une documentation d’usage avec Claude Code ou Cursor.

---

## 23. Contraintes importantes

Claude Code doit éviter :

- de complexifier avec une base vectorielle au début ;
- d’ajouter un frontend trop tôt ;
- de créer trop d’abstractions inutiles ;
- de faire des commits automatiques ;
- de modifier les sources brutes ;
- de supprimer des fichiers sans validation ;
- de mélanger documentation produit et documentation technique.

---

## 24. Vision long terme

Fonctionnalités futures possibles :

- interface Nuxt ;
- validation humaine des pages ;
- connecteur Google Drive ;
- connecteur Basecamp ;
- connecteur GitHub/GitLab ;
- détection de contradictions ;
- export vers OpenRAG ;
- API compatible n8n ;
- gestion multi-projets ;
- gestion des droits ;
- mode SaaS ;
- historique Git visible dans l’interface.

---

## 25. Instruction finale pour Claude Code

Tu dois construire ce projet progressivement, proprement et avec une documentation claire.

Après chaque étape importante :

1. documente ce qui a été fait ;
2. mets à jour le changelog si nécessaire ;
3. liste les fichiers modifiés ;
4. propose les tests à lancer ;
5. propose un message de commit ;
6. demande l’autorisation avant tout commit.

Tu ne dois jamais faire de commit sans accord explicite de l’utilisateur.
