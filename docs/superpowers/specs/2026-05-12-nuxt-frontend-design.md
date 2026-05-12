# OpenWikiLLM — Frontend Nuxt Design

## Objectif

Fournir une interface web locale au-dessus de l'API OpenWikiLLM, inspirée du design de Langflow/OpenRag : sidebar collapsible, dark mode par défaut, chat comme page principale.

## Architecture

**Mode :** Nuxt 3 SPA (`ssr: false`). Aucun serveur Node en prod — `nuxt generate` produit un dossier `dist/` statique servi par nginx dans Docker.

**Appels API :** Directs depuis le browser vers `http://localhost:8088` (ou l'URL configurée). La clé API est stockée en `localStorage` et injectée en header `X-API-Key` sur chaque requête.

**Intégration repo :** Dossier `frontend/` à la racine du repo OpenWikiLLM. Service `frontend` ajouté dans `docker-compose.yml` sur le port `3000`.

## Stack technique

| Couche | Choix |
|---|---|
| Framework | Nuxt 3, TypeScript, `ssr: false` |
| Styles | Tailwind CSS 4, dark mode par défaut |
| Composants UI | shadcn-vue (Radix Vue + Tailwind) |
| État global | Pinia |
| Utilitaires | VueUse |
| Markdown | `marked` + `DOMPurify` |
| Icons | Lucide Vue Next |
| HTTP | `$fetch` natif Nuxt (ofetch) |

## Pages et routes

| Route | Accès | Description |
|---|---|---|
| `/login` | public | Saisir et valider la clé API — stockée en localStorage |
| `/` | protégé | Redirige vers `/chat` |
| `/chat` | protégé | Interface de questions/réponses sur le wiki |
| `/wiki` | protégé | Liste des pages wiki + recherche FTS5 |
| `/wiki/[slug]` | protégé | Lecture d'une page Markdown |
| `/ingest` | protégé | Ingestion texte et image |

**Guard global :** middleware Nuxt qui redirige vers `/login` si aucune clé API en localStorage.

## Layout

Sidebar (256px) + contenu principal flexible, inspiré de Langflow/OpenRag.

```
┌─────────────────────────────────────────────────────────┐
│  ◉ OpenWikiLLM                          [connected ✓]   │
├──────────────┬──────────────────────────────────────────┤
│  💬 Chat     │                                          │
│  📚 Wiki     │         CONTENU PRINCIPAL                │
│  ⬆  Ingest  │                                          │
│  ──────────  │                                          │
│  ⚙  Réglages│                                          │
│  [← réduire] │                                          │
└──────────────┴──────────────────────────────────────────┘
```

La sidebar se réduit en mode icônes (48px) via `Cmd+B` ou bouton toggle. L'état est persisté en localStorage.

## Page Chat (`/chat`)

- Zone de messages avec scroll automatique vers le bas
- Chaque message assistant inclut le rendu Markdown et les sources sous forme de chips cliquables (→ `/wiki/[slug]`)
- Sélecteur de mode : `validated_only` (défaut), `strict`, `draft`, `source_only`
- Zone de saisie multi-ligne, envoi par `Cmd+Enter` ou bouton
- État vide : message de bienvenue

## Page Wiki (`/wiki`)

- Barre de recherche FTS5 (debounce 300ms, appel `POST /api/search`)
- Grille de cards : titre, statut (badge coloré), tags, date de mise à jour
- Clic sur une card → `/wiki/[slug]`
- Si recherche vide : liste complète via `GET /api/pages`

## Page Wiki détail (`/wiki/[slug]`)

- Rendu Markdown du contenu de la page
- Frontmatter affiché dans un panel latéral : status, confidence, sources, updated_at, tags
- Bouton retour → `/wiki`

## Page Ingest (`/ingest`)

Deux onglets :

**Texte**
- Champs : Titre (requis), Tags (séparés par virgule), Zone de texte
- Bouton "Ingérer" → `POST /api/ingest/text`

**Image**
- Champs : Titre (optionnel), Tags (séparés par virgule)
- Zone drag & drop : `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`
- Bouton "Ingérer" → `POST /api/ingest/image` (multipart)

Les deux onglets affichent un résultat inline après ingestion : slug créé, lien vers la page wiki.

## Page Login (`/login`)

- Champ unique : clé API
- Bouton "Connexion" → appel `GET /health` avec le header `X-API-Key` pour valider la clé
- Si succès : clé stockée en localStorage, redirect vers `/chat`
- Si échec : message d'erreur inline

## Composables

| Composable | Responsabilité |
|---|---|
| `useAuth` | login, logout, clé API, état connecté |
| `useApi` | wrapper `$fetch` avec injection header X-API-Key et gestion 401 |
| `useChat` | historique messages, appel `/api/answer`, état loading |
| `useWiki` | liste pages, recherche, lecture page |
| `useIngest` | ingestion texte et image, état loading/résultat |

## Structure fichiers

```
frontend/
├── nuxt.config.ts
├── package.json
├── tailwind.config.ts
├── app.vue
├── middleware/
│   └── auth.global.ts
├── pages/
│   ├── login.vue
│   ├── index.vue
│   ├── chat.vue
│   ├── wiki/
│   │   ├── index.vue
│   │   └── [slug].vue
│   └── ingest.vue
├── components/
│   ├── layout/
│   │   ├── AppSidebar.vue
│   │   └── AppHeader.vue
│   ├── chat/
│   │   ├── ChatMessages.vue
│   │   ├── ChatInput.vue
│   │   ├── ChatMessage.vue
│   │   └── SourceChip.vue
│   ├── wiki/
│   │   ├── WikiPageCard.vue
│   │   ├── WikiSearchBar.vue
│   │   └── MarkdownViewer.vue
│   └── ingest/
│       ├── IngestText.vue
│       └── IngestImage.vue
├── composables/
│   ├── useAuth.ts
│   ├── useApi.ts
│   ├── useChat.ts
│   ├── useWiki.ts
│   └── useIngest.ts
├── stores/
│   └── auth.ts
├── types/
│   └── api.ts
└── Dockerfile
```

## Docker

`frontend/Dockerfile` :
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run generate

FROM nginx:alpine
COPY --from=builder /app/.output/public /usr/share/nginx/html
EXPOSE 80
```

Ajout dans `docker-compose.yml` :
```yaml
frontend:
  build: ./frontend
  ports:
    - "3000:80"
```

## Limites connues (MVP)

- Pas de pagination sur la liste wiki (toutes les pages chargées d'un coup)
- Pas d'historique de conversations persisté (effacé au rechargement)
- Pas de mode édition des pages wiki depuis le front
- La clé API en localStorage n'est pas chiffrée
