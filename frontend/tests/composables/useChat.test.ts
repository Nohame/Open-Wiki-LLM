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
