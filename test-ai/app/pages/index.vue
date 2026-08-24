<template>
  <div>
    <v-card class="mb-6">
      <v-card-title class="d-flex align-center">
        <v-icon icon="mdi-clipboard-text-search-outline" class="mr-2" />
        New Screening
      </v-card-title>
      <v-card-text>
        <v-form @submit.prevent="submit">
          <v-text-field v-model="name" label="Screening name" placeholder="e.g. Backend Engineer batch #1"
            prepend-inner-icon="mdi-tag-outline" :disabled="loading" required />

          <div class="text-subtitle-2 mb-2 mt-2">Job description</div>

          <v-text-field v-model="jd.title" label="Job title" placeholder="e.g. Backend Engineer"
            prepend-inner-icon="mdi-briefcase-outline" :disabled="loading" required />

          <div class="d-flex flex-wrap ga-4">
            <v-select v-model="jd.workType" :items="workTypeOptions" label="Work type" clearable
              prepend-inner-icon="mdi-domain" style="min-width: 220px" class="flex-1-0" :disabled="loading" />
            <v-text-field v-model="jd.location" label="Location" placeholder="e.g. District 1, Ho Chi Minh City"
              prepend-inner-icon="mdi-map-marker-outline" style="min-width: 220px" class="flex-1-1"
              :disabled="loading" />
          </div>

          <v-select v-model="jd.education" :items="educationOptions" label="Education" multiple chips closable-chips
            prepend-inner-icon="mdi-school-outline" :disabled="loading" />

          <v-text-field v-model="jd.experienceRequirement" label="Experience requirement" placeholder="e.g. 3+ years"
            prepend-inner-icon="mdi-clock-outline" :disabled="loading" />

          <v-autocomplete v-model="jd.requiredSkills" :items="requiredSkillItems" label="Required skills" multiple chips
            closable-chips prepend-inner-icon="mdi-star-outline" placeholder="Type to search and pick skills"
            :disabled="loading" />

          <v-autocomplete v-model="jd.preferredSkills" :items="preferredSkillItems" label="Preferred skills" multiple
            chips closable-chips prepend-inner-icon="mdi-star-half-full" placeholder="Type to search and pick skills"
            :disabled="loading" />

          <v-autocomplete v-model="jd.niceToHave" :items="niceToHaveSkillItems" label="Nice to have skills" multiple
            chips closable-chips prepend-inner-icon="mdi-star-off-outline" placeholder="Type to search and pick skills"
            :disabled="loading" />

          <v-textarea v-model="jd.responsibilities" label="Responsibilities"
            placeholder="Describe the day-to-day responsibilities..." prepend-inner-icon="mdi-format-list-bulleted"
            rows="5" auto-grow :disabled="loading" />

          <v-textarea v-model="jd.requirements" label="Requirements"
            placeholder="Describe the requirements for this role..." prepend-inner-icon="mdi-clipboard-check-outline"
            rows="5" auto-grow :disabled="loading" />

          <v-textarea v-model="jd.benefits" label="Benefits" placeholder="Describe the benefits offered..."
            prepend-inner-icon="mdi-gift-outline" rows="5" auto-grow :disabled="loading" />

          <div class="d-flex justify-end mb-4">
            <v-btn variant="tonal" prepend-icon="mdi-eye-outline" :disabled="loading" @click="previewDialog = true">
              Preview JD text
            </v-btn>
          </div>

          <div class="text-subtitle-2 mb-2">CV URLs</div>

          <template v-if="bulkPasteMode">
            <v-textarea v-model="bulkPasteText" label="Paste CV URLs, one per line"
              placeholder="https://example.com/cv1.pdf&#10;https://example.com/cv2.pdf"
              prepend-inner-icon="mdi-file-pdf-box" rows="6" auto-grow :disabled="loading" />
            <div class="d-flex ga-2 mb-4">
              <v-btn variant="flat" color="primary" prepend-icon="mdi-check" :disabled="loading"
                @click="applyBulkPaste">
                Confirm links
              </v-btn>
              <v-btn variant="text" :disabled="loading" @click="bulkPasteMode = false">
                Cancel
              </v-btn>
            </div>
          </template>

          <template v-else>
            <div v-for="(url, i) in cvUrls" :key="i" class="d-flex align-center mb-1">
              <v-text-field v-model="cvUrls[i]" :label="`CV URL #${i + 1}`" prepend-inner-icon="mdi-file-pdf-box"
                density="comfortable" hide-details :disabled="loading" />
              <v-btn icon="mdi-close" variant="text" class="ml-1" :disabled="loading || cvUrls.length === 1"
                @click="cvUrls.splice(i, 1)" />
            </div>
            <div class="d-flex flex-wrap ga-2 mb-4">
              <v-btn variant="tonal" prepend-icon="mdi-plus" :disabled="loading" @click="cvUrls.push('')">
                Add CV URL
              </v-btn>
              <v-btn variant="tonal" prepend-icon="mdi-content-paste" :disabled="loading" @click="openBulkPaste">
                Paste multiple links
              </v-btn>
            </div>
          </template>

          <div class="text-subtitle-2 mb-2">
            Dimension weights (Wi)
            <span class="text-body-2 ml-2" :class="weightSumValid ? 'text-medium-emphasis' : 'text-error'">
              sum: {{ weightSum.toFixed(2) }} / 1.00
            </span>
          </div>

          <div v-for="dim in weightDims" :key="dim.key" class="mb-2">
            <v-slider v-model="weightPercents[dim.key]" :label="dim.label" min="0" max="100" step="1" thumb-label
              density="compact" :disabled="loading" hide-details>
              <template #append>
                <v-text-field v-model.number="weightPercents[dim.key]" type="number" step="1" min="0" max="100"
                  density="compact" style="width: 90px" hide-details suffix="%" :disabled="loading" />
              </template>
            </v-slider>
          </div>

          <div class="d-flex flex-wrap ga-6 mb-2">
            <v-switch v-model="includeNarrative" label="Include narrative" color="primary" density="compact"
              hide-details :disabled="loading" />
          </div>

          <v-alert v-if="error" type="error" variant="tonal" class="mb-4" closable @click:close="error = null">
            {{ error }}
          </v-alert>

          <v-alert v-if="loading" type="warning" variant="tonal" class="mb-4">
            Screening in progress — this can take a while. Please don't close or reload this tab until it finishes.
          </v-alert>

          <v-btn type="submit" color="primary" size="large" block :loading="loading" :disabled="!canSubmit"
            prepend-icon="mdi-send">
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
        <v-list-item v-for="s in screenings" :key="s._id" :title="s.name"
          :subtitle="`${s.jdTitle ?? 'Untitled JD'} · ${formatDate(s.createdAt)}`"
          @click="$router.push(`/screenings/${s._id}`)">
          <template #prepend>
            <v-avatar color="primary" variant="tonal">
              <v-icon icon="mdi-account-search-outline" />
            </v-avatar>
          </template>
          <template #append>
            <v-chip size="small" variant="tonal" class="mr-2">
              {{ s.candidateCount }} candidate{{ s.candidateCount === 1 ? '' : 's' }}
            </v-chip>
            <v-btn icon="mdi-delete-outline" variant="text" color="error" size="small"
              :loading="deletingId === s._id" @click.stop="confirmDelete(s)" />
          </template>
        </v-list-item>
      </v-list>
      <v-card-text v-else-if="!pending" class="text-medium-emphasis">
        No screenings yet. Run your first one above.
      </v-card-text>
    </v-card>

    <v-dialog v-model="previewDialog" max-width="720">
      <v-card>
        <v-card-title class="d-flex align-center">
          Demo JD Text
          <v-spacer />
          <v-btn icon="mdi-content-copy" variant="text" size="small" @click="copyJdText" />
        </v-card-title>
        <v-card-text>
          <pre class="text-body-2" style="white-space: pre-wrap; font-family: inherit">{{ jdText }}</pre>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="previewDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="jdTextCopied" timeout="2000">
      JD text copied to clipboard
    </v-snackbar>

    <v-dialog v-model="deleteDialog" max-width="480">
      <v-card>
        <v-card-title>Delete screening?</v-card-title>
        <v-card-text>
          This will permanently delete "{{ deleteTarget?.name }}" and all its candidate results. This cannot be
          undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" :disabled="!!deletingId" @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" variant="flat" :loading="!!deletingId" @click="doDelete">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import taxonomiesRaw from '../taxonomies.json'

