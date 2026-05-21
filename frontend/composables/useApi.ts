import { useAuthStore } from '~/stores/auth'

export function useApi() {
  const authStore = useAuthStore()
  const config = useRuntimeConfig()
  const baseUrl = config.public.apiBaseUrl as string

  function headers(extra: Record<string, string> = {}): Record<string, string> {
    const h: Record<string, string> = { ...extra }
    if (authStore.apiKey) h['X-API-Key'] = authStore.apiKey
    return h
  }

  function onResponseError({ response }: { response: { status: number } }) {
    if (response.status === 401) {
      authStore.logout()
      navigateTo('/login')
    }
  }

  async function get<T>(path: string): Promise<T> {
    return $fetch<T>(`${baseUrl}${path}`, {
      headers: headers(),
      onResponseError,
    })
  }

  async function post<T>(path: string, body: unknown): Promise<T> {
    return $fetch<T>(`${baseUrl}${path}`, {
      method: 'POST',
      headers: headers({ 'Content-Type': 'application/json' }),
      body: body as Record<string, unknown>,
      onResponseError,
    })
  }

  async function postForm<T>(path: string, formData: FormData): Promise<T> {
    return $fetch<T>(`${baseUrl}${path}`, {
      method: 'POST',
      headers: headers(),
      body: formData,
      onResponseError,
    })
  }

  async function patch<T>(path: string, body: unknown): Promise<T> {
    return $fetch<T>(`${baseUrl}${path}`, {
      method: 'PATCH',
      headers: headers({ 'Content-Type': 'application/json' }),
      body: body as Record<string, unknown>,
      onResponseError,
    })
  }

  async function del(path: string): Promise<void> {
    await $fetch(`${baseUrl}${path}`, {
      method: 'DELETE',
      headers: headers(),
      onResponseError,
    })
  }

  return { get, post, postForm, patch, del }
}
