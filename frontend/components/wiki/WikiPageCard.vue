<template>
  <div class="relative">
    <!-- Mode confirmation -->
    <div
      v-if="confirming"
      class="p-4 bg-gray-900 border border-red-700 rounded-xl space-y-3"
    >
      <p class="text-sm text-white font-medium">Supprimer ?</p>
      <p class="text-xs text-gray-400 leading-relaxed">
        « {{ page.title }} » sera supprimée définitivement.
      </p>
      <div class="flex gap-2">
        <button
          data-testid="confirm-btn"
          class="flex-1 px-3 py-1.5 bg-red-700 hover:bg-red-600 text-white text-xs font-medium rounded-lg transition-colors"
          @click="onConfirm"
        >
          Oui, supprimer
        </button>
        <button
          data-testid="cancel-btn"
          class="flex-1 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-200 text-xs font-medium rounded-lg transition-colors"
          @click="confirming = false"
        >
          Annuler
        </button>
      </div>
    </div>

    <!-- Mode normal -->
    <div v-else class="relative group">
      <NuxtLink
        :to="`/wiki/${page.slug}`"
        class="block p-4 bg-gray-900 border border-gray-800 rounded-xl hover:border-gray-600 hover:bg-gray-800 transition-colors space-y-2"
      >
        <div class="flex items-start justify-between gap-2">
          <h3 class="font-medium text-white text-sm leading-snug pr-6">{{ page.title }}</h3>
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

      <button
        data-testid="delete-btn"
        class="absolute top-2.5 right-2.5 p-1.5 rounded-md text-gray-500 hover:text-red-400 hover:bg-red-950 transition-colors"
        title="Supprimer cette page"
        @click.prevent="confirming = true"
      >
        <Trash2 class="w-3.5 h-3.5" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Trash2 } from 'lucide-vue-next'
import type { WikiPageSummary } from '~/types/api'

const props = defineProps<{ page: WikiPageSummary }>()
const emit = defineEmits<{ delete: [slug: string] }>()

const confirming = ref(false)

function onConfirm() {
  emit('delete', props.page.slug)
  confirming.value = false
}
</script>
