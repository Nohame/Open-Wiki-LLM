import { useAuthStore } from '~/stores/auth'

export default defineNuxtRouteMiddleware((to) => {
  if (to.path === '/login') return

  const authStore = useAuthStore()
  authStore.loadFromStorage()

  if (!authStore.isAuthenticated) return navigateTo('/login')
})
