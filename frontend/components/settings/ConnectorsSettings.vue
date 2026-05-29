<template>
  <div class="space-y-4">
    <div class="p-4 border border-gray-700 rounded-lg space-y-4">
      <div class="flex items-center justify-between">
        <span class="text-sm font-medium text-white">Google Drive</span>
        <span
          :class="[
            'text-xs px-2 py-0.5 rounded-full font-medium',
            isConnected ? 'bg-green-900 text-green-300' : 'bg-gray-800 text-gray-400',
          ]"
        >
          {{ isConnected ? 'Connecté' : 'Non connecté' }}
        </span>
      </div>

      <div class="space-y-2">
        <div>
          <label class="block text-xs text-gray-400 mb-1">Client ID</label>
          <input
            v-model="local.google_drive.client_id"
            type="text"
            placeholder="xxx.apps.googleusercontent.com"
            class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
            @input="emit('update:modelValue', { ...local, google_drive: { ...local.google_drive } })"
          />
        </div>
        <div>
          <label class="block text-xs text-gray-400 mb-1">Client Secret</label>
          <div class="relative">
            <input
              v-model="local.google_drive.client_secret"
              :type="showSecret ? 'text' : 'password'"
              placeholder="GOCSPX-..."
              class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500 pr-10"
              @input="emit('update:modelValue', { ...local, google_drive: { ...local.google_drive } })"
            />
            <button
              type="button"
              class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
              @click="showSecret = !showSecret"
            >
              <component :is="showSecret ? EyeOff : Eye" class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <div class="flex gap-2">
        <button
          v-if="!isConnected"
          class="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm rounded-lg transition-colors"
          :disabled="connecting"
          @click="handleConnect"
        >
          {{ connecting ? 'Redirection…' : 'Connecter à Google Drive' }}
        </button>
        <button
          v-else
          class="px-3 py-1.5 bg-red-700 hover:bg-red-600 text-white text-sm rounded-lg transition-colors"
          @click="emit('disconnect')"
        >
          Déconnecter
        </button>
      </div>

      <p v-if="connectError" class="text-xs text-red-400">{{ connectError }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, computed, ref, watch } from 'vue'
import { Eye, EyeOff } from 'lucide-vue-next'
import type { ConnectorsConfig } from '~/types/api'

const props = defineProps<{ modelValue: ConnectorsConfig; connectionFailed?: boolean }>()
const emit = defineEmits<{
  'update:modelValue': [ConnectorsConfig]
  'connect': []
  'disconnect': []
}>()

const local = reactive({
  ...props.modelValue,
  google_drive: { ...props.modelValue.google_drive },
})
watch(() => props.modelValue, (v) => {
  Object.assign(local, v)
  Object.assign(local.google_drive, v.google_drive)
}, { deep: true })

watch(() => props.connectionFailed, (failed) => {
  if (failed) {
    connecting.value = false
  }
})

const showSecret = ref(false)
const connecting = ref(false)
const connectError = ref<string | null>(null)

const isConnected = computed(() => local.google_drive.access_token === '****')

function handleConnect() {
  if (!local.google_drive.client_id || !local.google_drive.client_secret) {
    connectError.value = 'Enregistrez d\'abord vos credentials Google Drive'
    return
  }
  connectError.value = null
  connecting.value = true
  emit('connect')
}
</script>
