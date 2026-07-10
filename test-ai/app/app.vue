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
        @click="theme.toggle()"
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
</script>
