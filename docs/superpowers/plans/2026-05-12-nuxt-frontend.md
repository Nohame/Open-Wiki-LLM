# OpenWikiLLM Frontend Nuxt Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire un frontend Nuxt 3 SPA (Chat + Wiki + Ingest) connecté à l'API OpenWikiLLM, inspiré du design Langflow/OpenRag.

**Architecture:** Nuxt 3 mode SPA (`ssr: false`), appels `$fetch` directs vers l'API depuis le browser, clé API stockée en localStorage injectée en header `X-API-Key` sur chaque requête. Build statique `nuxt generate` servi par nginx:alpine dans Docker sur le port 3000.

**Tech Stack:** Nuxt 3.15, TypeScript, Tailwind CSS 3, `@nuxtjs/tailwindcss`, Pinia 2 + `@pinia/nuxt`, VueUse, marked 14, DOMPurify 3, lucide-vue-next, Vitest 2 + happy-dom

---

## Contexte API

Base URL : `http://localhost:8088` (configurable via `NUXT_PUBLIC_API_BASE_URL`)
Auth : header `X-API-Key` (vide = pas d'auth côté backend)

Endpoints utilisés :
- `GET /health` → `{ status: "ok", version: "0.1.0" }` — validation clé
- `GET /api/pages` → `WikiPageSummary[]`
- `GET /api/pages/{slug}` → `WikiPage`
- `POST /api/search` body `{ q, limit }` → `SearchResult[]`
- `POST /api/answer` body `{ question, mode }` → `AnswerResponse`
- `POST /api/ingest/text` body `{ text, title?, tags }` → `IngestResult`
- `POST /api/ingest/image` multipart `file + title? + tags` → `IngestResult`

---

## Structure fichiers

```
frontend/
├── package.json
├── nuxt.config.ts
├── tailwind.config.ts
├── vitest.config.ts
├── app.vue
├── types/api.ts
├── stores/auth.ts
├── composables/
│   ├── useApi.ts
│   ├── useChat.ts
│   ├── useWiki.ts
│   └── useIngest.ts
├── middleware/auth.global.ts
├── pages/
│   ├── login.vue
│   ├── index.vue
│   ├── chat.vue
│   ├── wiki/index.vue
│   ├── wiki/[slug].vue
│   └── ingest.vue
├── components/
│   ├── layout/AppSidebar.vue
│   ├── layout/AppHeader.vue
│   ├── chat/ChatMessage.vue
│   ├── chat/SourceChip.vue
│   ├── chat/ChatMessages.vue
│   ├── chat/ChatInput.vue
│   ├── wiki/WikiPageCard.vue
│   ├── wiki/WikiSearchBar.vue
│   ├── wiki/MarkdownViewer.vue
│   ├── ingest/IngestText.vue
│   └── ingest/IngestImage.vue
├── tests/
│   ├── stores/auth.test.ts
│   ├── composables/useChat.test.ts
│   ├── composables/useWiki.test.ts
│   └── composables/useIngest.test.ts
└── Dockerfile
```

---

## Task 1 : Scaffold — configuration de base

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/nuxt.config.ts`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/types/api.ts`
- Create: `frontend/app.vue`

---

- [ ] **Step 1 : Créer `frontend/package.json`**

```json
{
  "name": "openwikillm-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "nuxt dev",
    "build": "nuxt build",
    "generate": "nuxt generate",
    "preview": "nuxt preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "nuxt": "^3.15.0",
    "vue": "^3.5.0",
    "pinia": "^2.2.0",
    "@pinia/nuxt": "^0.9.0",
    "@vueuse/nuxt": "^11.0.0",
    "@vueuse/core": "^11.0.0",
    "lucide-vue-next": "^0.462.0",
    "marked": "^14.0.0",
    "dompurify": "^3.1.0"
  },
  "devDependencies": {
    "@nuxtjs/tailwindcss": "^6.12.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.0.0",
    "vitest": "^2.0.0",
    "@vue/test-utils": "^2.4.0",
    "happy-dom": "^15.0.0",
    "@types/dompurify": "^3.0.0",
    "@vitejs/plugin-vue": "^5.0.0",
    "@tailwindcss/typography": "^0.5.0"
  }
}
```

- [ ] **Step 2 : Créer `frontend/nuxt.config.ts`**

```typescript
export default defineNuxtConfig({
  ssr: false,
  modules: ['@nuxtjs/tailwindcss', '@pinia/nuxt', '@vueuse/nuxt'],
  runtimeConfig: {
    public: {
      apiBaseUrl: 'http://localhost:8088',
    },
  },
  app: {
    head: {
      title: 'OpenWikiLLM',
      htmlAttrs: { class: 'dark' },
    },
  },
})
```

- [ ] **Step 3 : Créer `frontend/tailwind.config.ts`**

```typescript
import type { Config } from 'tailwindcss'

export default {
  darkMode: 'class',
  content: [
    './components/**/*.{vue,ts}',
    './layouts/**/*.vue',
    './pages/**/*.vue',
    './app.vue',
  ],
  plugins: [require('@tailwindcss/typography')],
  theme: {
    extend: {
      colors: {
        sidebar: {
          DEFAULT: '#1e293b',
          dark: '#192638',
        },
      },
    },
  },
} satisfies Config
```

- [ ] **Step 4 : Créer `frontend/vitest.config.ts`**

```typescript
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'happy-dom',
    globals: true,
  },
  resolve: {
    alias: {
      '~': resolve(__dirname, '.'),
    },
  },
})
```

- [ ] **Step 5 : Créer `frontend/types/api.ts`**

```typescript
export interface WikiPageSummary {
  slug: string
  title: string
  type: string
  status: string
  confidence: string
  sources: string[]
  updated_at: string
  tags: string[]
}

export interface WikiPage extends WikiPageSummary {
  content: string
}

export interface SearchResult {
  slug: string
  title: string
  snippet: string
  score: number
}

export interface AnswerResponse {
  answer: string
  mode: string
  sources: string[]
}

export interface IngestResult {
  slug: string
  raw_path: string
  wiki_path: string
  title: string
}

export type AnswerMode = 'validated_only' | 'strict' | 'draft' | 'source_only'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
}
```

- [ ] **Step 6 : Créer `frontend/app.vue`**

```vue
<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>
```

- [ ] **Step 7 : Installer les dépendances**

```bash
cd frontend
npm install
```

Expected: dossier `node_modules/` créé, pas d'erreur.

- [ ] **Step 8 : Vérifier que Nuxt démarre**

```bash
npm run dev
```

Expected: `Nuxt 3.x.x ready` sur `http://localhost:3000`. Page blanche sans erreur console = OK.

Arrêter avec `Ctrl+C`.

- [ ] **Step 9 : Commit**

```bash
cd ..
git add frontend/
git commit -m "feat(frontend): scaffold Nuxt 3 SPA — config, types, tailwind"
```

---

## Task 2 : Auth — store, composable API, middleware, page login

**Files:**
- Create: `frontend/stores/auth.ts`
- Create: `frontend/composables/useApi.ts`
- Create: `frontend/middleware/auth.global.ts`
- Create: `frontend/pages/login.vue`
- Create: `frontend/tests/stores/auth.test.ts`

---

- [ ] **Step 1 : Écrire le test du store auth**

Créer `frontend/tests/stores/auth.test.ts` :

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '~/stores/auth'

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('démarre non authentifié', () => {
    const store = useAuthStore()
    expect(store.isAuthenticated).toBe(false)
    expect(store.apiKey).toBe('')
  })

  it('setApiKey met à jour la clé et localStorage', () => {
    const store = useAuthStore()
    store.setApiKey('test-key-123')
    expect(store.apiKey).toBe('test-key-123')
    expect(store.isAuthenticated).toBe(true)
    expect(localStorage.getItem('openwikillm_api_key')).toBe('test-key-123')
  })

  it('loadFromStorage charge depuis localStorage', () => {
    localStorage.setItem('openwikillm_api_key', 'stored-key')
    const store = useAuthStore()
    store.loadFromStorage()
    expect(store.apiKey).toBe('stored-key')
    expect(store.isAuthenticated).toBe(true)
  })

  it('logout efface la clé et localStorage', () => {
    const store = useAuthStore()
    store.setApiKey('some-key')
    store.logout()
    expect(store.apiKey).toBe('')
    expect(store.isAuthenticated).toBe(false)
    expect(localStorage.getItem('openwikillm_api_key')).toBeNull()
  })
})
```

- [ ] **Step 2 : Lancer le test — vérifier qu'il échoue**

```bash
cd frontend
npm test -- tests/stores/auth.test.ts
```

Expected: FAIL — `Cannot find module '~/stores/auth'`

- [ ] **Step 3 : Créer `frontend/stores/auth.ts`**

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const apiKey = ref('')
  const isAuthenticated = computed(() => !!apiKey.value)

  function setApiKey(key: string) {
    apiKey.value = key
    if (typeof window !== 'undefined') {
      localStorage.setItem('openwikillm_api_key', key)
    }
  }

  function loadFromStorage() {
    if (typeof window !== 'undefined') {
      apiKey.value = localStorage.getItem('openwikillm_api_key') || ''
    }
  }

  function logout() {
    apiKey.value = ''
    if (typeof window !== 'undefined') {
      localStorage.removeItem('openwikillm_api_key')
    }
  }

  return { apiKey, isAuthenticated, setApiKey, loadFromStorage, logout }
})
```

