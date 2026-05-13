<template>
  <form class="space-y-4" @submit.prevent="handleSubmit">
    <div class="space-y-1">
      <label class="block text-sm text-gray-300">Titre <span class="text-red-400">*</span></label>
      <input
        v-model="title"
        type="text"
        required
        placeholder="Titre de la page wiki"
        class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500"
      />
    </div>

    <div class="space-y-1">
      <label class="block text-sm text-gray-300">Tags <span class="text-gray-500">(séparés par virgule)</span></label>
      <input
        v-model="tagsInput"
        type="text"
        placeholder="livraison, logistique"
        class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500"
      />
    </div>

    <div class="space-y-1">
      <label class="block text-sm text-gray-300">Contenu <span class="text-red-400">*</span></label>
      <textarea
        v-model="text"
        required
        rows="8"
        placeholder="Colle le texte brut à structurer..."
        class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500 resize-y"
      />
    </div>

    <p v-if="error" class="text-red-400 text-sm">{{ error }}</p>

    <div v-if="result" class="p-3 bg-green-900/30 border border-green-700 rounded-lg space-y-1">
      <p class="text-green-400 text-sm font-medium">✓ {{ result.slug }} créé</p>
      <p v-for="s in result.pages_updated" :key="s" class="text-blue-300 text-xs">↻ {{ s }} mis à jour</p>
      <NuxtLink :to="`/wiki/${result.slug}`" class="text-blue-400 text-xs hover:underline">
        Voir la page →
      </NuxtLink>
    </div>

    <button
      type="submit"
      :disabled="loading"
      class="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
    >
      {{ loadingLabel }}
    </button>
  </form>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'

const { result, loading, error, ingestText, reset } = useIngest()

const title = ref('')
const tagsInput = ref('')
const text = ref('')
const phase = ref<'analyse' | 'compilation'>('analyse')
let phaseTimer: ReturnType<typeof setTimeout> | null = null

const loadingLabel = computed(() => {
  if (!loading.value) return 'Ingérer →'
  return phase.value === 'analyse' ? 'Analyse des pages liées...' : 'Compilation du wiki...'
})

onUnmounted(() => {
  if (phaseTimer) clearTimeout(phaseTimer)
})

async function handleSubmit() {
  reset()
  phase.value = 'analyse'
  phaseTimer = setTimeout(() => { phase.value = 'compilation' }, 8000)
  const tags = tagsInput.value.split(',').map((t) => t.trim()).filter(Boolean)
  await ingestText(text.value, title.value, tags)
  if (phaseTimer) { clearTimeout(phaseTimer); phaseTimer = null }
  if (result.value) {
    title.value = ''
    tagsInput.value = ''
    text.value = ''
  }
}
</script>
