import { ref } from 'vue'
import { useApi } from '~/composables/useApi'
import type { AppSettings } from '~/types/api'

export function useSettings() {
  const { get, put } = useApi()
  const settings = ref<AppSettings | null>(null)
  const saving = ref(false)
  const saveError = ref<string | null>(null)

  async function fetchSettings(): Promise<void> {
    settings.value = await get<AppSettings>('/api/settings')
  }

  async function saveSettings(s: AppSettings): Promise<void> {
    saving.value = true
    saveError.value = null
    try {
      settings.value = await put<AppSettings>('/api/settings', s)
    } catch (e: unknown) {
      saveError.value = e instanceof Error ? e.message : 'Erreur lors de la sauvegarde'
      throw e
    } finally {
      saving.value = false
    }
  }

  function isConfigured(): boolean {
    if (!settings.value) return false
    const { provider } = settings.value.llm
    if (provider === 'ollama') return !!settings.value.llm.ollama.base_url
    if (provider === 'custom') return !!settings.value.llm.custom.base_url
    const cfg = settings.value.llm[provider as 'openai' | 'gemini' | 'anthropic']
    return !!cfg.api_key && cfg.api_key !== ''
  }

  return { settings, saving, saveError, fetchSettings, saveSettings, isConfigured }
}
