<template>
  <div class="space-y-4">
    <div class="space-y-1">
      <label class="block text-xs text-gray-400">Taille max du texte ingéré (caractères)</label>
      <input
        v-model.number="local.max_text_chars"
        type="number"
        min="1000"
        max="100000"
        step="1000"
        class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
        @input="emit('update:modelValue', { ...local })"
      />
      <p class="text-xs text-gray-500">Le texte sera tronqué à cette limite avant envoi au LLM. Défaut : 30 000.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import type { IngestConfig } from '~/types/api'

const props = defineProps<{ modelValue: IngestConfig }>()
const emit = defineEmits<{ 'update:modelValue': [IngestConfig] }>()
const local = reactive({ ...props.modelValue })
watch(() => props.modelValue, (v) => Object.assign(local, v))
</script>
