# Git Settings Frontend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter une section "Git" dans la page Settings du frontend Nuxt 3 pour configurer et interagir avec le dépôt git du wiki depuis l'UI.

**Architecture:** Un composable `useGit.ts` encapsule les appels `/api/git/*` (status, init, push). Un composant `GitSettings.vue` utilise ce composable pour afficher 3 états (désactivé / activé non initialisé / initialisé). La config est sauvegardée via `PUT /api/settings` comme les autres sections.

**Tech Stack:** Nuxt 3, Vue 3, TypeScript, Tailwind CSS, Vitest, @vue/test-utils

**Spec:** `docs/superpowers/specs/2026-06-02-git-settings-frontend-design.md`

---

## File Map

| Fichier | Action | Rôle |
|---------|--------|------|
| `frontend/types/api.ts` | Modifier | Ajouter `GitConfig`, `GitStatus`, mettre à jour `AppSettings` |
| `frontend/tests/composables/useSettings.test.ts` | Modifier | Ajouter `git` dans `defaultSettings` |
| `frontend/composables/useGit.ts` | Créer | Appels API git : fetchStatus, initRepo, pushRepo |
| `frontend/tests/composables/useGit.test.ts` | Créer | Tests unitaires de useGit |
| `frontend/components/settings/GitSettings.vue` | Créer | Composant UI des 3 états |
| `frontend/tests/components/GitSettings.test.ts` | Créer | Tests des 3 états du composant |
| `frontend/pages/settings.vue` | Modifier | Ajout section Git après Connecteurs |

---

### Task 1: Types TypeScript + mise à jour defaultSettings

**Files:**
- Modify: `frontend/types/api.ts`
- Modify: `frontend/tests/composables/useSettings.test.ts`

- [ ] **Step 1: Écrire le test échouant**

Dans `frontend/tests/composables/useSettings.test.ts`, remplacer le `defaultSettings` existant (qui se termine après `connectors`) par :

```typescript
const defaultSettings: AppSettings = {
  llm: {
    provider: 'ollama',
    ollama: { base_url: 'http://localhost:11434', model: 'mistral', vision_model: 'llava' },
    openai: { api_key: '', model: 'gpt-4o', vision_model: 'gpt-4o' },
    gemini: { api_key: '', model: 'gemini-1.5-pro', vision_model: 'gemini-1.5-pro' },
    anthropic: { api_key: '', model: 'claude-opus-4-7', vision_model: 'claude-opus-4-7' },
    custom: { base_url: '', api_key: '', model: '', vision_model: '' },
  },
  ingest: { max_text_chars: 30000 },
  connectors: {
    google_drive: {
      client_id: '',
      client_secret: '',
      access_token: '',
      refresh_token: '',
      token_expiry: '',
    },
  },
  git: { enabled: false, auto_push: false, remote_url: '', branch: 'main' },
}
```

- [ ] **Step 2: Vérifier que le test échoue**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/frontend && npm run test -- tests/composables/useSettings.test.ts
```

Résultat attendu : erreur TypeScript — `Object literal may only specify known properties, and 'git' does not exist in type 'AppSettings'`

- [ ] **Step 3: Ajouter les types dans `frontend/types/api.ts`**

Ajouter après l'interface `ConnectorsConfig` :

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
```

Remplacer l'interface `AppSettings` existante :

```typescript
export interface AppSettings {
  llm: LLMConfig
  ingest: IngestConfig
  connectors: ConnectorsConfig
  git: GitConfig
}
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/frontend && npm run test -- tests/composables/useSettings.test.ts
```

Résultat attendu : tous `PASSED`

