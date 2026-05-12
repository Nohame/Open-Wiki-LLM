<template>
  <aside
    :class="[
      'flex flex-col bg-sidebar-dark border-r border-gray-800 transition-all duration-200 shrink-0',
      collapsed ? 'w-12' : 'w-64',
    ]"
  >
    <!-- Logo -->
    <div class="flex items-center h-14 px-3 border-b border-gray-800">
      <div class="w-6 h-6 rounded-full bg-blue-600 shrink-0 flex items-center justify-center">
        <BookOpen class="w-3 h-3 text-white" />
      </div>
      <span v-if="!collapsed" class="ml-3 font-semibold text-white truncate">OpenWikiLLM</span>
    </div>

    <!-- Nav -->
    <nav class="flex-1 p-2 space-y-1">
      <NuxtLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="flex items-center gap-3 px-2 py-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
        active-class="text-white bg-gray-800"
      >
        <component :is="item.icon" class="w-4 h-4 shrink-0" />
        <span v-if="!collapsed" class="text-sm">{{ item.label }}</span>
      </NuxtLink>
    </nav>

    <!-- Toggle -->
    <div class="p-2 border-t border-gray-800">
      <button
        class="flex items-center gap-3 px-2 py-2 w-full rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
        @click="toggle"
      >
        <PanelLeft class="w-4 h-4 shrink-0" />
        <span v-if="!collapsed" class="text-sm">Réduire</span>
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { BookOpen, MessageSquare, Library, Upload, PanelLeft } from 'lucide-vue-next'
import { useLocalStorage } from '@vueuse/core'

const collapsed = useLocalStorage('sidebar-collapsed', false)

function toggle() {
  collapsed.value = !collapsed.value
}

const navItems = [
  { to: '/chat', icon: MessageSquare, label: 'Chat' },
  { to: '/wiki', icon: Library, label: 'Wiki' },
  { to: '/ingest', icon: Upload, label: 'Ingest' },
]
</script>
