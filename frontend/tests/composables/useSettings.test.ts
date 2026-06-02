import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const mockGet = vi.fn()
const mockPut = vi.fn()
vi.mock('~/composables/useApi', () => ({
  useApi: () => ({ get: mockGet, put: mockPut }),
}))
vi.mock('~/stores/auth', () => ({
  useAuthStore: () => ({ apiKey: '', isAuthenticated: true, loadFromStorage: vi.fn(), logout: vi.fn() }),
}))
vi.mock('#imports', () => ({
  useRuntimeConfig: () => ({ public: { apiBaseUrl: 'http://localhost:8088' } }),
  navigateTo: vi.fn(),
  ref: (v: unknown) => ({ value: v }),
  useState: (_key: string, init: () => unknown) => {
    const { ref } = require('vue')
    return ref(init())
  },
}), { virtual: true })

import type { AppSettings } from '~/types/api'

const defaultSettings: AppSettings = {
  llm: {
    provider: 'ollama',
    ollama: { base_url: 'http://localhost:11434', model: 'mistral', vision_model: 'llava' },
    openai: { api_key: '', model: 'gpt-4o', vision_model: 'gpt-4o' },
    gemini: { api_key: '', model: 'gemini-1.5-pro', vision_model: 'gemini-1.5-pro' },
    anthropic: { api_key: '', model: 'claude-opus-4-7', vision_model: 'claude-opus-4-7' },
    custom: { base_url: '', api_key: '', model: '', vision_model: '' },
  },
  ingest: { max_text_chars: 30000 },
  connectors: {
    google_drive: {
      client_id: '',
      client_secret: '',
      access_token: '',
      refresh_token: '',
      token_expiry: '',
    },
  },
  git: { enabled: false, auto_push: false, remote_url: '', branch: 'main' },
}

describe('useSettings', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockGet.mockReset()
    mockPut.mockReset()
  })

  it('fetchSettings populates settings', async () => {
    mockGet.mockResolvedValue(defaultSettings)
    const { useSettings } = await import('~/composables/useSettings')
    const { settings, fetchSettings } = useSettings()
    await fetchSettings()
    expect(settings.value).toEqual(defaultSettings)
  })

  it('isConfigured returns true for ollama with base_url', async () => {
    mockGet.mockResolvedValue(defaultSettings)
    const { useSettings } = await import('~/composables/useSettings')
    const { fetchSettings, isConfigured } = useSettings()
    await fetchSettings()
    expect(isConfigured()).toBe(true)
  })

  it('isConfigured returns false for openai without api_key', async () => {
    const s = { ...defaultSettings, llm: { ...defaultSettings.llm, provider: 'openai' as const } }
    mockGet.mockResolvedValue(s)
    const { useSettings } = await import('~/composables/useSettings')
    const { fetchSettings, isConfigured } = useSettings()
    await fetchSettings()
    expect(isConfigured()).toBe(false)
  })

  it('saveSettings calls PUT and updates settings', async () => {
    const updated = { ...defaultSettings, ingest: { max_text_chars: 20000 } }
    mockPut.mockResolvedValue(updated)
    const { useSettings } = await import('~/composables/useSettings')
    const { settings, saveSettings } = useSettings()
    await saveSettings(updated)
    expect(mockPut).toHaveBeenCalledWith('/api/settings', updated)
    expect(settings.value?.ingest.max_text_chars).toBe(20000)
  })
})
