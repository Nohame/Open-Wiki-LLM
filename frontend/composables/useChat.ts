import { ref } from 'vue'
import { useApi } from '~/composables/useApi'
import type { ChatMessage, AnswerMode } from '~/types/api'

export function useChat() {
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const error = ref('')
  const { post } = useApi()

  async function sendMessage(question: string, mode: AnswerMode) {
    messages.value.push({ role: 'user', content: question })
    loading.value = true
    error.value = ''
    try {
      const data = await post<{ answer: string; mode: string; sources: string[] }>(
        '/api/answer',
        { question, mode },
      )
      messages.value.push({
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
      })
    } catch {
      error.value = 'Erreur lors de la requête.'
    } finally {
      loading.value = false
    }
  }

  function clearHistory() {
    messages.value = []
  }

  return { messages, loading, error, sendMessage, clearHistory }
}
