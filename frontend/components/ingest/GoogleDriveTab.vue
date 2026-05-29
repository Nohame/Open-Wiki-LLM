<template>
  <div class="space-y-4">
    <!-- Not connected -->
    <div v-if="!isConnected" class="text-center py-12 space-y-3">
      <p class="text-gray-400 text-sm">Google Drive n'est pas connecté.</p>
      <NuxtLink to="/settings" class="text-blue-400 hover:text-blue-300 text-sm underline">
        Configurer dans les Paramètres
      </NuxtLink>
    </div>

    <!-- Connected -->
    <div v-else class="space-y-4">
      <!-- Breadcrumb -->
      <nav class="flex items-center gap-1 text-sm text-gray-400 flex-wrap">
        <button
          class="hover:text-white transition-colors"
          @click="navigateTo('root', 0)"
        >
          Mon Drive
        </button>
        <template v-for="(crumb, i) in breadcrumb" :key="crumb.id">
          <span class="text-gray-600">/</span>
          <button
            class="hover:text-white transition-colors"
            @click="navigateTo(crumb.id, i + 1)"
          >
            {{ crumb.name }}
          </button>
        </template>
      </nav>

      <!-- Loading -->
      <div v-if="loading" class="text-gray-400 text-sm text-center py-8">Chargement…</div>

      <!-- Error -->
      <p v-else-if="listError" class="text-red-400 text-sm">{{ listError }}</p>

      <!-- File list -->
      <ul v-else class="divide-y divide-gray-800">
        <li
          v-for="file in files"
          :key="file.id"
          class="flex items-center justify-between py-3 gap-4"
        >
          <div class="flex items-center gap-3 min-w-0">
            <component
              :is="file.isFolder ? Folder : FileText"
              class="w-4 h-4 shrink-0 text-gray-400"
            />
            <button
              v-if="file.isFolder"
              class="text-sm text-white hover:text-blue-400 transition-colors truncate text-left"
              @click="openFolder(file)"
            >
              {{ file.name }}
            </button>
            <span v-else class="text-sm text-white truncate">{{ file.name }}</span>
          </div>

          <div v-if="!file.isFolder" class="flex items-center gap-3 shrink-0">
            <div v-if="ingestResults[file.id]" class="text-xs text-green-400">
              {{ ingestResults[file.id].slug }} ingéré
            </div>
            <div v-if="ingestErrors[file.id]" class="text-xs text-red-400">
              {{ ingestErrors[file.id] }}
            </div>
            <button
              :disabled="!!ingestingIds[file.id]"
              class="px-3 py-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs rounded-lg transition-colors shrink-0"
              @click="handleIngest(file)"
            >
              {{ ingestingIds[file.id] ? 'Ingestion…' : 'Ingérer' }}
            </button>
          </div>
        </li>

        <li v-if="files.length === 0" class="py-8 text-center text-gray-500 text-sm">
          Dossier vide
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { Folder, FileText } from 'lucide-vue-next'
import type { GoogleDriveFile, IngestResult } from '~/types/api'

const { fetchSettings, settings } = useSettings()
const { listFiles, ingestFile } = useGoogleDrive()

const isConnected = computed(
  () => settings.value?.connectors?.google_drive?.access_token === '****'
)

interface Crumb { id: string; name: string }

const breadcrumb = ref<Crumb[]>([])
const files = ref<GoogleDriveFile[]>([])
const loading = ref(false)
const listError = ref<string | null>(null)

const ingestingIds = reactive<Record<string, boolean>>({})
const ingestResults = reactive<Record<string, IngestResult>>({})
const ingestErrors = reactive<Record<string, string>>({})

onMounted(async () => {
  await fetchSettings()
  if (isConnected.value) {
    await loadFiles('root')
  }
})

async function loadFiles(folderId: string) {
  loading.value = true
  listError.value = null
  try {
    const resp = await listFiles(folderId)
    files.value = resp.files
  } catch (e: unknown) {
    listError.value = e instanceof Error ? e.message : 'Erreur lors du chargement'
  } finally {
    loading.value = false
  }
}

async function openFolder(file: GoogleDriveFile) {
  breadcrumb.value.push({ id: file.id, name: file.name })
  await loadFiles(file.id)
}

async function navigateTo(folderId: string, crumbIndex: number) {
  if (folderId === 'root') {
    breadcrumb.value = []
  } else {
    breadcrumb.value = breadcrumb.value.slice(0, crumbIndex)
  }
  await loadFiles(folderId)
}

async function handleIngest(file: GoogleDriveFile) {
  ingestingIds[file.id] = true
  delete ingestErrors[file.id]
  delete ingestResults[file.id]
  try {
    const result = await ingestFile(file.id, file.name, file.mimeType, file.name)
    ingestResults[file.id] = result
  } catch (e: unknown) {
    ingestErrors[file.id] = e instanceof Error ? e.message : 'Erreur lors de l\'ingestion'
  } finally {
    ingestingIds[file.id] = false
  }
}
</script>