- [ ] **Step 4 : Relancer le test — vérifier qu'il passe**

```bash
npm test -- tests/stores/auth.test.ts
```

Expected: PASS — 4 tests passés.

- [ ] **Step 5 : Créer `frontend/composables/useApi.ts`**

```typescript
import { useAuthStore } from '~/stores/auth'

export function useApi() {
  const authStore = useAuthStore()
  const config = useRuntimeConfig()
  const baseUrl = config.public.apiBaseUrl as string

  function headers(extra: Record<string, string> = {}): Record<string, string> {
    const h: Record<string, string> = { ...extra }
    if (authStore.apiKey) h['X-API-Key'] = authStore.apiKey
    return h
  }

  async function get<T>(path: string): Promise<T> {
    return $fetch<T>(`${baseUrl}${path}`, {
      headers: headers(),
      onResponseError({ response }) {
        if (response.status === 401) {
          authStore.logout()
          navigateTo('/login')
        }
      },
    })
  }

  async function post<T>(path: string, body: unknown): Promise<T> {
    return $fetch<T>(`${baseUrl}${path}`, {
      method: 'POST',
      headers: headers({ 'Content-Type': 'application/json' }),
      body,
      onResponseError({ response }) {
        if (response.status === 401) {
          authStore.logout()
          navigateTo('/login')
        }
      },
    })
  }

  async function postForm<T>(path: string, formData: FormData): Promise<T> {
    return $fetch<T>(`${baseUrl}${path}`, {
      method: 'POST',
      headers: headers(),
      body: formData,
      onResponseError({ response }) {
        if (response.status === 401) {
          authStore.logout()
          navigateTo('/login')
        }
      },
    })
  }

  return { get, post, postForm }
}
```

- [ ] **Step 6 : Créer `frontend/middleware/auth.global.ts`**

```typescript
export default defineNuxtRouteMiddleware((to) => {
  if (to.path === '/login') return

  if (typeof window !== 'undefined') {
    const key = localStorage.getItem('openwikillm_api_key')
    if (!key) return navigateTo('/login')
  }
})
```

- [ ] **Step 7 : Créer `frontend/pages/login.vue`**

```vue
<template>
  <div class="min-h-screen bg-gray-950 flex items-center justify-center">
    <div class="w-full max-w-sm space-y-6 p-8">
      <div class="text-center space-y-2">
        <div class="w-10 h-10 rounded-full bg-blue-600 mx-auto flex items-center justify-center">
          <BookOpen class="w-5 h-5 text-white" />
        </div>
        <h1 class="text-2xl font-bold text-white">OpenWikiLLM</h1>
        <p class="text-gray-400 text-sm">Connexion à l'API</p>
      </div>

      <form class="space-y-4" @submit.prevent="handleLogin">
        <div class="space-y-1">
          <label class="block text-sm text-gray-300">Clé API</label>
          <input
            v-model="apiKey"
            type="password"
            placeholder="Laisser vide si pas d'auth"
            class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
        </div>

        <p v-if="error" class="text-red-400 text-sm">{{ error }}</p>

        <button
          type="submit"
          :disabled="loading"
          class="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg font-medium transition-colors"
        >
          {{ loading ? 'Connexion...' : 'Connexion' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { BookOpen } from 'lucide-vue-next'

definePageMeta({ layout: false })

const config = useRuntimeConfig()
const authStore = useAuthStore()

const apiKey = ref('')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    const h: Record<string, string> = {}
    if (apiKey.value) h['X-API-Key'] = apiKey.value
    await $fetch(`${config.public.apiBaseUrl}/health`, { headers: h })
    authStore.setApiKey(apiKey.value)
    await navigateTo('/chat')
  } catch {
    error.value = 'Clé invalide ou API inaccessible.'
  } finally {
    loading.value = false
  }
}
</script>
```

