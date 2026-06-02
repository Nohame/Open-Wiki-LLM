import { ref } from 'vue'
import { useApi } from '~/composables/useApi'
import type { GitStatus } from '~/types/api'

export function useGit() {
  const { get, post } = useApi()
  const status = ref<GitStatus | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchStatus(): Promise<void> {
    error.value = null
    try {
      status.value = await get<GitStatus>('/api/git/status')
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Erreur lors du chargement du statut git'
    }
  }

  async function initRepo(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      await post<{ status: string }>('/api/git/init', {})
      await fetchStatus()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : "Erreur lors de l'initialisation"
    } finally {
      loading.value = false
    }
  }

  async function pushRepo(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      await post<{ status: string }>('/api/git/push', {})
      await fetchStatus()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Erreur lors du push'
    } finally {
      loading.value = false
    }
  }

  return { status, loading, error, fetchStatus, initRepo, pushRepo }
}
