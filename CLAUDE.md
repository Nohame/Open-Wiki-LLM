# Instructions pour Claude Code — OpenWikiLLM

## Commit

Ne jamais committer sans validation explicite.

Avant chaque commit, résumer les changements, lister les fichiers modifiés, proposer un message, et attendre une réponse du type `oui`, `ok`, `commit`.

## Documentation

Pour chaque tâche importante, créer ou mettre à jour une note dans `docs/dev-notes/YYYY-MM-DD-nom-de-la-tache.md`.

Format attendu :

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

Mettre à jour `CHANGELOG.md` à chaque modification significative.

## Style de code

- Simple, clair, maintenable
- Typé quand possible
- Pas de duplication inutile
- MVP d'abord — pas de complexité prématurée
- Utiliser les skills superpowers

## Structure docs

```
docs/
├── architecture/
├── changelog/
├── decisions/
├── dev-notes/
└── specs/
```
