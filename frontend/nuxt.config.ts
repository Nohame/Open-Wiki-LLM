export default defineNuxtConfig({
  ssr: false,
  modules: ['@nuxtjs/tailwindcss', '@pinia/nuxt', '@vueuse/nuxt'],
  runtimeConfig: {
    public: {
      apiBaseUrl: 'http://localhost:8088',
    },
  },
  app: {
    head: {
      title: 'OpenWikiLLM',
      htmlAttrs: { class: 'dark' },
    },
  },
})
