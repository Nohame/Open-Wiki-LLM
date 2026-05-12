import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '~/stores/auth'

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('démarre non authentifié', () => {
    const store = useAuthStore()
    expect(store.isAuthenticated).toBe(false)
    expect(store.apiKey).toBe('')
  })

  it('setApiKey met à jour la clé et localStorage', () => {
    const store = useAuthStore()
    store.setApiKey('test-key-123')
    expect(store.apiKey).toBe('test-key-123')
    expect(store.isAuthenticated).toBe(true)
    expect(localStorage.getItem('openwikillm_api_key')).toBe('test-key-123')
  })

  it('loadFromStorage charge depuis localStorage', () => {
    localStorage.setItem('openwikillm_api_key', 'stored-key')
    const store = useAuthStore()
    store.loadFromStorage()
    expect(store.apiKey).toBe('stored-key')
    expect(store.isAuthenticated).toBe(true)
  })

  it('logout efface la clé et localStorage', () => {
    const store = useAuthStore()
    store.setApiKey('some-key')
    store.logout()
    expect(store.apiKey).toBe('')
    expect(store.isAuthenticated).toBe(false)
    expect(localStorage.getItem('openwikillm_api_key')).toBeNull()
  })
})
