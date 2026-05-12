<template>
  <div class="border-t border-gray-800 p-4 space-y-3">
    <div class="flex items-center gap-2">
      <label class="text-xs text-gray-400">Mode :</label>
      <select
        v-model="selectedMode"
        class="text-xs bg-gray-800 border border-gray-700 text-gray-300 rounded px-2 py-1 focus:outline-none focus:border-blue-500"
      >
        <option value="validated_only">validated_only</option>
        <option value="strict">strict</option>
        <option value="draft">draft</option>
        <option value="source_only">source_only</option>
      </select>
    </div>

    <div class="flex gap-2">
      <textarea
        ref="textarea"
        v-model="input"
        rows="1"
        placeholder="Pose ta question..."
        :disabled="loading"
        class="flex-1 bg-gray-800 border border-gray-700 text-white placeholder-gray-500 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:border-blue-500 disabled:opacity-50"
        style="min-height: 48px; max-height: 200px"
        @keydown.meta.enter.prevent="submit"
        @keydown.ctrl.enter.prevent="submit"
        @input="autoResize"
      />
      <button
        :disabled="!input.trim() || loading"
        class="px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-xl transition-colors shrink-0"
        @click="submit"
      >
        <Send class="w-4 h-4" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Send } from 'lucide-vue-next'
import type { AnswerMode } from '~/types/api'

const props = defineProps<{ loading: boolean }>()
const emit = defineEmits<{ send: [question: string, mode: AnswerMode] }>()

const input = ref('')
const selectedMode = ref<AnswerMode>('validated_only')
const textarea = ref<HTMLTextAreaElement>()

function autoResize() {
  if (!textarea.value) return
  textarea.value.style.height = 'auto'
  textarea.value.style.height = `${Math.min(textarea.value.scrollHeight, 200)}px`
}

function submit() {
  if (!input.value.trim() || props.loading) return
  emit('send', input.value.trim(), selectedMode.value)
  input.value = ''
  if (textarea.value) textarea.value.style.height = '48px'
}
</script>