- [ ] **Step 5: Vérifier la suite complète**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/frontend && npm run test
```

Résultat attendu : tous `PASSED`

- [ ] **Step 6: Commit**

```bash
git add frontend/types/api.ts frontend/tests/composables/useSettings.test.ts
git commit -m "feat(frontend): add GitConfig and GitStatus types"
```

---

### Task 2: Composable `useGit.ts`

**Files:**
- Create: `frontend/composables/useGit.ts`
- Create: `frontend/tests/composables/useGit.test.ts`

- [ ] **Step 1: Créer le fichier de tests**

Créer `frontend/tests/composables/useGit.test.ts` :

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockGet = vi.fn()
const mockPost = vi.fn()
vi.mock('~/composables/useApi', () => ({
  useApi: () => ({ get: mockGet, post: mockPost }),
}))

import type { GitStatus } from '~/types/api'

const mockStatus: GitStatus = {
  enabled: true,
  initialized: true,
  last_commit: 'abc1234 chore(wiki): init',
  dirty_files: 0,
}

describe('useGit', () => {
  beforeEach(() => {
    mockGet.mockReset()
    mockPost.mockReset()
  })

  it('fetchStatus populates status', async () => {
    mockGet.mockResolvedValue(mockStatus)
    const { useGit } = await import('~/composables/useGit')
    const { status, fetchStatus } = useGit()
    await fetchStatus()
    expect(status.value).toEqual(mockStatus)
  })

  it('fetchStatus sets error on failure', async () => {
    mockGet.mockRejectedValue(new Error('Network error'))
    const { useGit } = await import('~/composables/useGit')
    const { error, fetchStatus } = useGit()
    await fetchStatus()
    expect(error.value).toBe('Network error')
  })

  it('initRepo appelle POST /api/git/init puis fetchStatus', async () => {
    mockPost.mockResolvedValue({ status: 'initialized' })
    mockGet.mockResolvedValue(mockStatus)
    const { useGit } = await import('~/composables/useGit')
    const { status, loading, initRepo } = useGit()
    await initRepo()
    expect(mockPost).toHaveBeenCalledWith('/api/git/init', {})
    expect(mockGet).toHaveBeenCalledWith('/api/git/status')
    expect(status.value).toEqual(mockStatus)
    expect(loading.value).toBe(false)
  })

  it('pushRepo appelle POST /api/git/push puis fetchStatus', async () => {
    mockPost.mockResolvedValue({ status: 'push_triggered' })
    mockGet.mockResolvedValue(mockStatus)
    const { useGit } = await import('~/composables/useGit')
    const { pushRepo } = useGit()
    await pushRepo()
    expect(mockPost).toHaveBeenCalledWith('/api/git/push', {})
    expect(mockGet).toHaveBeenCalledWith('/api/git/status')
  })

  it('initRepo set error et remet loading à false en cas d\'échec', async () => {
    mockPost.mockRejectedValue(new Error('Init failed'))
    const { useGit } = await import('~/composables/useGit')
    const { error, loading, initRepo } = useGit()
    await initRepo()
    expect(error.value).toBe('Init failed')
    expect(loading.value).toBe(false)
  })

  it('pushRepo set error et remet loading à false en cas d\'échec', async () => {
    mockPost.mockRejectedValue(new Error('Push failed'))
    const { useGit } = await import('~/composables/useGit')
    const { error, loading, pushRepo } = useGit()
    await pushRepo()
    expect(error.value).toBe('Push failed')
    expect(loading.value).toBe(false)
  })
})
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/frontend && npm run test -- tests/composables/useGit.test.ts
```

Résultat attendu : `ERROR` — `Cannot find module '~/composables/useGit'`

- [ ] **Step 3: Créer `frontend/composables/useGit.ts`**

```typescript
import { ref } from 'vue'
import { useApi } from '~/composables/useApi'
import type { GitStatus } from '~/types/api'

export function useGit() {
  const { get, post } = useApi()
  const status = ref<GitStatus | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchStatus(): Promise<void> {
    error.value = null
    try {
      status.value = await get<GitStatus>('/api/git/status')
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Erreur lors du chargement du statut git'
    }
  }

  async function initRepo(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      await post<{ status: string }>('/api/git/init', {})
      await fetchStatus()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : "Erreur lors de l'initialisation"
    } finally {
      loading.value = false
    }
  }

  async function pushRepo(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      await post<{ status: string }>('/api/git/push', {})
      await fetchStatus()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Erreur lors du push'
    } finally {
      loading.value = false
    }
  }

  return { status, loading, error, fetchStatus, initRepo, pushRepo }
}
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/frontend && npm run test -- tests/composables/useGit.test.ts
```

