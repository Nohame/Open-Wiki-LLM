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
        <WikiPageCard v-for="page in displayedPages" :key="page.slug" :page="page" @delete="deletePage" />
      </div>
      <p v-else class="text-gray-400 text-sm">Aucun résultat.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDebounceFn } from '@vueuse/core'
import type { WikiPageSummary } from '~/types/api'

const { pages, searchResults, loading, error, fetchPages, search, deletePage } = useWiki()

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
  debouncedSearch(q)
})

onMounted(() => fetchPages())
</script>
