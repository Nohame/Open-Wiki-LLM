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

  async function get<T>(path: string): Promise<T> {
    return $fetch<T>(`${baseUrl}${path}`, {
      headers: headers(),
      onResponseError({ response }) {
        if (response.status === 401) {
          authStore.logout()
          navigateTo('/login')
        }
      },
    })
  }

  async function post<T>(path: string, body: unknown): Promise<T> {
    return $fetch<T>(`${baseUrl}${path}`, {
      method: 'POST',
      headers: headers({ 'Content-Type': 'application/json' }),
      body,
      onResponseError({ response }) {
        if (response.status === 401) {
          authStore.logout()
          navigateTo('/login')
        }
      },
    })
  }

  async function postForm<T>(path: string, formData: FormData): Promise<T> {
    return $fetch<T>(`${baseUrl}${path}`, {
      method: 'POST',
      headers: headers(),
      body: formData,
      onResponseError({ response }) {
        if (response.status === 401) {
          authStore.logout()
          navigateTo('/login')
        }
      },
    })
  }

  return { get, post, postForm }
}
