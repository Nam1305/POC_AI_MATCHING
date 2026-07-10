<template>
  <div>
    <v-btn
      size="small"
      variant="tonal"
      :prepend-icon="open ? 'mdi-code-json' : 'mdi-code-json'"
      @click="open = !open"
    >
      {{ open ? `Hide ${label} JSON` : `View ${label} JSON` }}
    </v-btn>

    <v-expand-transition>
      <pre v-if="open" class="json-viewer mt-2">{{ formatted }}</pre>
    </v-expand-transition>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  data: unknown
  label: string
}>()

const open = ref(false)
const formatted = computed(() => JSON.stringify(props.data, null, 2))
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