Résultat attendu : 6/6 `PASSED`

- [ ] **Step 5: Commit**

```bash
git add frontend/composables/useGit.ts frontend/tests/composables/useGit.test.ts
git commit -m "feat(frontend): add useGit composable"
```

---

### Task 3: Composant `GitSettings.vue`

**Files:**
- Create: `frontend/components/settings/GitSettings.vue`
- Create: `frontend/tests/components/GitSettings.test.ts`

- [ ] **Step 1: Créer le fichier de tests**

Créer `frontend/tests/components/GitSettings.test.ts` :

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import type { GitConfig, GitStatus } from '~/types/api'

vi.mock('~/composables/useGit', () => ({
  useGit: vi.fn(),
}))

import { useGit } from '~/composables/useGit'
import GitSettings from '~/components/settings/GitSettings.vue'

const defaultConfig: GitConfig = {
  enabled: false,
  auto_push: false,
  remote_url: '',
  branch: 'main',
}

function mockGit(overrides: {
  status?: GitStatus | null
  loading?: boolean
  error?: string | null
} = {}) {
  vi.mocked(useGit).mockReturnValue({
    status: ref(overrides.status ?? null),
    loading: ref(overrides.loading ?? false),
    error: ref(overrides.error ?? null),
    fetchStatus: vi.fn(),
    initRepo: vi.fn(),
    pushRepo: vi.fn(),
  })
}