- [ ] **Step 8 : Créer `frontend/pages/index.vue`**

```vue
<script setup lang="ts">
navigateTo('/chat')
</script>
```

- [ ] **Step 9 : Tester manuellement**

```bash
npm run dev
```

Ouvrir `http://localhost:3000`. Doit rediriger vers `/login`.
Saisir la clé `Azerty12` (ou vide si API_KEY vide). Cliquer "Connexion".
Expected : redirect vers `/chat` (page vide pour l'instant).

- [ ] **Step 10 : Commit**

```bash
cd ..
git add frontend/
git commit -m "feat(frontend): auth store, useApi, middleware, page login"
```

---

## Task 3 : Layout shell — sidebar + header

**Files:**
- Create: `frontend/layouts/default.vue`
- Create: `frontend/components/layout/AppSidebar.vue`
- Create: `frontend/components/layout/AppHeader.vue`

---

- [ ] **Step 1 : Créer `frontend/layouts/default.vue`**

```vue
<template>
  <div class="flex h-screen bg-gray-950 text-white overflow-hidden">
    <AppSidebar />
    <div class="flex flex-col flex-1 overflow-hidden">
      <AppHeader />
      <main class="flex-1 overflow-auto">
        <slot />
      </main>
    </div>
  </div>
</template>
```

- [ ] **Step 2 : Créer `frontend/components/layout/AppSidebar.vue`**

```vue
<template>
  <aside
    :class="[
      'flex flex-col bg-sidebar-dark border-r border-gray-800 transition-all duration-200 shrink-0',
      collapsed ? 'w-12' : 'w-64',
    ]"
  >
    <!-- Logo -->
    <div class="flex items-center h-14 px-3 border-b border-gray-800">
      <div class="w-6 h-6 rounded-full bg-blue-600 shrink-0 flex items-center justify-center">
        <BookOpen class="w-3 h-3 text-white" />
      </div>
      <span v-if="!collapsed" class="ml-3 font-semibold text-white truncate">OpenWikiLLM</span>
    </div>

    <!-- Nav -->
    <nav class="flex-1 p-2 space-y-1">
      <NuxtLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="flex items-center gap-3 px-2 py-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
        active-class="text-white bg-gray-800"
      >
        <component :is="item.icon" class="w-4 h-4 shrink-0" />
        <span v-if="!collapsed" class="text-sm">{{ item.label }}</span>
      </NuxtLink>
    </nav>

    <!-- Toggle -->
    <div class="p-2 border-t border-gray-800">
      <button
        class="flex items-center gap-3 px-2 py-2 w-full rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
        @click="toggle"
      >
        <PanelLeft class="w-4 h-4 shrink-0" />
        <span v-if="!collapsed" class="text-sm">Réduire</span>
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { BookOpen, MessageSquare, Library, Upload, PanelLeft } from 'lucide-vue-next'
import { useLocalStorage } from '@vueuse/core'

const collapsed = useLocalStorage('sidebar-collapsed', false)

function toggle() {
  collapsed.value = !collapsed.value
}

const navItems = [
  { to: '/chat', icon: MessageSquare, label: 'Chat' },
  { to: '/wiki', icon: Library, label: 'Wiki' },
  { to: '/ingest', icon: Upload, label: 'Ingest' },
]
</script>
```

- [ ] **Step 3 : Créer `frontend/components/layout/AppHeader.vue`**

```vue
<template>
  <header class="h-14 flex items-center justify-between px-4 border-b border-gray-800 bg-gray-950 shrink-0">
    <h2 class="text-sm font-medium text-gray-300">{{ pageTitle }}</h2>
    <div class="flex items-center gap-2">
      <span class="w-2 h-2 rounded-full bg-green-500"></span>
      <span class="text-xs text-gray-400">Connecté</span>
      <button
        class="ml-4 text-xs text-gray-500 hover:text-white transition-colors"
        @click="logout"
      >
        Déconnexion
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
const route = useRoute()
const authStore = useAuthStore()

const pageTitles: Record<string, string> = {
  '/chat': 'Chat',
  '/wiki': 'Wiki',
  '/ingest': 'Ingest',
}

const pageTitle = computed(() => pageTitles[route.path] || 'OpenWikiLLM')

async function logout() {
  authStore.logout()
  await navigateTo('/login')
}
</script>
```

- [ ] **Step 4 : Tester manuellement**

```bash
npm run dev
```

Se connecter. Vérifier :
- Sidebar s'affiche avec les 3 liens
- Clic sur "Réduire" → sidebar en mode icônes (48px)
- L'état persiste après refresh (localStorage)
- Header affiche "Connecté" et le titre de la page

- [ ] **Step 5 : Commit**

```bash
cd ..
git add frontend/
git commit -m "feat(frontend): layout shell — sidebar collapsible + header"
```

---

## Task 4 : Page Chat

**Files:**
- Create: `frontend/composables/useChat.ts`
- Create: `frontend/components/chat/ChatMessage.vue`
- Create: `frontend/components/chat/SourceChip.vue`
- Create: `frontend/components/chat/ChatMessages.vue`
- Create: `frontend/components/chat/ChatInput.vue`
- Create: `frontend/pages/chat.vue`
- Create: `frontend/tests/composables/useChat.test.ts`

---

- [ ] **Step 1 : Écrire le test de useChat**

Créer `frontend/tests/composables/useChat.test.ts` :

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('~/composables/useApi', () => ({
  useApi: () => ({
    post: vi.fn().mockResolvedValue({
      answer: 'La livraison est en 24h.',
      mode: 'validated_only',
      sources: ['imports--livraison-24h'],
    }),
    get: vi.fn(),
    postForm: vi.fn(),
  }),
}))

vi.mock('#imports', () => ({
  useRuntimeConfig: () => ({ public: { apiBaseUrl: 'http://localhost:8088' } }),
  navigateTo: vi.fn(),
  useRoute: () => ({ path: '/chat' }),
  useRouter: () => ({}),
  ref: (v: unknown) => ({ value: v }),
  computed: (fn: () => unknown) => ({ value: fn() }),
}), { virtual: true })

describe('useChat', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('démarre avec historique vide', async () => {
    const { useChat } = await import('~/composables/useChat')
    const { messages, loading } = useChat()
    expect(messages.value).toHaveLength(0)
    expect(loading.value).toBe(false)
  })

  it('sendMessage ajoute les messages user et assistant', async () => {
    const { useChat } = await import('~/composables/useChat')
    const { messages, sendMessage } = useChat()
    await sendMessage('Quel délai de livraison ?', 'validated_only')
    expect(messages.value).toHaveLength(2)
    expect(messages.value[0].role).toBe('user')
    expect(messages.value[0].content).toBe('Quel délai de livraison ?')
    expect(messages.value[1].role).toBe('assistant')
    expect(messages.value[1].content).toBe('La livraison est en 24h.')
    expect(messages.value[1].sources).toEqual(['imports--livraison-24h'])
  })
})
```

- [ ] **Step 2 : Lancer le test — vérifier qu'il échoue**

```bash
npm test -- tests/composables/useChat.test.ts
```

Expected: FAIL — `Cannot find module '~/composables/useChat'`

- [ ] **Step 3 : Créer `frontend/composables/useChat.ts`**

```typescript
import type { ChatMessage, AnswerMode } from '~/types/api'

