import { ref } from 'vue'
import { useApi } from '~/composables/useApi'
import type { IngestResult } from '~/types/api'

export function useIngest() {
  const result = ref<IngestResult | null>(null)
  const loading = ref(false)
  const error = ref('')
  const { post, postForm } = useApi()

  async function ingestText(text: string, title: string, tags: string[]) {
    loading.value = true
    error.value = ''
    result.value = null
    try {
      result.value = await post<IngestResult>('/api/ingest/text', { text, title, tags })
    } catch {
      error.value = "Erreur lors de l'ingestion."
    } finally {
      loading.value = false
    }
  }

  async function ingestImage(file: File, title: string, tags: string[]) {
    loading.value = true
    error.value = ''
    result.value = null
    try {
      const form = new FormData()
      form.append('file', file)
      if (title) form.append('title', title)
      form.append('tags', tags.join(','))
      result.value = await postForm<IngestResult>('/api/ingest/image', form)
    } catch {
      error.value = "Erreur lors de l'ingestion."
    } finally {
      loading.value = false
    }
  }

  async function ingestFile(file: File, tags: string[]): Promise<IngestResult> {
    const form = new FormData()
    form.append('file', file)
    form.append('title', file.name.replace(/\.[^.]+$/, ''))
    form.append('tags', tags.join(','))
    return postForm<IngestResult>('/api/ingest/file', form)
  }

  function reset() {
    result.value = null
    error.value = ''
  }

  return { result, loading, error, ingestText, ingestImage, ingestFile, reset }
}
