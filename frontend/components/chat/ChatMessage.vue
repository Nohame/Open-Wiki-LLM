<template>
  <div :class="['flex gap-3', isUser ? 'flex-row-reverse' : 'flex-row']">
    <!-- Avatar -->
    <div
      :class="[
        'w-7 h-7 rounded-full shrink-0 flex items-center justify-center text-xs font-bold mt-1',
        isUser ? 'bg-blue-600' : 'bg-gray-700',
      ]"
    >
      {{ isUser ? 'U' : 'W' }}
    </div>

    <!-- Contenu -->
    <div :class="['max-w-2xl space-y-2', isUser ? 'items-end' : 'items-start']">
      <div
        :class="[
          'px-4 py-3 rounded-xl text-sm',
          isUser
            ? 'bg-blue-600 text-white rounded-tr-none'
            : 'bg-gray-800 text-gray-100 rounded-tl-none',
        ]"
      >
        <!-- eslint-disable vue/no-v-html -->
        <div
          v-if="!isUser"
          class="prose prose-invert prose-sm max-w-none"
          v-html="renderedContent"
        />
        <span v-else>{{ message.content }}</span>
      </div>

      <!-- Sources -->
      <div v-if="message.sources?.length" class="flex flex-wrap gap-1 px-1">
        <SourceChip v-for="s in message.sources" :key="s" :slug="s" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import type { ChatMessage } from '~/types/api'

const props = defineProps<{ message: ChatMessage }>()

const isUser = computed(() => props.message.role === 'user')
const renderedContent = computed(() =>
  DOMPurify.sanitize(marked.parse(props.message.content) as string),
)
</script>
