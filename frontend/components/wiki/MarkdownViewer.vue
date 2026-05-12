<template>
  <!-- eslint-disable vue/no-v-html -->
  <div
    class="prose prose-invert prose-sm max-w-none
           prose-headings:text-white prose-p:text-gray-300
           prose-code:text-blue-300 prose-pre:bg-gray-800
           prose-a:text-blue-400 prose-strong:text-white
           prose-li:text-gray-300"
    v-html="rendered"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps<{ content: string }>()
const rendered = computed(() =>
  DOMPurify.sanitize(marked.parse(props.content) as string),
)
</script>
