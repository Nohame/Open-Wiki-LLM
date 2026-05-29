# Google Drive Connector

## Objectif

Ajouter un connecteur Google Drive permettant à l'utilisateur de configurer ses credentials OAuth dans la page Settings et d'ingérer des fichiers Drive depuis la page Ingest via le même pipeline que l'upload manuel.

## Fichiers modifiés

### Backend — Créés
- `backend/app/services/connectors/__init__.py`
- `backend/app/services/connectors/google_drive.py` — OAuth (build_auth_url, exchange_code, refresh_token_if_needed) + Drive API (list_files, download_file) via httpx
- `backend/app/api/connectors.py` — 5 routes sous `/api/connectors/google-drive/`
- `backend/tests/test_google_drive_service.py` — 8 tests service
- `backend/tests/test_api_connectors.py` — 9 tests API

### Backend — Modifiés
- `backend/app/models/settings.py` — ajout GoogleDriveConfig, ConnectorsConfig, extension AppSettings
- `backend/app/core/config.py` — ajout `app_url`, `backend_url`
- `backend/app/api/settings.py` — extension `_mask` / `_merge_keys` pour les champs Drive
- `backend/app/main.py` — enregistrement du router connectors

### Frontend — Créés
- `frontend/composables/useGoogleDrive.ts` — getAuthUrl, disconnect, listFiles, ingestFile
- `frontend/components/settings/ConnectorsSettings.vue` — formulaire credentials + statut + boutons Connect/Disconnect
- `frontend/components/ingest/GoogleDriveTab.vue` — navigateur de fichiers Drive avec breadcrumb et ingest par fichier

### Frontend — Modifiés
- `frontend/types/api.ts` — ajout GoogleDriveConfig, ConnectorsConfig, GoogleDriveFile, GoogleDriveListResponse ; extension AppSettings
- `frontend/pages/settings.vue` — section Connecteurs + gestion callback OAuth
- `frontend/pages/ingest.vue` — onglet Google Drive
- `.env.example` — ajout OPENWIKILLM_APP_URL, OPENWIKILLM_BACKEND_URL

## Décisions prises

- **OAuth full-page redirect** : pas de popup. Le backend reçoit le callback (`{backend_url}/api/connectors/google-drive/callback`) et redirige ensuite vers le frontend.
- **Credentials utilisateur** : l'utilisateur crée son propre Google Cloud Project et entre `client_id` + `client_secret` dans les Paramètres.
- **httpx uniquement** : pas de SDK Google. Toutes les interactions avec l'API Drive via `httpx.AsyncClient(timeout=30)`.
- **Scope** : `drive.readonly` uniquement.
- **State OAuth supprimé** : pas de session store côté backend pour valider le state CSRF. Acceptable pour un déploiement local mono-utilisateur.
- **Token refresh persisté** : si le token est rafraîchi dans `/files` ou `/ingest`, le nouveau token est écrit en config.json.
- **Masquage** : `client_secret`, `access_token`, `refresh_token` masqués avec `"****"` en GET, préservés en PUT.
- **`ConnectorsSettings.vue` dumb component** : émet `connect` / `disconnect`, le parent (`settings.vue`) gère save-first-then-getAuthUrl.
- **`connectionFailed` prop** : permet au parent de signaler un échec OAuth au composant enfant pour réinitialiser le spinner "Redirection…".

## Tests effectués

- Backend : 147/147 tests passent
- TypeScript frontend : aucune erreur nouvelle (avertissement `baseUrl` pré-existant)

## Limites connues

- Un seul compte Google Drive par instance (pas de multi-compte)
- Pas de sync automatique (ingest manuel uniquement)
- Google Sheets, Slides, Forms non supportés
- Pagination Drive non implémentée (max 100 fichiers par dossier)
- Les tokens sont en clair dans `config.json` — sécurité assurée par les permissions du volume Docker
- Pas de validation CSRF du `state` OAuth (déploiement local uniquement)

## Prochaines étapes

- Pagination des fichiers Drive (nextPageToken)
- Support Google Sheets → export CSV
- Centraliser `isGoogleDriveConnected(cfg)` dans `useGoogleDrive.ts`
