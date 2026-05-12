import { ref } from 'vue'
import { useApi } from '~/composables/useApi'
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
