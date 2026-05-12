<template>
  <div class="flex flex-col h-full">
    <ChatMessages :messages="messages" :loading="loading" />
    <ChatInput :loading="loading" @send="sendMessage" />
  </div>
</template>

<script setup lang="ts">
const { messages, loading, sendMessage } = useChat()
</script>
