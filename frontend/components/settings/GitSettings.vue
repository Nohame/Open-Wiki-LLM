<template>
  <div class="space-y-4">
    <!-- Toggle -->
    <div class="flex items-center justify-between">
      <div>
        <span class="text-sm font-medium text-white">Dépôt git du wiki</span>
        <p class="text-xs text-gray-400 mt-0.5">Versionner automatiquement les pages</p>
      </div>
      <button
        :class="[
          'relative w-9 h-5 rounded-full transition-colors',
          local.enabled ? 'bg-blue-600' : 'bg-gray-700',
        ]"
        @click="toggle"
      >
        <span
          :class="[
            'absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform',
            local.enabled ? 'translate-x-4' : 'translate-x-0.5',
          ]"
        />
      </button>
    </div>

    <!-- Badge statut (état 3 : initialisé) -->
    <div
      v-if="local.enabled && status?.initialized"
      class="flex items-center justify-between bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5"
    >
      <div>
        <div class="flex items-center gap-2 mb-1">
          <span class="w-2 h-2 bg-green-500 rounded-full inline-block" />
          <span class="text-sm font-medium text-white">Initialisé</span>
          <span v-if="status.dirty_files > 0" class="text-xs text-gray-400">
            · {{ status.dirty_files }} fichier{{ status.dirty_files > 1 ? 's' : '' }} modifié{{ status.dirty_files > 1 ? 's' : '' }}
          </span>
        </div>
        <p v-if="status.last_commit" class="text-xs text-gray-500">
          Dernier commit :
          <code class="text-blue-400">{{ status.last_commit.split(' ')[0] }}</code>
          <span class="text-gray-400"> {{ status.last_commit.split(' ').slice(1).join(' ') }}</span>
        </p>
      </div>
      <button
        :disabled="loading"
        class="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white text-xs rounded-lg transition-colors whitespace-nowrap"
        @click="pushRepo"
      >
        {{ loading ? 'Push…' : 'Push ↑' }}
      </button>
    </div>

    <!-- Champs config -->
    <fieldset :disabled="!local.enabled" class="space-y-3 disabled:opacity-40">
      <div>
        <label class="block text-xs text-gray-400 mb-1">
          Remote URL <span class="text-gray-600">(optionnel)</span>
        </label>
        <input
          v-model="local.remote_url"
          type="text"
          placeholder="git@github.com:user/wiki.git"
          class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500 disabled:cursor-not-allowed"
          @input="emit('update:modelValue', { ...local })"
        />
      </div>
      <div class="flex items-end gap-3">
        <div class="flex-1">
          <label class="block text-xs text-gray-400 mb-1">Branche</label>
          <input
            v-model="local.branch"
            type="text"
            placeholder="main"
            class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500 disabled:cursor-not-allowed"
            @input="emit('update:modelValue', { ...local })"
          />
        </div>
        <div class="pb-1.5">
          <label class="block text-xs text-gray-400 mb-1">Auto-push</label>
          <button
            :class="[
              'relative w-8 h-4 rounded-full transition-colors',
              local.auto_push ? 'bg-blue-600' : 'bg-gray-700',
            ]"
            @click="toggleAutoPush"
          >
            <span
              :class="[
                'absolute top-0.5 w-3 h-3 bg-white rounded-full shadow transition-transform',
                local.auto_push ? 'translate-x-4' : 'translate-x-0.5',
              ]"
            />
          </button>
        </div>
      </div>
    </fieldset>

    <!-- Bouton Init (état 2 : activé non initialisé) -->
    <button
      v-if="local.enabled && !status?.initialized"
      :disabled="loading"
      class="w-full px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
      @click="initRepo"
    >
      {{ loading ? 'Initialisation…' : 'Initialiser le dépôt git' }}
    </button>

    <p v-if="error" class="text-xs text-red-400">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch, onMounted } from 'vue'
import { useGit } from '~/composables/useGit'
import type { GitConfig } from '~/types/api'

const props = defineProps<{ modelValue: GitConfig }>()
const emit = defineEmits<{ 'update:modelValue': [GitConfig] }>()

const { status, loading, error, fetchStatus, initRepo, pushRepo } = useGit()

const local = reactive({ ...props.modelValue })

watch(() => props.modelValue, (v) => { Object.assign(local, v) }, { deep: true })

watch(() => local.enabled, async (enabled) => {
  if (enabled && !status.value) await fetchStatus()
})

onMounted(async () => {
  if (props.modelValue.enabled) await fetchStatus()
})

function toggle() {
  local.enabled = !local.enabled
  emit('update:modelValue', { ...local })
}

function toggleAutoPush() {
  local.auto_push = !local.auto_push
  emit('update:modelValue', { ...local })
}
</script>