export function useChat() {
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const error = ref('')
  const { post } = useApi()

  async function sendMessage(question: string, mode: AnswerMode) {
    messages.value.push({ role: 'user', content: question })
    loading.value = true
    error.value = ''
    try {
      const data = await post<{ answer: string; mode: string; sources: string[] }>(
        '/api/answer',
        { question, mode },
      )
      messages.value.push({
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
      })
    } catch {
      error.value = 'Erreur lors de la requête.'
    } finally {
      loading.value = false
    }
  }

  function clearHistory() {
    messages.value = []
  }

  return { messages, loading, error, sendMessage, clearHistory }
}
```

- [ ] **Step 4 : Relancer le test — vérifier qu'il passe**

```bash
npm test -- tests/composables/useChat.test.ts
```

Expected: PASS — 2 tests passés.

- [ ] **Step 5 : Créer `frontend/components/chat/SourceChip.vue`**

```vue
<template>
  <NuxtLink
    :to="`/wiki/${slug}`"
    class="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded text-xs text-blue-400 hover:text-blue-300 transition-colors"
  >
    <FileText class="w-3 h-3" />
    {{ slug }}
  </NuxtLink>
</template>

<script setup lang="ts">
import { FileText } from 'lucide-vue-next'
defineProps<{ slug: string }>()
</script>
```

- [ ] **Step 6 : Créer `frontend/components/chat/ChatMessage.vue`**

```vue
<template>
  <div :class="['flex gap-3', isUser ? 'flex-row-reverse' : 'flex-row']">
    <!-- Avatar -->
    <div
      :class="[
        'w-7 h-7 rounded-full shrink-0 flex items-center justify-center text-xs font-bold mt-1',
        isUser ? 'bg-blue-600' : 'bg-gray-700',
      ]"
    >
      {{ isUser ? 'U' : 'W' }}
    </div>

    <!-- Contenu -->
    <div :class="['max-w-2xl space-y-2', isUser ? 'items-end' : 'items-start']">
      <div
        :class="[
          'px-4 py-3 rounded-xl text-sm',
          isUser
            ? 'bg-blue-600 text-white rounded-tr-none'
            : 'bg-gray-800 text-gray-100 rounded-tl-none',
        ]"
      >
        <!-- eslint-disable vue/no-v-html -->
        <div
          v-if="!isUser"
          class="prose prose-invert prose-sm max-w-none"
          v-html="renderedContent"
        />
        <span v-else>{{ message.content }}</span>
      </div>

      <!-- Sources -->
      <div v-if="message.sources?.length" class="flex flex-wrap gap-1 px-1">
        <SourceChip v-for="s in message.sources" :key="s" :slug="s" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import type { ChatMessage } from '~/types/api'

const props = defineProps<{ message: ChatMessage }>()

const isUser = computed(() => props.message.role === 'user')
const renderedContent = computed(() =>
  DOMPurify.sanitize(marked.parse(props.message.content) as string),
)
</script>
```

- [ ] **Step 7 : Créer `frontend/components/chat/ChatMessages.vue`**

```vue
<template>
  <div ref="container" class="flex-1 overflow-y-auto px-4 py-6 space-y-6">
    <!-- État vide -->
    <div v-if="!messages.length" class="flex flex-col items-center justify-center h-full text-center space-y-3">
      <div class="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center">
        <BookOpen class="w-6 h-6 text-gray-400" />
      </div>
      <p class="text-gray-400 text-sm">Pose une question sur le wiki</p>
    </div>

    <ChatMessage v-for="(msg, i) in messages" :key="i" :message="msg" />

    <!-- Indicateur loading -->
    <div v-if="loading" class="flex gap-3">
      <div class="w-7 h-7 rounded-full bg-gray-700 shrink-0 flex items-center justify-center text-xs font-bold">W</div>
      <div class="px-4 py-3 bg-gray-800 rounded-xl rounded-tl-none">
        <div class="flex gap-1">
          <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay:0ms" />
          <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay:150ms" />
          <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay:300ms" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { BookOpen } from 'lucide-vue-next'
import type { ChatMessage as ChatMsg } from '~/types/api'

const props = defineProps<{ messages: ChatMsg[]; loading: boolean }>()
const container = ref<HTMLElement>()

watch(
  () => [props.messages.length, props.loading],
  async () => {
    await nextTick()
    if (container.value) {
      container.value.scrollTop = container.value.scrollHeight
    }
  },
)
</script>
```

- [ ] **Step 8 : Créer `frontend/components/chat/ChatInput.vue`**

```vue
<template>
  <div class="border-t border-gray-800 p-4 space-y-3">
    <div class="flex items-center gap-2">
      <label class="text-xs text-gray-400">Mode :</label>
      <select
        v-model="selectedMode"
        class="text-xs bg-gray-800 border border-gray-700 text-gray-300 rounded px-2 py-1 focus:outline-none focus:border-blue-500"
      >
        <option value="validated_only">validated_only</option>
        <option value="strict">strict</option>
        <option value="draft">draft</option>
        <option value="source_only">source_only</option>
      </select>
    </div>

    <div class="flex gap-2">
      <textarea
        ref="textarea"
        v-model="input"
        rows="1"
        placeholder="Pose ta question..."
        :disabled="loading"
        class="flex-1 bg-gray-800 border border-gray-700 text-white placeholder-gray-500 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:border-blue-500 disabled:opacity-50"
        style="min-height: 48px; max-height: 200px"
        @keydown.meta.enter.prevent="submit"
        @keydown.ctrl.enter.prevent="submit"
        @input="autoResize"
      />
      <button
        :disabled="!input.trim() || loading"
        class="px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-xl transition-colors shrink-0"
        @click="submit"
      >
        <Send class="w-4 h-4" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Send } from 'lucide-vue-next'
import type { AnswerMode } from '~/types/api'