describe('GitSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('état 1: toggle off — fieldset disabled, pas de bouton Init', () => {
    mockGit()
    const wrapper = mount(GitSettings, {
      props: { modelValue: { ...defaultConfig, enabled: false } },
    })
    const fieldset = wrapper.find('fieldset')
    expect(fieldset.exists()).toBe(true)
    expect((fieldset.element as HTMLFieldSetElement).disabled).toBe(true)
    expect(wrapper.text()).not.toContain('Initialiser')
    expect(wrapper.text()).not.toContain('Push')
  })

  it('état 2: activé non initialisé — bouton Init visible, pas de badge statut', () => {
    mockGit({
      status: { enabled: true, initialized: false, last_commit: null, dirty_files: 0 },
    })
    const wrapper = mount(GitSettings, {
      props: { modelValue: { ...defaultConfig, enabled: true } },
    })
    expect(wrapper.text()).toContain('Initialiser le dépôt git')
    expect(wrapper.text()).not.toContain('Push ↑')
    expect(wrapper.text()).not.toContain('Initialisé')
  })

  it('état 3: initialisé — badge statut, bouton Push, pas de bouton Init', () => {
    mockGit({
      status: {
        enabled: true,
        initialized: true,
        last_commit: 'abc1234 feat(wiki): ingest test',
        dirty_files: 2,
      },
    })
    const wrapper = mount(GitSettings, {
      props: { modelValue: { ...defaultConfig, enabled: true } },
    })
    expect(wrapper.text()).toContain('Initialisé')
    expect(wrapper.text()).toContain('2 fichiers modifiés')
    expect(wrapper.text()).toContain('Push ↑')
    expect(wrapper.text()).not.toContain('Initialiser')
  })

  it('état 3: affiche le hash du dernier commit', () => {
    mockGit({
      status: {
        enabled: true,
        initialized: true,
        last_commit: 'abc1234 feat(wiki): ingest test',
        dirty_files: 0,
      },
    })
    const wrapper = mount(GitSettings, {
      props: { modelValue: { ...defaultConfig, enabled: true } },
    })
    expect(wrapper.text()).toContain('abc1234')
  })

  it('clic toggle émet update:modelValue avec enabled inversé', async () => {
    mockGit()
    const wrapper = mount(GitSettings, {
      props: { modelValue: { ...defaultConfig, enabled: false } },
    })
    await wrapper.find('button').trigger('click')
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    expect((emitted![0][0] as GitConfig).enabled).toBe(true)
  })

  it('affiche l\'erreur en rouge si error est renseigné', () => {
    mockGit({ error: 'Erreur réseau' })
    const wrapper = mount(GitSettings, {
      props: { modelValue: { ...defaultConfig, enabled: true } },
    })
    expect(wrapper.text()).toContain('Erreur réseau')
  })
})
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/frontend && npm run test -- tests/components/GitSettings.test.ts
```

Résultat attendu : `ERROR` — `Cannot find module '~/components/settings/GitSettings.vue'`

- [ ] **Step 3: Créer `frontend/components/settings/GitSettings.vue`**

```vue
<template>
  <div class="space-y-4">
    <!-- Toggle -->
    <div class="flex items-center justify-between">
      <div>
        <span class="text-sm font-medium text-white">Dépôt git du wiki</span>
        <p class="text-xs text-gray-400 mt-0.5">Versionner automatiquement les pages</p>
      </div>
      <button
        :class="[
          'relative w-9 h-5 rounded-full transition-colors',
          local.enabled ? 'bg-blue-600' : 'bg-gray-700',
        ]"
        @click="toggle"
      >
        <span
          :class="[
            'absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform',
            local.enabled ? 'translate-x-4' : 'translate-x-0.5',
          ]"
        />
      </button>
    </div>

    <!-- Badge statut (état 3 : initialisé) -->
    <div
      v-if="local.enabled && status?.initialized"
      class="flex items-center justify-between bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5"
    >
      <div>
        <div class="flex items-center gap-2 mb-1">
          <span class="w-2 h-2 bg-green-500 rounded-full inline-block" />
          <span class="text-sm font-medium text-white">Initialisé</span>
          <span v-if="status.dirty_files > 0" class="text-xs text-gray-400">
            · {{ status.dirty_files }} fichier{{ status.dirty_files > 1 ? 's' : '' }} modifié{{ status.dirty_files > 1 ? 's' : '' }}
          </span>
        </div>
        <p v-if="status.last_commit" class="text-xs text-gray-500">
          Dernier commit :
          <code class="text-blue-400">{{ status.last_commit.split(' ')[0] }}</code>
          <span class="text-gray-400"> {{ status.last_commit.split(' ').slice(1).join(' ') }}</span>
        </p>
      </div>
      <button
        :disabled="loading"
        class="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white text-xs rounded-lg transition-colors whitespace-nowrap"
        @click="pushRepo"
      >
        {{ loading ? 'Push…' : 'Push ↑' }}
      </button>
    </div>

    <!-- Champs config -->
    <fieldset :disabled="!local.enabled" class="space-y-3 disabled:opacity-40">
      <div>
        <label class="block text-xs text-gray-400 mb-1">
          Remote URL <span class="text-gray-600">(optionnel)</span>
        </label>
        <input
          v-model="local.remote_url"
          type="text"
          placeholder="git@github.com:user/wiki.git"
          class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500 disabled:cursor-not-allowed"
          @input="emit('update:modelValue', { ...local })"
        />
      </div>
      <div class="flex items-end gap-3">
        <div class="flex-1">
          <label class="block text-xs text-gray-400 mb-1">Branche</label>
          <input
            v-model="local.branch"
            type="text"
            placeholder="main"
            class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500 disabled:cursor-not-allowed"
            @input="emit('update:modelValue', { ...local })"
          />
        </div>
        <div class="pb-1.5">
          <label class="block text-xs text-gray-400 mb-1">Auto-push</label>
          <button
            :class="[
              'relative w-8 h-4 rounded-full transition-colors',
              local.auto_push ? 'bg-blue-600' : 'bg-gray-700',
            ]"
            @click="toggleAutoPush"
          >
            <span
              :class="[
                'absolute top-0.5 w-3 h-3 bg-white rounded-full shadow transition-transform',
                local.auto_push ? 'translate-x-4' : 'translate-x-0.5',
              ]"
            />
          </button>
        </div>
      </div>
    </fieldset>

    <!-- Bouton Init (état 2 : activé non initialisé) -->
    <button
      v-if="local.enabled && !status?.initialized"
      :disabled="loading"
      class="w-full px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
      @click="initRepo"
    >
      {{ loading ? 'Initialisation…' : 'Initialiser le dépôt git' }}
    </button>

    <p v-if="error" class="text-xs text-red-400">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch, onMounted } from 'vue'
