// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  modules: ['vuetify-nuxt-module', 'nuxt-mongoose'],
  vuetify: {
    moduleOptions: {
      ssrClientHints: {
        prefersColorScheme: true,
        prefersColorSchemeOptions: {
          useBrowserThemeOnly: false,
        },
      },
    },
    vuetifyOptions: {
      theme: {
        defaultTheme: 'light',
        themes: {
          light: { dark: false },
          dark: { dark: true },
        },
      },
    },
  },
  mongoose: {
    uri: process.env.NUXT_MONGOOSE_URI,
    modelsDir: 'models',
  },
  runtimeConfig: {
    aiServiceUrl: process.env.NUXT_AI_SERVICE_URL || 'http://localhost:8000',
  },
})