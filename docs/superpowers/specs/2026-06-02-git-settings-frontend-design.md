# Git Settings Frontend — Design

## Objectif

Ajouter une section "Git" dans la page Settings du frontend pour permettre à l'utilisateur de configurer et d'interagir avec le dépôt git du wiki depuis l'UI.

## Fichiers modifiés

- `frontend/types/api.ts` — ajout `GitConfig`, `GitStatus`, mise à jour `AppSettings`
- `frontend/composables/useGit.ts` — NOUVEAU : appels API git (status, init, push)
- `frontend/components/settings/GitSettings.vue` — NOUVEAU : composant UI
- `frontend/pages/settings.vue` — ajout section Git

## Architecture

```
useSettings (existant)          useGit (nouveau)
  └─ GET/PUT /api/settings          ├─ GET /api/git/status
       └─ git: GitConfig            ├─ POST /api/git/init
                                    └─ POST /api/git/push

GitSettings.vue
  ├─ v-model: GitConfig  (config sauvegardée via useSettings)
  └─ useGit()            (actions init/push + affichage statut)
```

La config (`enabled`, `auto_push`, `remote_url`, `branch`) est lue/écrite via `PUT /api/settings` comme les autres sections. Les actions (`init`, `push`) et la lecture du statut (`/api/git/status`) sont indépendantes du save global.

## Types TypeScript (`types/api.ts`)

```typescript
export interface GitConfig {
  enabled: boolean
  auto_push: boolean
  remote_url: string
  branch: string
}

export interface GitStatus {
  enabled: boolean
  initialized: boolean
  last_commit: string | null
  dirty_files: number
}

// AppSettings mis à jour
export interface AppSettings {
  llm: LLMConfig
  ingest: IngestConfig
  connectors: ConnectorsConfig
  git: GitConfig
}
```

## Composable `useGit.ts`

```typescript
const status = ref<GitStatus | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

async function fetchStatus(): Promise<void>   // GET /api/git/status
async function initRepo(): Promise<void>      // POST /api/git/init → fetchStatus()
async function pushRepo(): Promise<void>      // POST /api/git/push → fetchStatus()

return { status, loading, error, fetchStatus, initRepo, pushRepo }
```

Erreurs catchées → `error.value` renseigné, pas d'exception remontée.

## Composant `GitSettings.vue`

### Props / Emits

```typescript
defineProps<{ modelValue: GitConfig }>()
defineEmits<{ 'update:modelValue': [GitConfig] }>()
```

Même pattern que `ConnectorsSettings.vue`.

### Comportement par état

**État 1 — `enabled = false`**
- Toggle OFF
- Tous les champs (Remote URL, Branche, Auto-push) visibles mais `disabled`
- Aucun bouton d'action affiché

**État 2 — `enabled = true`, `status.initialized = false`**
- Toggle ON
- `fetchStatus()` appelé au `watch(enabled)` si statut non chargé
- Champs Remote URL, Branche, Auto-push éditables
- Bouton "Initialiser le dépôt git" (pleine largeur, bleu) — appelle `initRepo()`
- Pendant `loading` : bouton désactivé avec texte "Initialisation…"

**État 3 — `enabled = true`, `status.initialized = true`**
- Badge vert "Initialisé" + nombre de fichiers modifiés + dernier commit (hash court + message)
- Bouton "Push ↑" (à droite du badge) — appelle `pushRepo()`
- Pendant push : bouton désactivé avec texte "Push…"
- Champs Remote URL, Branche, Auto-push éditables
- Les modifications des champs émettent `update:modelValue` (sauvegardées par le bouton global "Enregistrer")

### Montage

```typescript
onMounted(async () => {
  if (props.modelValue.enabled) await fetchStatus()
})

watch(() => props.modelValue.enabled, async (enabled) => {
  if (enabled && !status.value) await fetchStatus()
})
```

## Intégration dans `settings.vue`

Ajouter après la section "Connecteurs" :

```vue
<section class="p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-4">
  <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wider">Git</h2>
  <SettingsGitSettings v-model="settings.git" />
</section>
```

Pas de nouveaux handlers dans `settings.vue` — init/push sont gérés entièrement dans le composant.

## Gestion d'erreurs

- `fetchStatus` / `initRepo` / `pushRepo` échouent → `error.value` renseigné, affiché en rouge sous le composant (`<p v-if="error" class="text-xs text-red-400">`)
- Erreur effacée au prochain appel réussi

## Tests

- `tests/composables/useGit.test.ts` — mock `useApi`, tester fetchStatus / initRepo / pushRepo + gestion d'erreur
- `tests/components/GitSettings.test.ts` — tester les 3 états (disabled, not initialized, initialized) via `modelValue` et mock de `useGit`

## Décisions prises

- Log git non affiché dans l'UI (endpoint `/api/git/log` existe en backend mais hors scope de cette itération)
- Remote URL est optionnel — init fonctionne sans remote
- La config git est sauvegardée via le bouton global "Enregistrer" de `settings.vue`, pas via un bouton dédié
- `fetchStatus()` appelé uniquement si `enabled = true` (pas de requête inutile quand git est désactivé)

## Limites connues

- Pas de feedback visuel sur le résultat du push (succès/échec silencieux côté backend si remote non configuré)
- Pas de log des commits dans l'UI pour cette itération

## Prochaines étapes

- Afficher les derniers commits (log) dans un accordéon sous le badge statut
- Feedback push : distinguer "push réussi" / "remote non configuré" / "erreur réseau"