import { useGit } from '~/composables/useGit'
import type { GitConfig } from '~/types/api'

const props = defineProps<{ modelValue: GitConfig }>()
const emit = defineEmits<{ 'update:modelValue': [GitConfig] }>()

const { status, loading, error, fetchStatus, initRepo, pushRepo } = useGit()

const local = reactive({ ...props.modelValue })

watch(() => props.modelValue, (v) => { Object.assign(local, v) }, { deep: true })

watch(() => local.enabled, async (enabled) => {
  if (enabled && !status.value) await fetchStatus()
})

onMounted(async () => {
  if (props.modelValue.enabled) await fetchStatus()
})

function toggle() {
  local.enabled = !local.enabled
  emit('update:modelValue', { ...local })
}

function toggleAutoPush() {
  local.auto_push = !local.auto_push
  emit('update:modelValue', { ...local })
}
</script>
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/frontend && npm run test -- tests/components/GitSettings.test.ts
```

Résultat attendu : 6/6 `PASSED`

- [ ] **Step 5: Vérifier la suite complète**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/frontend && npm run test
```

Résultat attendu : tous `PASSED`

- [ ] **Step 6: Commit**

```bash
git add frontend/components/settings/GitSettings.vue frontend/tests/components/GitSettings.test.ts
git commit -m "feat(frontend): add GitSettings component"
```

---

### Task 4: Intégration dans `settings.vue`

**Files:**
- Modify: `frontend/pages/settings.vue`

- [ ] **Step 1: Ajouter la section Git dans `frontend/pages/settings.vue`**

Dans le template, après le bloc `<section>` Connecteurs (qui se termine avant `<div class="flex items-center gap-4">`), ajouter :

```vue
      <section class="p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-4">
        <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wider">Git</h2>
        <SettingsGitSettings v-model="settings.git" />
      </section>
```

Le template complet après modification ressemble à :

```vue
    <div v-if="settings" class="space-y-8">
      <section class="p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-4">
        <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wider">LLM</h2>
        <SettingsLLMSettings v-model="settings.llm" />
      </section>

      <section class="p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-4">
        <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wider">Ingestion</h2>
        <SettingsIngestSettings v-model="settings.ingest" />
      </section>

      <section class="p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-4">
        <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wider">Connecteurs</h2>
        <SettingsConnectorsSettings
          v-model="settings.connectors"
          :connection-failed="connectionFailed"
          @connect="handleConnect"
          @disconnect="handleDisconnect"
        />
      </section>

      <section class="p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-4">
        <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wider">Git</h2>
        <SettingsGitSettings v-model="settings.git" />
      </section>

      <div class="flex items-center gap-4">
        ...
```

- [ ] **Step 2: Vérifier la suite de tests complète**

```bash
cd /Users/lachose/PycharmProjects/open-wiki-llm/frontend && npm run test
```

Résultat attendu : tous `PASSED`

- [ ] **Step 3: Commit**

```bash
git add frontend/pages/settings.vue
git commit -m "feat(frontend): add Git section in settings page"
```
