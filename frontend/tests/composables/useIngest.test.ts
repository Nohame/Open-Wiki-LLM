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
