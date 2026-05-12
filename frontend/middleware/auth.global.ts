export default defineNuxtRouteMiddleware((to) => {
  if (to.path === '/login') return

  if (typeof window !== 'undefined') {
    const key = localStorage.getItem('openwikillm_api_key')
    if (!key) return navigateTo('/login')
  }
})
