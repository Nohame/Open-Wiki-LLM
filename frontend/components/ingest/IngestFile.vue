<template>
  <div class="space-y-4">
    <div
      class="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors"
      :class="isDragging ? 'border-blue-500 bg-blue-950/20' : 'border-gray-700 hover:border-gray-600'"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="onDragLeave"
      @drop.prevent="onDrop"
      @click="fileInput?.click()"
    >
      <FolderOpen class="mx-auto w-8 h-8 text-gray-500 mb-2" />
      <p class="text-sm text-gray-400">
        Glissez des fichiers ici ou
        <span class="text-blue-400">cliquez pour sélectionner</span>
      </p>
      <p class="text-xs text-gray-600 mt-1">.md .txt .pdf .docx — max 10 Mo</p>
      <input
        ref="fileInput"
        type="file"
        multiple
        accept=".md,.txt,.pdf,.docx"
        class="hidden"
        @change="onFileInput"
      />
    </div>

    <div>
      <label class="block text-sm text-gray-400 mb-1">Tags (appliqués à tous les fichiers)</label>
      <input
        v-model="tagsInput"
        type="text"
        placeholder="tag1, tag2"
        class="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500"
        :disabled="isProcessing"
      />
    </div>

    <ul v-if="entries.length" class="space-y-2">
      <li
        v-for="entry in entries"
        :key="entry.file.name"
        class="flex items-center justify-between text-sm rounded px-3 py-2 bg-gray-900"
      >
        <span class="text-gray-300 truncate max-w-xs">{{ entry.file.name }}</span>
        <span class="ml-4 shrink-0">
          <span v-if="entry.status === 'pending'" class="text-gray-500">en attente</span>
          <span v-else-if="entry.status === 'processing'" class="text-blue-400 animate-pulse">en cours...</span>
          <span v-else-if="entry.status === 'done'" class="text-green-400">
            ✓
            <NuxtLink :to="`/wiki/${entry.slug}`" class="ml-1 underline hover:text-white">
              {{ entry.slug }}
            </NuxtLink>
          </span>
          <span v-else class="text-red-400">✗ {{ entry.error }}</span>
        </span>
      </li>
    </ul>

    <div v-if="rejectedMessage" class="text-sm text-yellow-400 bg-yellow-950/30 rounded px-3 py-2">
      {{ rejectedMessage }}
    </div>

    <div class="flex gap-2">
      <button
        :disabled="!entries.length || isProcessing"
        class="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-white font-medium"
        @click="ingestAll"
      >
        Tout ingérer →
      </button>
      <button
        :disabled="isProcessing"
        class="px-4 py-2 text-sm bg-gray-800 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-white"
        @click="clearAll"
      >
        Effacer
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { FolderOpen } from 'lucide-vue-next'
import { useIngest } from '~/composables/useIngest'

interface FileEntry {
  file: File
  status: 'pending' | 'processing' | 'done' | 'error'
  slug?: string
  error?: string
}

const ALLOWED_EXTS = new Set(['.md', '.txt', '.pdf', '.docx'])
const MAX_SIZE = 10 * 1024 * 1024

const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const tagsInput = ref('')
const entries = ref<FileEntry[]>([])
const rejectedMessage = ref('')

const isProcessing = computed(() => entries.value.some((e) => e.status === 'processing'))

const { ingestFile } = useIngest()

function addFiles(files: FileList | File[]) {
  const rejected: string[] = []
  for (const file of Array.from(files)) {
    const ext = '.' + (file.name.split('.').pop() ?? '').toLowerCase()
    if (!ALLOWED_EXTS.has(ext)) {
      rejected.push(`${file.name} (format non supporté)`)
      continue
    }
    if (file.size > MAX_SIZE) {
      rejected.push(`${file.name} (> 10 Mo)`)
      continue
    }
    if (!entries.value.some((e) => e.file.name === file.name && e.status !== 'error')) {
      entries.value.push({ file, status: 'pending' })
    }
  }
  rejectedMessage.value = rejected.length ? `Fichiers rejetés : ${rejected.join(', ')}` : ''
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  if (e.dataTransfer?.files) addFiles(e.dataTransfer.files)
}

function onDragLeave(e: DragEvent) {
  if (!(e.currentTarget as Element).contains(e.relatedTarget as Node | null)) {
    isDragging.value = false
  }
}

function onFileInput(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) addFiles(input.files)
  input.value = ''
}

async function ingestAll() {
  if (isProcessing.value) return
  rejectedMessage.value = ''
  const tags = tagsInput.value
    .split(',')
    .map((t) => t.trim())
    .filter(Boolean)
  for (const entry of entries.value) {
    if (entry.status !== 'pending') continue
    entry.status = 'processing'
    try {
      const result = await ingestFile(entry.file, tags)
      entry.status = 'done'
      entry.slug = result.slug
    } catch (err: unknown) {
      entry.status = 'error'
      entry.error = err instanceof Error ? err.message : 'Erreur inconnue'
    }
  }
}

function clearAll() {
  if (!isProcessing.value) {
    entries.value = []
    rejectedMessage.value = ''
  }
}
</script>