interface ScreeningSummary {
  _id: string
  name: string
  jdTitle: string | null
  candidateCount: number
  createdAt: string
}

interface JobDescriptionForm {
  title: string
  workType: string | null
  location: string
  education: string[]
  experienceRequirement: string
  requiredSkills: string[]
  preferredSkills: string[]
  niceToHave: string[]
  responsibilities: string
  requirements: string
  benefits: string
}

const workTypeOptions = ['Onsite', 'Remote', 'Hybrid', 'Oversea']

const educationOptions = ['THPT', 'Đại học', 'Cao đẳng', 'Tiến sĩ', 'Thạc sĩ']

// The taxonomy file contains raw, case-inconsistent duplicates. Dedupe by a
// lowercase key (keeping the first casing) and sort so the picker is clean.
const skillOptions = Array.from(
  new Map(
    (taxonomiesRaw as string[])
      .map(skill => skill.trim())
      .filter(Boolean)
      .map(skill => [skill.toLowerCase(), skill] as const),
  ).values(),
).sort((a, b) => a.localeCompare(b))

function buildJdText(f: JobDescriptionForm): string {
  const parts: string[] = []
  if (f.title.trim())
    parts.push(`Job Title: ${f.title.trim()}`)
  if (f.workType)
    parts.push(`Work Type: ${f.workType}`)
  if (f.location.trim())
    parts.push(`Location: ${f.location.trim()}`)
  if (f.education.length > 0)
    parts.push(`Education: ${f.education.join(', ')}`)
  if (f.requiredSkills.length > 0)
    parts.push(`Required Skills: ${f.requiredSkills.join(', ')}`)
  if (f.preferredSkills.length > 0)
    parts.push(`Preferred Skills: ${f.preferredSkills.join(', ')}`)
  if (f.niceToHave.length > 0)
    parts.push(`Nice to Have Skills: ${f.niceToHave.join(', ')}`)
  if (f.experienceRequirement.trim())
    parts.push(`Experience Requirement: ${f.experienceRequirement.trim()}`)
  if (f.responsibilities.trim())
    parts.push(`Responsibilities:\n${f.responsibilities.trim()}`)
  if (f.requirements.trim())
    parts.push(`Requirements:\n${f.requirements.trim()}`)
  if (f.benefits.trim())
    parts.push(`Benefits:\n${f.benefits.trim()}`)
  return parts.join('\n\n')
}

