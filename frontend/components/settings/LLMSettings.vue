<template>
  <div class="space-y-4">
    <!-- Sélecteur provider -->
    <div class="space-y-1">
      <label class="block text-xs text-gray-400 uppercase tracking-wider">Provider</label>
      <select
        v-model="local.provider"
        class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
        @change="emit('update:modelValue', { ...local })"
      >
        <option value="ollama">Ollama (local)</option>
        <option value="openai">OpenAI</option>
        <option value="gemini">Google Gemini</option>
        <option value="anthropic">Anthropic</option>
        <option value="custom">Custom (OpenAI-compatible)</option>
      </select>
    </div>

    <!-- Ollama -->
    <template v-if="local.provider === 'ollama'">
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">URL de base</label>
        <input v-model="local.ollama.base_url" placeholder="http://host.docker.internal:11434" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle texte</label>
        <input v-model="local.ollama.model" placeholder="mistral" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle vision</label>
        <input v-model="local.ollama.vision_model" placeholder="llava" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
    </template>

    <!-- OpenAI -->
    <template v-else-if="local.provider === 'openai'">
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Clé API</label>
        <div class="relative">
          <input v-model="local.openai.api_key" :type="showOpenAIKey ? 'text' : 'password'" placeholder="sk-..." :class="inputClass + ' pr-10'" @input="emit('update:modelValue', { ...local })" />
          <button type="button" class="absolute right-2 top-2 text-gray-400 hover:text-white" @click="showOpenAIKey = !showOpenAIKey">
            <Eye v-if="!showOpenAIKey" class="w-4 h-4" /><EyeOff v-else class="w-4 h-4" />
          </button>
        </div>
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle texte</label>
        <input v-model="local.openai.model" placeholder="gpt-4o" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle vision</label>
        <input v-model="local.openai.vision_model" placeholder="gpt-4o" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
    </template>

    <!-- Gemini -->
    <template v-else-if="local.provider === 'gemini'">
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Clé API</label>
        <div class="relative">
          <input v-model="local.gemini.api_key" :type="showGeminiKey ? 'text' : 'password'" placeholder="AIza..." :class="inputClass + ' pr-10'" @input="emit('update:modelValue', { ...local })" />
          <button type="button" class="absolute right-2 top-2 text-gray-400 hover:text-white" @click="showGeminiKey = !showGeminiKey">
            <Eye v-if="!showGeminiKey" class="w-4 h-4" /><EyeOff v-else class="w-4 h-4" />
          </button>
        </div>
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle texte</label>
        <input v-model="local.gemini.model" placeholder="gemini-1.5-pro" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle vision</label>
        <input v-model="local.gemini.vision_model" placeholder="gemini-1.5-pro" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
    </template>

    <!-- Anthropic -->
    <template v-else-if="local.provider === 'anthropic'">
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Clé API</label>
        <div class="relative">
          <input v-model="local.anthropic.api_key" :type="showAnthropicKey ? 'text' : 'password'" placeholder="sk-ant-..." :class="inputClass + ' pr-10'" @input="emit('update:modelValue', { ...local })" />
          <button type="button" class="absolute right-2 top-2 text-gray-400 hover:text-white" @click="showAnthropicKey = !showAnthropicKey">
            <Eye v-if="!showAnthropicKey" class="w-4 h-4" /><EyeOff v-else class="w-4 h-4" />
          </button>
        </div>
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle texte</label>
        <input v-model="local.anthropic.model" placeholder="claude-opus-4-7" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle vision</label>
        <input v-model="local.anthropic.vision_model" placeholder="claude-opus-4-7" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
    </template>

    <!-- Custom -->
    <template v-else-if="local.provider === 'custom'">
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">URL de base</label>
        <input v-model="local.custom.base_url" placeholder="https://openrouter.ai/api/v1" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Clé API</label>
        <div class="relative">
          <input v-model="local.custom.api_key" :type="showCustomKey ? 'text' : 'password'" placeholder="sk-..." :class="inputClass + ' pr-10'" @input="emit('update:modelValue', { ...local })" />
          <button type="button" class="absolute right-2 top-2 text-gray-400 hover:text-white" @click="showCustomKey = !showCustomKey">
            <Eye v-if="!showCustomKey" class="w-4 h-4" /><EyeOff v-else class="w-4 h-4" />
          </button>
        </div>
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle texte</label>
        <input v-model="local.custom.model" placeholder="mistral" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
      <div class="space-y-1">
        <label class="block text-xs text-gray-400">Modèle vision (optionnel)</label>
        <input v-model="local.custom.vision_model" placeholder="" :class="inputClass" @input="emit('update:modelValue', { ...local })" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { Eye, EyeOff } from 'lucide-vue-next'
import type { LLMConfig } from '~/types/api'

const props = defineProps<{ modelValue: LLMConfig }>()
const emit = defineEmits<{ 'update:modelValue': [LLMConfig] }>()

const inputClass = 'w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500'

const local = reactive(JSON.parse(JSON.stringify(props.modelValue)) as LLMConfig)
watch(() => props.modelValue, (v) => Object.assign(local, JSON.parse(JSON.stringify(v))), { deep: true })

const showOpenAIKey = ref(false)
const showGeminiKey = ref(false)
const showAnthropicKey = ref(false)
const showCustomKey = ref(false)
</script>
