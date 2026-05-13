<template>
  <div class="p-6 max-w-2xl mx-auto space-y-6">
    <h2 class="text-lg font-semibold text-white">Ingestion</h2>

    <div class="flex border-b border-gray-800">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :class="[
          'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
          activeTab === tab.id
            ? 'border-blue-500 text-blue-400'
            : 'border-transparent text-gray-400 hover:text-white',
        ]"
        @click="activeTab = tab.id"
      >
        <component :is="tab.icon" class="inline w-4 h-4 mr-1" />
        {{ tab.label }}
      </button>
    </div>

    <IngestText v-if="activeTab === 'text'" />
    <IngestImage v-else-if="activeTab === 'image'" />
    <IngestFile v-else-if="activeTab === 'file'" />
  </div>
</template>

<script setup lang="ts">
import { FileText, ImageIcon, FolderOpen } from 'lucide-vue-next'
import IngestFile from '~/components/ingest/IngestFile.vue'

const activeTab = ref<'text' | 'image' | 'file'>('text')
const tabs = [
  { id: 'text' as const, label: 'Texte', icon: FileText },
  { id: 'image' as const, label: 'Image', icon: ImageIcon },
  { id: 'file' as const, label: 'Fichiers', icon: FolderOpen },
]
</script>
