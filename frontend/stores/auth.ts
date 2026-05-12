import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const apiKey = ref('')
  const isAuthenticated = computed(() => !!apiKey.value)

  function setApiKey(key: string) {
    apiKey.value = key
    if (typeof window !== 'undefined') {
      localStorage.setItem('openwikillm_api_key', key)
    }
  }

  function loadFromStorage() {
    if (typeof window !== 'undefined') {
      apiKey.value = localStorage.getItem('openwikillm_api_key') || ''
    }
  }

  function logout() {
    apiKey.value = ''
    if (typeof window !== 'undefined') {
      localStorage.removeItem('openwikillm_api_key')
    }
  }

  return { apiKey, isAuthenticated, setApiKey, loadFromStorage, logout }
})
