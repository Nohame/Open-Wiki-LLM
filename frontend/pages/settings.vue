<template>
  <div class="max-w-2xl mx-auto py-10 px-6 space-y-8">
    <div>
      <h1 class="text-xl font-bold text-white">
        {{ isSetupMode ? 'Configuration initiale' : 'Paramètres' }}
      </h1>
      <p v-if="isSetupMode" class="text-sm text-gray-400 mt-1">
        Configurez votre provider LLM pour commencer à utiliser OpenWikiLLM.
      </p>
    </div>

    <div v-if="settings" class="space-y-8">
      <section class="p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-4">
        <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wider">LLM</h2>
        <SettingsLLMSettings v-model="settings.llm" />
      </section>

      <section class="p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-4">
        <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wider">Ingestion</h2>
        <SettingsIngestSettings v-model="settings.ingest" />
      </section>

      <section class="p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-4">
        <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wider">Connecteurs</h2>
        <SettingsConnectorsSettings
          v-model="settings.connectors"
          :connection-failed="connectionFailed"
          @connect="handleConnect"
          @disconnect="handleDisconnect"
        />
      </section>

      <section class="p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-4">
        <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wider">Git</h2>
        <SettingsGitSettings v-model="settings.git" />
      </section>

      <div class="flex items-center gap-4">
        <button
          :disabled="saving"
          class="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
          @click="handleSave"
        >
          {{ saving ? 'Enregistrement…' : 'Enregistrer' }}
        </button>
        <p v-if="saved" class="text-green-400 text-sm">Paramètres enregistrés.</p>
        <p v-if="saveError" class="text-red-400 text-sm">{{ saveError }}</p>
      </div>
    </div>

    <div v-else class="text-gray-400 text-sm">Chargement…</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const { settings, saving, saveError, fetchSettings, saveSettings, isConfigured } = useSettings()
const { getAuthUrl, disconnect } = useGoogleDrive()
const router = useRouter()
const route = useRoute()
const saved = ref(false)
const connectionFailed = ref(false)
const isSetupMode = computed(() => !isConfigured())

onMounted(async () => {
  await fetchSettings()
  if (route.query.connected === 'google-drive') {
    await fetchSettings()
    saved.value = true
    await router.replace('/settings')
  }
  if (route.query.error === 'google-drive-denied') {
    connectionFailed.value = true
    await router.replace('/settings')
  }
})

async function handleSave() {
  if (!settings.value) return
  saved.value = false
  const wasSetupMode = isSetupMode.value
  try {
    await saveSettings(settings.value)
    const llmReady = useState('llm-ready', () => false)
    llmReady.value = true
    saved.value = true
    if (wasSetupMode) {
      await router.push('/chat')
    }
  } catch {
    // saveError is handled in useSettings
  }
}

async function handleConnect() {
  if (!settings.value) return
  connectionFailed.value = false
  try {
    await saveSettings(settings.value)
    const url = await getAuthUrl()
    window.location.href = url
  } catch {
    connectionFailed.value = true
  }
}

async function handleDisconnect() {
  try {
    await disconnect()
    await fetchSettings()
  } catch {
    // ignore
  }
}
</script>
