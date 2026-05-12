import type { Config } from 'tailwindcss'

export default {
  darkMode: 'class',
  content: [
    './components/**/*.{vue,ts}',
    './layouts/**/*.vue',
    './pages/**/*.vue',
    './composables/**/*.ts',
    './stores/**/*.ts',
    './app.vue',
  ],
  plugins: [require('@tailwindcss/typography')],
  theme: {
    extend: {
      colors: {
        sidebar: {
          DEFAULT: '#1e293b',
          dark: '#192638',
        },
      },
    },
  },
} satisfies Config
