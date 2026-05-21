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

const mockDelete = vi.fn().mockResolvedValue(undefined)

vi.mock('~/composables/useApi', () => ({
  useApi: () => ({
    get: vi.fn().mockResolvedValue([mockPage]),
    post: vi.fn().mockResolvedValue([
      { slug: 'imports--livraison', title: 'Livraison 24h', snippet: 'délai 24h', score: 1.5 },
    ]),
    postForm: vi.fn(),
    patch: vi.fn().mockResolvedValue({}),
    del: mockDelete,
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

  it('deletePage retire la page de la liste', async () => {
    const { useWiki } = await import('~/composables/useWiki')
    const { pages, fetchPages, deletePage } = useWiki()
    await fetchPages()
    expect(pages.value).toHaveLength(1)
    await deletePage('imports--livraison')
    expect(mockDelete).toHaveBeenCalledWith('/api/pages/imports--livraison')
    expect(pages.value).toHaveLength(0)
  })
})
