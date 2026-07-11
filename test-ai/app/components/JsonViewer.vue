<template>
  <div>
    <v-btn
      size="small"
      variant="tonal"
      :prepend-icon="raw ? 'mdi-text-box-outline' : 'mdi-code-json'"
      @click="open = !open"
    >
      {{ open ? `Hide ${label}` : `View ${label}` }}
    </v-btn>

    <v-expand-transition>
      <pre v-if="open" class="json-viewer mt-2">{{ formatted }}</pre>
    </v-expand-transition>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  data: unknown
  label: string
  raw?: boolean
}>(), {
  raw: false,
})

const open = ref(false)
const formatted = computed(() => props.raw ? String(props.data ?? '') : JSON.stringify(props.data, null, 2))
</script>

<style scoped>
.json-viewer {
  background: rgba(128, 128, 128, 0.1);
  border-radius: 4px;
  padding: 12px;
  font-size: 12px;
  line-height: 1.5;
  max-height: 480px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
