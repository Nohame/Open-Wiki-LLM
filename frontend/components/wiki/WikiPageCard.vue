<template>
  <div class="relative group">
    <NuxtLink
      :to="`/wiki/${page.slug}`"
      class="block p-4 bg-gray-900 border border-gray-800 rounded-xl hover:border-gray-600 hover:bg-gray-800 transition-colors space-y-2"
    >
      <div class="flex items-start justify-between gap-2">
        <h3 class="font-medium text-white text-sm leading-snug pr-6">{{ page.title }}</h3>
        <span
          :class="[
            'shrink-0 px-2 py-0.5 rounded text-xs font-medium',
            page.status === 'validated'
              ? 'bg-green-900 text-green-300'
              : page.status === 'draft'
                ? 'bg-yellow-900 text-yellow-300'
                : 'bg-gray-700 text-gray-400',
          ]"
        >
          {{ page.status || '—' }}
        </span>
      </div>

      <div v-if="page.tags?.length" class="flex flex-wrap gap-1">
        <span
          v-for="tag in page.tags.slice(0, 4)"
          :key="tag"
          class="px-2 py-0.5 bg-gray-800 rounded text-xs text-gray-400"
        >
          #{{ tag }}
        </span>
      </div>

      <p v-if="page.updated_at" class="text-xs text-gray-500">{{ page.updated_at }}</p>
    </NuxtLink>

    <button
      class="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded text-gray-500 hover:text-red-400 hover:bg-gray-700"
      title="Supprimer cette page"
      @click.prevent="onDelete"
    >
      <Trash2 class="w-3.5 h-3.5" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { Trash2 } from 'lucide-vue-next'
import type { WikiPageSummary } from '~/types/api'

const props = defineProps<{ page: WikiPageSummary }>()
const emit = defineEmits<{ delete: [slug: string] }>()

function onDelete() {
  if (confirm(`Supprimer définitivement « ${props.page.title} » ?`)) {
    emit('delete', props.page.slug)
  }
}
</script>