const props = defineProps<{ loading: boolean }>()
const emit = defineEmits<{ send: [question: string, mode: AnswerMode] }>()

const input = ref('')
const selectedMode = ref<AnswerMode>('validated_only')
const textarea = ref<HTMLTextAreaElement>()

function autoResize() {
  if (!textarea.value) return
  textarea.value.style.height = 'auto'
  textarea.value.style.height = `${Math.min(textarea.value.scrollHeight, 200)}px`
}

function submit() {
  if (!input.value.trim() || props.loading) return
  emit('send', input.value.trim(), selectedMode.value)
  input.value = ''
  if (textarea.value) textarea.value.style.height = '48px'
}
</script>
```

- [ ] **Step 9 : Créer `frontend/pages/chat.vue`**

```vue
<template>
  <div class="flex flex-col h-full">
    <ChatMessages :messages="messages" :loading="loading" />
    <ChatInput :loading="loading" @send="sendMessage" />
  </div>
</template>

<script setup lang="ts">
const { messages, loading, sendMessage } = useChat()
</script>
```

- [ ] **Step 10 : Tester manuellement**

```bash
npm run dev
```

Se connecter. Sur `/chat` :
- Zone de messages vide avec message d'accueil
- Saisir une question, Cmd+Enter ou bouton envoyer
- Expected : message user s'affiche, indicateur loading, puis réponse assistant avec sources cliquables

- [ ] **Step 11 : Commit**

```bash
cd ..
git add frontend/
git commit -m "feat(frontend): page chat — messages, input, modes, sources"
```

---

## Task 5 : Page Wiki — liste + recherche

**Files:**
- Create: `frontend/composables/useWiki.ts`
- Create: `frontend/components/wiki/WikiSearchBar.vue`
- Create: `frontend/components/wiki/WikiPageCard.vue`
- Create: `frontend/pages/wiki/index.vue`
- Create: `frontend/tests/composables/useWiki.test.ts`

---

- [ ] **Step 1 : Écrire le test de useWiki**

Créer `frontend/tests/composables/useWiki.test.ts` :

```typescript
import { describe, it, expect, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const mockPage = {
  slug: 'imports--livraison',
  title: 'Livraison 24h',
  type: 'concept',
  status: 'validated',
  confidence: 'high',
  sources: ['raw/imports/livraison.md'],
  updated_at: '2026-05-12',
  tags: ['livraison'],
}

vi.mock('~/composables/useApi', () => ({
  useApi: () => ({
    get: vi.fn().mockResolvedValue([mockPage]),
    post: vi.fn().mockResolvedValue([
      { slug: 'imports--livraison', title: 'Livraison 24h', snippet: 'délai 24h', score: 1.5 },
    ]),
    postForm: vi.fn(),
  }),
}))

vi.mock('#imports', () => ({
  useRuntimeConfig: () => ({ public: { apiBaseUrl: 'http://localhost:8088' } }),
  navigateTo: vi.fn(),
  ref: (v: unknown) => ({ value: v }),
  computed: (fn: () => unknown) => ({ value: fn() }),
}), { virtual: true })

describe('useWiki', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('fetchPages charge la liste', async () => {
    const { useWiki } = await import('~/composables/useWiki')
    const { pages, fetchPages } = useWiki()
    await fetchPages()
    expect(pages.value).toHaveLength(1)
    expect(pages.value[0].slug).toBe('imports--livraison')
  })

  it('search retourne des résultats', async () => {
    const { useWiki } = await import('~/composables/useWiki')
    const { searchResults, search } = useWiki()
    await search('livraison')
    expect(searchResults.value).toHaveLength(1)
    expect(searchResults.value[0].slug).toBe('imports--livraison')
  })
})
```

- [ ] **Step 2 : Lancer le test — vérifier qu'il échoue**

```bash
npm test -- tests/composables/useWiki.test.ts
```

Expected: FAIL — `Cannot find module '~/composables/useWiki'`

- [ ] **Step 3 : Créer `frontend/composables/useWiki.ts`**

```typescript
import type { WikiPageSummary, WikiPage, SearchResult } from '~/types/api'

export function useWiki() {
  const pages = ref<WikiPageSummary[]>([])
  const searchResults = ref<SearchResult[]>([])
  const currentPage = ref<WikiPage | null>(null)
  const loading = ref(false)
  const error = ref('')
  const { get, post } = useApi()

  async function fetchPages() {
    loading.value = true
    error.value = ''
    try {
      pages.value = await get<WikiPageSummary[]>('/api/pages')
    } catch {
      error.value = 'Impossible de charger les pages.'
    } finally {
      loading.value = false
    }
  }

  async function search(q: string) {
    if (!q.trim()) {
      searchResults.value = []
      return
    }
    loading.value = true
    try {
      searchResults.value = await post<SearchResult[]>('/api/search', { q, limit: 20 })
    } catch {
      searchResults.value = []
    } finally {
      loading.value = false
    }
  }

  async function fetchPage(slug: string) {
    loading.value = true
    error.value = ''
    try {
      currentPage.value = await get<WikiPage>(`/api/pages/${slug}`)
    } catch {
      error.value = 'Page introuvable.'
      currentPage.value = null
    } finally {
      loading.value = false
    }
  }

  return { pages, searchResults, currentPage, loading, error, fetchPages, search, fetchPage }
}
```

- [ ] **Step 4 : Relancer le test — vérifier qu'il passe**

```bash
npm test -- tests/composables/useWiki.test.ts
```

Expected: PASS — 2 tests passés.

- [ ] **Step 5 : Créer `frontend/components/wiki/WikiSearchBar.vue`**

```vue
<template>
  <div class="relative">
    <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
    <input
      :value="modelValue"
      type="text"
      placeholder="Rechercher dans le wiki..."
      class="w-full pl-9 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    />
  </div>
</template>

<script setup lang="ts">
import { Search } from 'lucide-vue-next'
defineProps<{ modelValue: string }>()
defineEmits<{ 'update:modelValue': [value: string] }>()
</script>
```

- [ ] **Step 6 : Créer `frontend/components/wiki/WikiPageCard.vue`**

```vue
<template>
  <NuxtLink
    :to="`/wiki/${page.slug}`"
    class="block p-4 bg-gray-900 border border-gray-800 rounded-xl hover:border-gray-600 hover:bg-gray-800 transition-colors space-y-2"
  >
    <div class="flex items-start justify-between gap-2">
      <h3 class="font-medium text-white text-sm leading-snug">{{ page.title }}</h3>
      <span
        :class="[
          'shrink-0 px-2 py-0.5 rounded text-xs font-medium',
          page.status === 'validated'
            ? 'bg-green-900 text-green-300'
            : page.status === 'draft'
              ? 'bg-yellow-900 text-yellow-300'
              : 'bg-gray-700 text-gray-400',
        ]"
      >
        {{ page.status || '—' }}
      </span>
    </div>

    <div v-if="page.tags?.length" class="flex flex-wrap gap-1">
      <span
        v-for="tag in page.tags.slice(0, 4)"
        :key="tag"
        class="px-2 py-0.5 bg-gray-800 rounded text-xs text-gray-400"
      >
        #{{ tag }}
      </span>
    </div>

    <p v-if="page.updated_at" class="text-xs text-gray-500">{{ page.updated_at }}</p>
  </NuxtLink>
