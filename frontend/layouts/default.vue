<template>
  <div class="flex h-screen bg-gray-950 text-white overflow-hidden">
    <AppSidebar />
    <div class="flex flex-col flex-1 overflow-hidden">
      <AppHeader />
      <main class="flex-1 overflow-auto">
        <slot />
      </main>
    </div>
  </div>
</template>
