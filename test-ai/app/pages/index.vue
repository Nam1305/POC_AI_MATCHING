<template>
  <div>
    <v-card class="mb-6">
      <v-card-title class="d-flex align-center">
        <v-icon icon="mdi-clipboard-text-search-outline" class="mr-2" />
        New Screening
      </v-card-title>
      <v-card-text>
        <v-form @submit.prevent="submit">
          <v-text-field
            v-model="name"
            label="Screening name"
            placeholder="e.g. Backend Engineer batch #1"
            prepend-inner-icon="mdi-tag-outline"
            :disabled="loading"
            required
          />

          <v-textarea
            v-model="jdText"
            label="Job description text"
            placeholder="Paste the full JD text here..."
            prepend-inner-icon="mdi-text-box-outline"
            rows="8"
            auto-grow
            :disabled="loading"
            required
          />

          <div class="text-subtitle-2 mb-2">CV URLs</div>
          <div
            v-for="(url, i) in cvUrls"
            :key="i"
            class="d-flex align-center mb-1"
          >
            <v-text-field
              v-model="cvUrls[i]"
              :label="`CV URL #${i + 1}`"
              prepend-inner-icon="mdi-file-pdf-box"
              density="comfortable"
              hide-details
              :disabled="loading"
            />
            <v-btn
              icon="mdi-close"
              variant="text"
              class="ml-1"
              :disabled="loading || cvUrls.length === 1"
              @click="cvUrls.splice(i, 1)"
            />
          </div>
          <div class="d-flex mb-4">
            <v-btn
              variant="tonal"
              prepend-icon="mdi-plus"
              :disabled="loading"
              @click="cvUrls.push('')"
            >
              Add CV URL
            </v-btn>
          </div>

          <v-alert v-if="error" type="error" variant="tonal" class="mb-4" closable @click:close="error = null">
            {{ error }}
          </v-alert>

          <v-alert v-if="loading" type="warning" variant="tonal" class="mb-4">
            Screening in progress — this can take a while. Please don't close or reload this tab until it finishes.
          </v-alert>

          <v-btn
            type="submit"
            color="primary"
            size="large"
            block
            :loading="loading"
            :disabled="!canSubmit"
            prepend-icon="mdi-send"
          >
            Run Screening
          </v-btn>
        </v-form>
      </v-card-text>
    </v-card>

    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon icon="mdi-history" class="mr-2" />
        Past Screenings
        <v-spacer />
        <v-btn icon="mdi-refresh" variant="text" :loading="pending" @click="refresh()" />
      </v-card-title>
      <v-divider />

      <v-list v-if="screenings?.length" lines="two">
        <v-list-item
          v-for="s in screenings"
          :key="s._id"
          :title="s.name"
          :subtitle="`${s.jdTitle ?? 'Untitled JD'} · ${formatDate(s.createdAt)}`"
          @click="$router.push(`/screenings/${s._id}`)"
        >
          <template #prepend>
            <v-avatar color="primary" variant="tonal">
              <v-icon icon="mdi-account-search-outline" />
            </v-avatar>
          </template>
          <template #append>
            <v-chip size="small" variant="tonal">
              {{ s.candidateCount }} candidate{{ s.candidateCount === 1 ? '' : 's' }}
            </v-chip>
          </template>
        </v-list-item>
      </v-list>
      <v-card-text v-else-if="!pending" class="text-medium-emphasis">
        No screenings yet. Run your first one above.
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
interface ScreeningSummary {
  _id: string
  name: string
  jdTitle: string | null
  candidateCount: number
  createdAt: string
}

const name = ref('')
const jdText = ref('')
const cvUrls = ref<string[]>([''])
const loading = ref(false)
const error = ref<string | null>(null)

const router = useRouter()

const { data: screenings, pending, refresh } = await useFetch<ScreeningSummary[]>('/api/screenings')

const canSubmit = computed(() =>
  name.value.trim().length > 0
  && jdText.value.trim().length > 0
  && cvUrls.value.some(u => u.trim().length > 0),
)

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString()
}

function beforeUnloadGuard(e: BeforeUnloadEvent) {
  e.preventDefault()
  e.returnValue = ''
}

watch(loading, (isLoading) => {
  if (import.meta.server) return
  if (isLoading) {
    window.addEventListener('beforeunload', beforeUnloadGuard)
  } else {
    window.removeEventListener('beforeunload', beforeUnloadGuard)
  }
})

onUnmounted(() => {
  if (!import.meta.server) window.removeEventListener('beforeunload', beforeUnloadGuard)
})

async function submit() {
  if (!canSubmit.value) return
  loading.value = true
  error.value = null

  try {
    const res = await $fetch<{ batch: { _id: string } }>('/api/screenings', {
      method: 'POST',
      body: {
        name: name.value.trim(),
        jdText: jdText.value.trim(),
        cvUrls: cvUrls.value.map(u => u.trim()).filter(Boolean),
      },
    })
    await router.push(`/screenings/${res.batch._id}`)
  } catch (e: any) {
    error.value = e?.data?.statusMessage || e?.message || 'Screening failed'
  } finally {
    loading.value = false
  }
}
</script>