</template>

<script setup lang="ts">
import type { WikiPageSummary } from '~/types/api'
defineProps<{ page: WikiPageSummary }>()
</script>
```

- [ ] **Step 7 : Créer `frontend/pages/wiki/index.vue`**

```vue
<template>
  <div class="p-6 space-y-6 max-w-5xl mx-auto">
    <WikiSearchBar v-model="query" />

    <div v-if="loading" class="text-gray-400 text-sm">Chargement...</div>
    <div v-else-if="error" class="text-red-400 text-sm">{{ error }}</div>

    <div v-else>
      <p class="text-xs text-gray-500 mb-4">
        {{ displayedPages.length }} page{{ displayedPages.length > 1 ? 's' : '' }}
      </p>
      <div v-if="displayedPages.length" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <WikiPageCard v-for="page in displayedPages" :key="page.slug" :page="page" />
      </div>
      <p v-else class="text-gray-400 text-sm">Aucun résultat.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDebounceFn } from '@vueuse/core'
import type { WikiPageSummary } from '~/types/api'

const { pages, searchResults, loading, error, fetchPages, search } = useWiki()

const query = ref('')

const displayedPages = computed<WikiPageSummary[]>(() => {
  if (query.value.trim()) {
    return searchResults.value.map((r) => ({
      slug: r.slug,
      title: r.title,
      type: '',
      status: '',
      confidence: '',
      sources: [],
      updated_at: '',
      tags: [],
    }))
  }
  return pages.value
})

const debouncedSearch = useDebounceFn((q: string) => search(q), 300)

watch(query, (q) => {
  if (q.trim()) debouncedSearch(q)
})

onMounted(() => fetchPages())
</script>
```

- [ ] **Step 8 : Tester manuellement**

Ouvrir `/wiki`. Vérifier :
- Liste de pages s'affiche en grille
- Rechercher "livraison" → résultats filtrés en temps réel (debounce 300ms)
- Vider la recherche → liste complète revient
- Badges de statut colorés (vert=validated, jaune=draft)

- [ ] **Step 9 : Commit**

```bash
cd ..
git add frontend/
git commit -m "feat(frontend): page wiki — liste, recherche FTS5, cards"
```

---

## Task 6 : Page Wiki détail

**Files:**
- Create: `frontend/components/wiki/MarkdownViewer.vue`
- Create: `frontend/pages/wiki/[slug].vue`

---

- [ ] **Step 1 : Créer `frontend/components/wiki/MarkdownViewer.vue`**

```vue
<template>
  <!-- eslint-disable vue/no-v-html -->
  <div
    class="prose prose-invert prose-sm max-w-none
           prose-headings:text-white prose-p:text-gray-300
           prose-code:text-blue-300 prose-pre:bg-gray-800
           prose-a:text-blue-400 prose-strong:text-white
           prose-li:text-gray-300"
    v-html="rendered"
  />
</template>

<script setup lang="ts">
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps<{ content: string }>()
const rendered = computed(() =>
  DOMPurify.sanitize(marked.parse(props.content) as string),
)
</script>
```

- [ ] **Step 2 : Créer `frontend/pages/wiki/[slug].vue`**

```vue
<template>
  <div class="flex h-full overflow-hidden">
    <!-- Contenu principal -->
    <div class="flex-1 overflow-y-auto p-6 max-w-3xl mx-auto space-y-6">
      <div class="flex items-center gap-3">
        <NuxtLink to="/wiki" class="text-gray-400 hover:text-white transition-colors">
          <ArrowLeft class="w-4 h-4" />
        </NuxtLink>
        <h1 class="text-xl font-bold text-white">{{ currentPage?.title }}</h1>
      </div>

      <div v-if="loading" class="text-gray-400 text-sm">Chargement...</div>
      <div v-else-if="error" class="text-red-400 text-sm">{{ error }}</div>
      <MarkdownViewer v-else-if="currentPage" :content="currentPage.content" />
    </div>

    <!-- Panel frontmatter -->
    <div
      v-if="currentPage"
      class="w-64 shrink-0 border-l border-gray-800 p-4 space-y-4 overflow-y-auto bg-gray-900"
    >
      <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Métadonnées</h3>

      <div class="space-y-3 text-sm">
        <div>
          <p class="text-xs text-gray-500">Statut</p>
          <span
            :class="[
              'px-2 py-0.5 rounded text-xs font-medium',
              currentPage.status === 'validated'
                ? 'bg-green-900 text-green-300'
                : 'bg-yellow-900 text-yellow-300',
            ]"
          >
            {{ currentPage.status }}
          </span>
        </div>

        <div>
          <p class="text-xs text-gray-500">Confiance</p>
          <p class="text-gray-300">{{ currentPage.confidence }}</p>
        </div>

        <div>
          <p class="text-xs text-gray-500">Mis à jour</p>
          <p class="text-gray-300">{{ currentPage.updated_at || '—' }}</p>
        </div>

        <div v-if="currentPage.tags?.length">
          <p class="text-xs text-gray-500 mb-1">Tags</p>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="tag in currentPage.tags"
              :key="tag"
              class="px-2 py-0.5 bg-gray-800 rounded text-xs text-gray-400"
            >
              #{{ tag }}
            </span>
          </div>
        </div>

        <div v-if="currentPage.sources?.length">
          <p class="text-xs text-gray-500 mb-1">Sources</p>
          <ul class="space-y-1">
            <li
              v-for="src in currentPage.sources"
              :key="src"
              class="text-xs text-gray-400 truncate"
            >
              {{ src }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft } from 'lucide-vue-next'

const route = useRoute()
const { currentPage, loading, error, fetchPage } = useWiki()

