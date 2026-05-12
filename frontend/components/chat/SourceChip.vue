<template>
  <NuxtLink
    :to="`/wiki/${slug}`"
    class="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded text-xs text-blue-400 hover:text-blue-300 transition-colors"
  >
    <FileText class="w-3 h-3" />
    {{ slug }}
  </NuxtLink>
</template>

<script setup lang="ts">
import { FileText } from 'lucide-vue-next'
defineProps<{ slug: string }>()
</script>
