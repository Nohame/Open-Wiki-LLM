<template>
  <div ref="container" class="flex-1 overflow-y-auto px-4 py-6 space-y-6">
    <!-- État vide -->
    <div v-if="!messages.length" class="flex flex-col items-center justify-center h-full text-center space-y-3">
      <div class="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center">
        <BookOpen class="w-6 h-6 text-gray-400" />
      </div>
      <p class="text-gray-400 text-sm">Pose une question sur le wiki</p>
    </div>

    <ChatMessage v-for="(msg, i) in messages" :key="i" :message="msg" />

    <!-- Indicateur loading -->
    <div v-if="loading" class="flex gap-3">
      <div class="w-7 h-7 rounded-full bg-gray-700 shrink-0 flex items-center justify-center text-xs font-bold">W</div>
      <div class="px-4 py-3 bg-gray-800 rounded-xl rounded-tl-none">
        <div class="flex gap-1">
          <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay:0ms" />
          <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay:150ms" />
          <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay:300ms" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { BookOpen } from 'lucide-vue-next'
import type { ChatMessage as ChatMsg } from '~/types/api'

const props = defineProps<{ messages: ChatMsg[]; loading: boolean }>()
const container = ref<HTMLElement>()

watch(
  () => [props.messages.length, props.loading],
  async () => {
    await nextTick()
    if (container.value) {
      container.value.scrollTop = container.value.scrollHeight
    }
  },
)
</script>