onMounted(() => fetchPage(route.params.slug as string))
</script>
```

- [ ] **Step 3 : Tester manuellement**

Depuis `/wiki`, cliquer sur une page. Vérifier :
- Contenu Markdown rendu avec syntaxe colorée
- Panel droit avec status, confidence, tags, sources
- Bouton retour ← vers `/wiki`

- [ ] **Step 4 : Commit**

```bash
cd ..
git add frontend/
git commit -m "feat(frontend): page wiki détail — markdown + métadonnées"
```

---

## Task 7 : Page Ingest

**Files:**
- Create: `frontend/composables/useIngest.ts`
- Create: `frontend/components/ingest/IngestText.vue`
- Create: `frontend/components/ingest/IngestImage.vue`
- Create: `frontend/pages/ingest.vue`
- Create: `frontend/tests/composables/useIngest.test.ts`

---

- [ ] **Step 1 : Écrire le test de useIngest**

Créer `frontend/tests/composables/useIngest.test.ts` :

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const mockResult = { slug: 'imports--test', raw_path: '/raw/test.md', wiki_path: '/wiki/test.md', title: 'Test' }

vi.mock('~/composables/useApi', () => ({
  useApi: () => ({
    post: vi.fn().mockResolvedValue(mockResult),
    postForm: vi.fn().mockResolvedValue(mockResult),
    get: vi.fn(),
  }),
}))

vi.mock('#imports', () => ({
  useRuntimeConfig: () => ({ public: { apiBaseUrl: 'http://localhost:8088' } }),
  navigateTo: vi.fn(),
  ref: (v: unknown) => ({ value: v }),
}), { virtual: true })

describe('useIngest', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('ingestText appelle /api/ingest/text et retourne le résultat', async () => {
    const { useIngest } = await import('~/composables/useIngest')
    const { result, ingestText } = useIngest()
    await ingestText('Mon texte', 'Mon titre', ['tag1'])
    expect(result.value?.slug).toBe('imports--test')
  })

  it('ingestImage appelle /api/ingest/image avec FormData', async () => {
    const { useIngest } = await import('~/composables/useIngest')
    const { result, ingestImage } = useIngest()
    const file = new File(['data'], 'test.png', { type: 'image/png' })
    await ingestImage(file, 'Image test', ['img'])
    expect(result.value?.slug).toBe('imports--test')
  })
})
```

- [ ] **Step 2 : Lancer le test — vérifier qu'il échoue**

```bash
npm test -- tests/composables/useIngest.test.ts
```

Expected: FAIL — `Cannot find module '~/composables/useIngest'`

- [ ] **Step 3 : Créer `frontend/composables/useIngest.ts`**

```typescript
import type { IngestResult } from '~/types/api'

export function useIngest() {
  const result = ref<IngestResult | null>(null)
  const loading = ref(false)
  const error = ref('')
  const { post, postForm } = useApi()

  async function ingestText(text: string, title: string, tags: string[]) {
    loading.value = true
    error.value = ''
    result.value = null
    try {
      result.value = await post<IngestResult>('/api/ingest/text', { text, title, tags })
    } catch {
      error.value = "Erreur lors de l'ingestion."
    } finally {
      loading.value = false
    }
  }

  async function ingestImage(file: File, title: string, tags: string[]) {
    loading.value = true
    error.value = ''
    result.value = null
    try {
      const form = new FormData()
      form.append('file', file)
      if (title) form.append('title', title)
      form.append('tags', tags.join(','))
      result.value = await postForm<IngestResult>('/api/ingest/image', form)
    } catch {
      error.value = "Erreur lors de l'ingestion."
    } finally {
      loading.value = false
    }
  }

  function reset() {
    result.value = null
    error.value = ''
  }

  return { result, loading, error, ingestText, ingestImage, reset }
}
```

- [ ] **Step 4 : Relancer le test — vérifier qu'il passe**

```bash
npm test -- tests/composables/useIngest.test.ts
```

Expected: PASS — 2 tests passés.

- [ ] **Step 5 : Créer `frontend/components/ingest/IngestText.vue`**

```vue
<template>
  <form class="space-y-4" @submit.prevent="handleSubmit">
    <div class="space-y-1">
      <label class="block text-sm text-gray-300">Titre <span class="text-red-400">*</span></label>
      <input
        v-model="title"
        type="text"
        required
        placeholder="Titre de la page wiki"
        class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500"
      />
    </div>

    <div class="space-y-1">
      <label class="block text-sm text-gray-300">Tags <span class="text-gray-500">(séparés par virgule)</span></label>
      <input
        v-model="tagsInput"
        type="text"
        placeholder="livraison, logistique"
        class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500"
      />
    </div>

    <div class="space-y-1">
      <label class="block text-sm text-gray-300">Contenu <span class="text-red-400">*</span></label>
      <textarea
        v-model="text"
        required
        rows="8"
        placeholder="Colle le texte brut à structurer..."
        class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500 resize-y"
      />
    </div>

    <p v-if="error" class="text-red-400 text-sm">{{ error }}</p>

    <div v-if="result" class="p-3 bg-green-900/30 border border-green-700 rounded-lg space-y-1">
      <p class="text-green-400 text-sm font-medium">✓ Page créée</p>
      <p class="text-gray-400 text-xs">Slug : {{ result.slug }}</p>
      <NuxtLink :to="`/wiki/${result.slug}`" class="text-blue-400 text-xs hover:underline">
        Voir la page →
      </NuxtLink>
    </div>

    <button
      type="submit"
      :disabled="loading"
      class="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
    >
      {{ loading ? 'Ingestion en cours...' : 'Ingérer →' }}
    </button>
  </form>
</template>

<script setup lang="ts">
const { result, loading, error, ingestText, reset } = useIngest()

const title = ref('')
const tagsInput = ref('')
const text = ref('')

async function handleSubmit() {
  reset()
  const tags = tagsInput.value.split(',').map((t) => t.trim()).filter(Boolean)
  await ingestText(text.value, title.value, tags)
  if (result.value) {
    title.value = ''
    tagsInput.value = ''
    text.value = ''
  }
}
</script>
```

- [ ] **Step 6 : Créer `frontend/components/ingest/IngestImage.vue`**

