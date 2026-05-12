<template>
  <NuxtLink
    :to="`/wiki/${page.slug}`"
    class="block p-4 bg-gray-900 border border-gray-800 rounded-xl hover:border-gray-600 hover:bg-gray-800 transition-colors space-y-2"
  >
    <div class="flex items-start justify-between gap-2">
      <h3 class="font-medium text-white text-sm leading-snug">{{ page.title }}</h3>
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
</template>

<script setup lang="ts">
import type { WikiPageSummary } from '~/types/api'
defineProps<{ page: WikiPageSummary }>()
</script>
