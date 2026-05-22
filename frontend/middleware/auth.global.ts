import { useAuthStore } from '~/stores/auth'
import type { AppSettings } from '~/types/api'

function _isLLMConfigured(s: AppSettings): boolean {
  const { provider } = s.llm
  if (provider === 'ollama') return !!s.llm.ollama.base_url
  if (provider === 'custom') return !!s.llm.custom.base_url
  const cfg = s.llm[provider as 'openai' | 'gemini' | 'anthropic']
  return !!cfg.api_key && cfg.api_key !== ''
}

export default defineNuxtRouteMiddleware(async (to) => {
  if (to.path === '/login' || to.path === '/settings') return

  const authStore = useAuthStore()
  authStore.loadFromStorage()

  if (!authStore.isAuthenticated) return navigateTo('/login')

  const llmReady = useState('llm-ready', () => false)
  if (llmReady.value) return

  try {
    const config = useRuntimeConfig()
    const baseUrl = config.public.apiBaseUrl as string
    const headers: Record<string, string> = {}
    if (authStore.apiKey) headers['X-API-Key'] = authStore.apiKey

    const s = await $fetch<AppSettings>(`${baseUrl}/api/settings`, { headers })
    llmReady.value = _isLLMConfigured(s)
  } catch {
    llmReady.value = true
  }

  if (!llmReady.value) return navigateTo('/settings')
})