```vue
<template>
  <form class="space-y-4" @submit.prevent="handleSubmit">
    <div class="space-y-1">
      <label class="block text-sm text-gray-300">Titre <span class="text-gray-500">(optionnel)</span></label>
      <input
        v-model="title"
        type="text"
        placeholder="Déduit du nom de fichier si vide"
        class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500"
      />
    </div>

    <div class="space-y-1">
      <label class="block text-sm text-gray-300">Tags <span class="text-gray-500">(séparés par virgule)</span></label>
      <input
        v-model="tagsInput"
        type="text"
        placeholder="architecture, schema"
        class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500"
      />
    </div>

    <!-- Zone drag & drop -->
    <div
      :class="[
        'border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer',
        isDragging ? 'border-blue-500 bg-blue-900/20' : 'border-gray-700 hover:border-gray-500',
      ]"
      @click="fileInput?.click()"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
      @drop.prevent="onDrop"
    >
      <ImageIcon class="w-8 h-8 text-gray-500 mx-auto mb-2" />
      <p v-if="selectedFile" class="text-white text-sm">{{ selectedFile.name }}</p>
      <p v-else class="text-gray-400 text-sm">
        Glisse une image ici ou clique pour sélectionner
      </p>
      <p class="text-gray-500 text-xs mt-1">.png .jpg .jpeg .webp .gif</p>
      <input
        ref="fileInput"
        type="file"
        accept=".png,.jpg,.jpeg,.webp,.gif"
        class="hidden"
        @change="onFileChange"
      />
    </div>

    <p v-if="error" class="text-red-400 text-sm">{{ error }}</p>

    <div v-if="result" class="p-3 bg-green-900/30 border border-green-700 rounded-lg space-y-1">
      <p class="text-green-400 text-sm font-medium">✓ Image ingérée</p>
      <p class="text-gray-400 text-xs">Slug : {{ result.slug }}</p>
      <NuxtLink :to="`/wiki/${result.slug}`" class="text-blue-400 text-xs hover:underline">
        Voir la page →
      </NuxtLink>
    </div>

    <button
      type="submit"
      :disabled="loading || !selectedFile"
      class="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
    >
      {{ loading ? 'Analyse en cours (llava)...' : 'Ingérer →' }}
    </button>
  </form>
</template>

<script setup lang="ts">
import { ImageIcon } from 'lucide-vue-next'

const { result, loading, error, ingestImage, reset } = useIngest()

const title = ref('')
const tagsInput = ref('')
const selectedFile = ref<File | null>(null)
const isDragging = ref(false)
const fileInput = ref<HTMLInputElement>()

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) selectedFile.value = file
}

async function handleSubmit() {
  if (!selectedFile.value) return
  reset()
  const tags = tagsInput.value.split(',').map((t) => t.trim()).filter(Boolean)
  await ingestImage(selectedFile.value, title.value, tags)
  if (result.value) {
    title.value = ''
    tagsInput.value = ''
    selectedFile.value = null
    if (fileInput.value) fileInput.value.value = ''
  }
}
</script>
```

- [ ] **Step 7 : Créer `frontend/pages/ingest.vue`**

```vue
<template>
  <div class="p-6 max-w-2xl mx-auto space-y-6">
    <h2 class="text-lg font-semibold text-white">Ingestion</h2>

    <!-- Onglets -->
    <div class="flex border-b border-gray-800">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :class="[
          'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
          activeTab === tab.id
            ? 'border-blue-500 text-blue-400'
            : 'border-transparent text-gray-400 hover:text-white',
        ]"
        @click="activeTab = tab.id"
      >
        <component :is="tab.icon" class="inline w-4 h-4 mr-1" />
        {{ tab.label }}
      </button>
    </div>

    <IngestText v-if="activeTab === 'text'" />
    <IngestImage v-else />
  </div>
</template>

<script setup lang="ts">
import { FileText, ImageIcon } from 'lucide-vue-next'

const activeTab = ref<'text' | 'image'>('text')
const tabs = [
  { id: 'text' as const, label: 'Texte', icon: FileText },
  { id: 'image' as const, label: 'Image', icon: ImageIcon },
]
</script>
```

- [ ] **Step 8 : Tester manuellement**

Ouvrir `/ingest`. Vérifier :
- Onglet Texte : remplir titre + texte → cliquer "Ingérer" → message de succès + lien vers la page
- Onglet Image : drag & drop une image → "Ingérer" → message de succès (plus long car llava)
- Lien "Voir la page →" ouvre `/wiki/imports--...`

- [ ] **Step 9 : Commit**

```bash
cd ..
git add frontend/
git commit -m "feat(frontend): page ingest — texte et image (drag & drop)"
```

---

## Task 8 : Docker + intégration docker-compose

**Files:**
- Create: `frontend/Dockerfile`
- Modify: `docker-compose.yml`
- Create: `frontend/.env.example`
- Create: `frontend/.gitignore`

---

- [ ] **Step 1 : Créer `frontend/.gitignore`**

```
node_modules/
.nuxt/
.output/
dist/
.env
```

- [ ] **Step 2 : Créer `frontend/.env.example`**

```
NUXT_PUBLIC_API_BASE_URL=http://localhost:8088
```

- [ ] **Step 3 : Créer `frontend/Dockerfile`**

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG NUXT_PUBLIC_API_BASE_URL=http://localhost:8088
ENV NUXT_PUBLIC_API_BASE_URL=$NUXT_PUBLIC_API_BASE_URL
RUN npm run generate

FROM nginx:alpine
COPY --from=builder /app/.output/public /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

- [ ] **Step 4 : Créer `frontend/nginx.conf`**

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

La directive `try_files` est indispensable pour que Vue Router fonctionne en SPA (toutes les routes vers `index.html`).

- [ ] **Step 5 : Vérifier que le build Docker fonctionne**

```bash
cd frontend
docker build -t openwikillm-frontend .
```

Expected: image buildée sans erreur. Taille finale < 50 MB.

- [ ] **Step 6 : Modifier `docker-compose.yml`**

Ajouter le service `frontend` après `openwikillm-api` :

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
      - ./logs:/app/logs
    env_file:
      - .env
    extra_hosts:
      - "host.docker.internal:host-gateway"

  frontend:
    build:
      context: ./frontend
      args:
        NUXT_PUBLIC_API_BASE_URL: http://localhost:8088
    container_name: openwikillm-frontend
    ports:
      - "3000:80"
    depends_on:
      - openwikillm-api
```

- [ ] **Step 7 : Tester l'intégration complète**

```bash
docker compose up -d --build
```

Ouvrir `http://localhost:3000`.
Expected :
- Redirect vers `/login`
- Connexion avec la clé API → redirect vers `/chat`
- Chat → réponse depuis l'API sur port 8088
- Wiki → liste des pages
- Ingest → ingestion texte fonctionnelle

- [ ] **Step 8 : Lancer tous les tests**

```bash
cd frontend
npm test
```

Expected: tous les tests passent (auth, useChat, useWiki, useIngest).

- [ ] **Step 9 : Commit final**

```bash
cd ..
git add frontend/ docker-compose.yml
git commit -m "feat(frontend): Dockerfile, nginx, docker-compose — frontend complet"
```
