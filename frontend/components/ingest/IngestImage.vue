<template>
  <form class="space-y-4" @submit.prevent="handleSubmit">
    <div class="space-y-1">
      <label class="block text-sm text-gray-300">Titre <span class="text-gray-500">(optionnel)</span></label>
      <input
        v-model="title"
        type="text"
        placeholder="Déduit du nom de fichier si vide"
        class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500"
      />
    </div>

    <div class="space-y-1">
      <label class="block text-sm text-gray-300">Tags <span class="text-gray-500">(séparés par virgule)</span></label>
      <input
        v-model="tagsInput"
        type="text"
        placeholder="architecture, schema"
        class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500"
      />
    </div>

    <!-- Zone drag & drop -->
    <div
      :class="[
        'border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer',
        isDragging ? 'border-blue-500 bg-blue-900/20' : 'border-gray-700 hover:border-gray-500',
      ]"
      @click="fileInput?.click()"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
      @drop.prevent="onDrop"
    >
      <ImageIcon class="w-8 h-8 text-gray-500 mx-auto mb-2" />
      <p v-if="selectedFile" class="text-white text-sm">{{ selectedFile.name }}</p>
      <p v-else class="text-gray-400 text-sm">
        Glisse une image ici ou clique pour sélectionner
      </p>
      <p class="text-gray-500 text-xs mt-1">.png .jpg .jpeg .webp .gif</p>
      <input
        ref="fileInput"
        type="file"
        accept=".png,.jpg,.jpeg,.webp,.gif"
        class="hidden"
        @change="onFileChange"
      />
    </div>

    <p v-if="error" class="text-red-400 text-sm">{{ error }}</p>

    <div v-if="result" class="p-3 bg-green-900/30 border border-green-700 rounded-lg space-y-1">
      <p class="text-green-400 text-sm font-medium">✓ Image ingérée</p>
      <p class="text-gray-400 text-xs">Slug : {{ result.slug }}</p>
      <NuxtLink :to="`/wiki/${result.slug}`" class="text-blue-400 text-xs hover:underline">
        Voir la page →
      </NuxtLink>
    </div>

    <button
      type="submit"
      :disabled="loading || !selectedFile"
      class="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
    >
      {{ loading ? 'Analyse en cours (llava)...' : 'Ingérer →' }}
    </button>
  </form>
</template>

<script setup lang="ts">
import { ImageIcon } from 'lucide-vue-next'

const { result, loading, error, ingestImage, reset } = useIngest()

const title = ref('')
const tagsInput = ref('')
const selectedFile = ref<File | null>(null)
const isDragging = ref(false)
const fileInput = ref<HTMLInputElement>()

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) selectedFile.value = file
}

async function handleSubmit() {
  if (!selectedFile.value) return
  reset()
  const tags = tagsInput.value.split(',').map((t) => t.trim()).filter(Boolean)
  await ingestImage(selectedFile.value, title.value, tags)
  if (result.value) {
    title.value = ''
    tagsInput.value = ''
    selectedFile.value = null
    if (fileInput.value) fileInput.value.value = ''
  }
}
</script>