const DEFAULT_WEIGHTS: Record<string, number> = {
  semantic: 0.30,
  skills: 0.35,
  experience: 0.20,
  education: 0.10,
  location: 0.05,
}

const weightDims = [
  { key: 'semantic', label: 'Semantic' },
  { key: 'skills', label: 'Skills' },
  { key: 'experience', label: 'Experience' },
  { key: 'education', label: 'Education' },
  { key: 'location', label: 'Location' },
] as const

const name = ref('')
const jd = reactive<JobDescriptionForm>({
  title: '',
  workType: null,
  location: '',
  education: [],
  experienceRequirement: '',
  requiredSkills: [],
  preferredSkills: [],
  niceToHave: [],
  responsibilities: '',
  requirements: '',
  benefits: '',
})

const requiredSkillItems = computed(() =>
  skillOptions.filter(s => !jd.preferredSkills.includes(s) && !jd.niceToHave.includes(s)),
)
const preferredSkillItems = computed(() =>
  skillOptions.filter(s => !jd.requiredSkills.includes(s) && !jd.niceToHave.includes(s)),
)
const niceToHaveSkillItems = computed(() =>
  skillOptions.filter(s => !jd.requiredSkills.includes(s) && !jd.preferredSkills.includes(s)),
)

const jdText = computed(() => buildJdText(jd))
const previewDialog = ref(false)
const jdTextCopied = ref(false)

async function copyJdText() {
  await navigator.clipboard.writeText(jdText.value)
  jdTextCopied.value = true
}

const cvUrls = ref<string[]>([''])
const bulkPasteMode = ref(false)
const bulkPasteText = ref('')
const weights = reactive<Record<string, number>>({ ...DEFAULT_WEIGHTS })
const weightPercents = reactive<Record<string, number>>(
  Object.fromEntries(weightDims.map(d => [d.key, Math.round((DEFAULT_WEIGHTS[d.key] ?? 0) * 100)])),
)
watch(weightPercents, (v) => {
  for (const dim of weightDims) weights[dim.key] = (v[dim.key] ?? 0) / 100
}, { deep: true })
const includeNarrative = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)

const deleteDialog = ref(false)
const deleteTarget = ref<ScreeningSummary | null>(null)
const deletingId = ref<string | null>(null)

const router = useRouter()

const { data: screenings, pending, refresh } = await useFetch<ScreeningSummary[]>('/api/screenings')

const weightSum = computed(() =>
  weightDims.reduce((sum, d) => sum + (Number(weights[d.key]) || 0), 0),
)
const weightSumValid = computed(() => Math.abs(weightSum.value - 1.0) < 1e-6)

const canSubmit = computed(() =>
  name.value.trim().length > 0
  && jd.title.trim().length > 0
  && cvUrls.value.some(u => u.trim().length > 0)
  && weightSumValid.value,
)

function openBulkPaste() {
  bulkPasteText.value = cvUrls.value.filter(u => u.trim().length > 0).join('\n')
  bulkPasteMode.value = true
}

function applyBulkPaste() {
  const urls = bulkPasteText.value
    .split('\n')
    .map(u => u.trim())
    .filter(Boolean)
  cvUrls.value = urls.length > 0 ? urls : ['']
  bulkPasteMode.value = false
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString()
}

function confirmDelete(s: ScreeningSummary) {
  deleteTarget.value = s
  deleteDialog.value = true
}

async function doDelete() {
  if (!deleteTarget.value) return
  deletingId.value = deleteTarget.value._id
  try {
    await $fetch(`/api/screenings/${deleteTarget.value._id}`, { method: 'DELETE' })
    deleteDialog.value = false
    await refresh()
  } catch (e: any) {
    error.value = e?.data?.statusMessage || e?.message || 'Failed to delete screening'
  } finally {
    deletingId.value = null
    deleteTarget.value = null
  }
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
        weights: { ...weights },
        includeNarrative: includeNarrative.value,
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
