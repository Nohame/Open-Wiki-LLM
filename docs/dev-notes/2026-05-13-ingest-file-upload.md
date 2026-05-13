# Ingest — Upload de fichiers

## Objectif

Ajouter un onglet "Fichiers" dans la page Ingest permettant d'uploader plusieurs fichiers à la fois (.md, .txt, .pdf, .docx) et de les ingérer séquentiellement avec un statut par fichier en temps réel.

## Fichiers modifiés

**Backend :**
- `backend/pyproject.toml` — ajout `pdfplumber>=0.11.0`, `python-docx>=1.1.0` (prod), `fpdf2>=2.7.0` (dev)
- `backend/app/services/file_extractor.py` (nouveau) — extraction texte depuis bytes selon extension
- `backend/app/api/ingest.py` — ajout endpoint `POST /api/ingest/file`
- `backend/tests/test_file_extractor.py` (nouveau) — 7 tests extracteurs
- `backend/tests/test_ingest.py` — 5 tests endpoint fichier

**Frontend :**
- `frontend/composables/useIngest.ts` — ajout méthode `ingestFile(file, tags): Promise<IngestResult>`
- `frontend/components/ingest/IngestFile.vue` (nouveau) — composant drag-and-drop
- `frontend/pages/ingest.vue` — ajout 3ème onglet "Fichiers"
- `frontend/tests/composables/useIngest.test.ts` — test `ingestFile`

## Décisions prises

- **Endpoint unique** `POST /api/ingest/file` + traitement séquentiel côté frontend (pas de queue serveur)
- **Validation double** extension ET content-type, avec fallback `application/octet-stream` et `""` pour compatibilité navigateurs (Firefox envoie parfois `text/plain` pour les `.md`)
- **Limite taille** : 10 Mo côté client ET côté serveur (HTTP 413 si dépassé)
- **ingestFile() ne modifie pas les refs partagées** `loading`/`error`/`result` — la gestion d'état par fichier est dans le composant (design intentionnel pour le batch)
- **Import explicite** de `IngestFile` dans `ingest.vue` pour éviter le tree-shaking en prod (même pattern que fix sidebar)

## Implémentation

Le flux complet :
1. `IngestFile.vue` → valide extension + taille côté client
2. `useIngest.ingestFile(file, tags)` → FormData avec titre déduit du nom de fichier
3. `POST /api/ingest/file` → valide extension + MIME → extrait texte via `file_extractor.py` → délègue à `ingest_text()` existant
4. Résultat : `IngestResult` avec slug → affiché comme lien vers `/wiki/{slug}`

## Tests effectués

- 35 tests backend (dont 12 nouveaux), 0 warnings
- 11 tests frontend (dont 1 nouveau), tous verts

## Limites connues

- Pas d'extraction d'images dans les PDF/DOCX (texte uniquement)
- Pas de limite sur le nombre de fichiers par batch
- Encodage UTF-8 uniquement pour .txt/.md (pas de détection automatique)
- Traitement séquentiel : pour 50 PDFs avec Ollama, attente longue côté utilisateur
- `extract_text` est async mais contient des appels bloquants (pdfplumber, python-docx) — acceptable MVP

## Prochaines étapes

- Connecteur Google Drive (spec séparée à créer)
- Limite de concurrence configurable pour le traitement batch
- Barre de progression globale (X/N fichiers traités)
