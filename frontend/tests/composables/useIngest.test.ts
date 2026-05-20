import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const mockResult = { slug: 'imports--test', raw_path: '/raw/test.md', wiki_path: '/wiki/test.md', title: 'Test' }

const postFormSpy = vi.fn().mockResolvedValue(mockResult)

vi.mock('~/composables/useApi', () => ({
  useApi: () => ({
    post: vi.fn().mockResolvedValue(mockResult),
    postForm: postFormSpy,
    get: vi.fn(),
    patch: vi.fn().mockResolvedValue({}),
  }),
}))

vi.mock('#imports', () => ({
  useRuntimeConfig: () => ({ public: { apiBaseUrl: 'http://localhost:8088' } }),
  navigateTo: vi.fn(),
  ref: (v: unknown) => ({ value: v }),
}), { virtual: true })

describe('useIngest', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    postFormSpy.mockClear()
  })

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

  it('ingestFile appelle /api/ingest/file et déduit le title depuis file.name', async () => {
    const { useIngest } = await import('~/composables/useIngest')
    const { ingestFile } = useIngest()
    const file = new File(['contenu'], 'rapport-annuel.pdf', { type: 'application/pdf' })
    const result = await ingestFile(file, ['tag1'])
    expect(postFormSpy).toHaveBeenCalledWith('/api/ingest/file', expect.any(FormData))
    const form = postFormSpy.mock.calls[0][1] as FormData
    expect(form.get('title')).toBe('rapport-annuel')
    expect(result.slug).toBe('imports--test')
  })
})
