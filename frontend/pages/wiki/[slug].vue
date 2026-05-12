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
                : currentPage.status === 'draft'
                  ? 'bg-yellow-900 text-yellow-300'
                  : 'bg-gray-700 text-gray-400',
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
