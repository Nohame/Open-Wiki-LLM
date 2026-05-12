<template>
  <div class="min-h-screen bg-gray-950 flex items-center justify-center">
    <div class="w-full max-w-sm space-y-6 p-8">
      <div class="text-center space-y-2">
        <div class="w-10 h-10 rounded-full bg-blue-600 mx-auto flex items-center justify-center">
          <BookOpen class="w-5 h-5 text-white" />
        </div>
        <h1 class="text-2xl font-bold text-white">OpenWikiLLM</h1>
        <p class="text-gray-400 text-sm">Connexion à l'API</p>
      </div>

      <form class="space-y-4" @submit.prevent="handleLogin">
        <div class="space-y-1">
          <label class="block text-sm text-gray-300">Clé API</label>
          <input
            v-model="apiKey"
            type="password"
            placeholder="Laisser vide si pas d'auth"
            class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
        </div>

        <p v-if="error" class="text-red-400 text-sm">{{ error }}</p>

        <button
          type="submit"
          :disabled="loading"
          class="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg font-medium transition-colors"
        >
          {{ loading ? 'Connexion...' : 'Connexion' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { BookOpen } from 'lucide-vue-next'

definePageMeta({ layout: false })

const config = useRuntimeConfig()
const authStore = useAuthStore()

const apiKey = ref('')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    const h: Record<string, string> = {}
    if (apiKey.value) h['X-API-Key'] = apiKey.value
    await $fetch(`${config.public.apiBaseUrl}/health`, { headers: h })
    authStore.setApiKey(apiKey.value)
    await navigateTo('/chat')
  } catch {
    error.value = 'Clé invalide ou API inaccessible.'
  } finally {
    loading.value = false
  }
}
</script>
