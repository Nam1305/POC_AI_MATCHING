<template>
  <v-app>
    <v-app-bar color="primary" flat>
      <v-app-bar-title>
        <NuxtLink to="/" class="text-white text-decoration-none">
          AI CV Screening
        </NuxtLink>
      </v-app-bar-title>
      <v-spacer />
      <v-btn
        :icon="theme.global.current.value.dark ? 'mdi-weather-night' : 'mdi-weather-sunny'"
        variant="text"
        @click="toggleTheme"
      />
    </v-app-bar>

    <v-main>
      <v-container class="py-6">
        <NuxtPage />
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
const theme = useTheme()

const STORAGE_KEY = 'theme-override'

function applySystemTheme(mql: MediaQueryList | MediaQueryListEvent) {
  theme.change(mql.matches ? 'dark' : 'light')
}

function toggleTheme() {
  theme.change(theme.global.current.value.dark ? 'light' : 'dark')
  if (!import.meta.server) localStorage.setItem(STORAGE_KEY, theme.global.name.value)
}

onMounted(() => {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored) {
    theme.change(stored)
    return
  }

  const mql = window.matchMedia('(prefers-color-scheme: dark)')
  applySystemTheme(mql)
  mql.addEventListener('change', applySystemTheme)
  onUnmounted(() => mql.removeEventListener('change', applySystemTheme))
})
</script>
