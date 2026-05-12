<template>
  <header class="h-14 flex items-center justify-between px-4 border-b border-gray-800 bg-gray-950 shrink-0">
    <h2 class="text-sm font-medium text-gray-300">{{ pageTitle }}</h2>
    <div class="flex items-center gap-2">
      <span class="w-2 h-2 rounded-full bg-green-500"></span>
      <span class="text-xs text-gray-400">Connecté</span>
      <button
        class="ml-4 text-xs text-gray-500 hover:text-white transition-colors"
        @click="logout"
      >
        Déconnexion
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
const route = useRoute()
const authStore = useAuthStore()

const pageTitles: Record<string, string> = {
  '/chat': 'Chat',
  '/wiki': 'Wiki',
  '/ingest': 'Ingest',
}

const pageTitle = computed(() => pageTitles[route.path] || 'OpenWikiLLM')

async function logout() {
  authStore.logout()
  await navigateTo('/login')
}
</script>
