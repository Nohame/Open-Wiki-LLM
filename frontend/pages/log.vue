<template>
  <div class="max-w-3xl mx-auto py-8 px-4">
    <h1 class="text-xl font-semibold text-white mb-6">Journal des ingestions</h1>
    <div v-if="loading" class="text-gray-400 text-sm">Chargement...</div>
    <div v-else-if="error" class="text-red-400 text-sm">{{ error }}</div>
    <div v-else-if="!content" class="text-gray-500 text-sm italic">
      Aucune ingestion enregistrée.
    </div>
    <MarkdownViewer v-else :content="content" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import MarkdownViewer from '~/components/wiki/MarkdownViewer.vue'
import { useApi } from '~/composables/useApi'
import type { LogResponse } from '~/types/api'

const { get } = useApi()
const content = ref('')
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    const data = await get<LogResponse>('/api/wiki/log')
    content.value = data.content
  } catch {
    error.value = 'Impossible de charger le journal.'
  } finally {
    loading.value = false
  }
})
</script>
