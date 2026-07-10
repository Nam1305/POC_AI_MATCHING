<template>
  <div>
    <v-btn variant="text" prepend-icon="mdi-arrow-left" class="mb-2" to="/">
      Back to screenings
    </v-btn>

    <v-skeleton-loader v-if="pending" type="article, table, article" />

    <v-alert v-else-if="error" type="error" variant="tonal">
      {{ error?.data?.statusMessage || 'Failed to load screening' }}
    </v-alert>

    <template v-else-if="screening">
      <v-card class="mb-6">
        <v-card-title class="d-flex align-center flex-wrap">
          <v-icon icon="mdi-briefcase-search-outline" class="mr-2" />
          {{ screening.name }}
          <v-spacer />
          <span class="text-body-2 text-medium-emphasis mr-3">{{ formatDate(screening.createdAt) }}</span>
          <v-btn variant="tonal" size="small" prepend-icon="mdi-cog-outline" @click="openDetailsDialog">
            View Screening Details
          </v-btn>
        </v-card-title>
        <v-card-text>
          <div class="text-h6 mb-2">{{ jd.title }}</div>

          <div class="d-flex flex-wrap ga-2 mb-3">
            <v-chip v-for="s in jd.required_skills" :key="'req-' + s.skill" size="small" color="primary"
              variant="tonal">
              {{ s.skill }} <span v-if="s.weight >= 3" class="ml-1">(must-have)</span>
            </v-chip>
            <v-chip v-for="s in jd.preferred_skills" :key="'pref-' + s" size="small" variant="outlined">
              {{ s }}
            </v-chip>
          </div>

          <div class="d-flex flex-wrap ga-4 text-body-2 text-medium-emphasis mb-3">
            <span><v-icon icon="mdi-clock-outline" size="16" class="mr-1" />{{ jd.min_experience_years }}+ yrs
              experience</span>
            <span v-if="jd.education_degree"><v-icon icon="mdi-school-outline" size="16" class="mr-1" />{{
              jd.education_degree }}</span>
            <span>
              <v-icon icon="mdi-map-marker-outline" size="16" class="mr-1" />
              {{ jd.work_location?.raw_address || jd.work_location?.city }} · {{ jd.work_location?.work_mode }}
            </span>
          </div>

          <div class="d-flex flex-column ga-2">
            <JsonViewer :data="jd" label="Parsed JD JSON" />
            <JsonViewer :data="screening.jobDescription.jdText" label="Raw JD Text" raw />
          </div>
        </v-card-text>
      </v-card>

      <v-card v-if="failed.length" class="mb-6" color="error" variant="tonal">
        <v-card-text>
          <div class="font-weight-medium mb-1">{{ failed.length }} CV(s) failed to process</div>
          <div v-for="f in failed" :key="f._id" class="text-body-2">
            {{ cvFileName(f.cvUrl) }} — {{ f.error }}
          </div>
        </v-card-text>
      </v-card>

      <v-card class="mb-6">
        <v-card-title>Candidate Summary</v-card-title>
        <v-table>
          <thead>
            <tr>
              <th>#</th>
              <th>CV</th>
              <th class="text-right">Final</th>
              <th class="text-right">Skills</th>
              <th class="text-right">Exp</th>
              <th class="text-right">Edu</th>
              <th class="text-right">Semantic</th>
              <th class="text-right">Location</th>
              <th>Recommendation</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(r, i) in scored" :key="r._id" class="cursor-pointer" @click="scrollTo(r._id)">
              <td>{{ i + 1 }}</td>
              <td>{{ cvFileName(r.cvUrl) }}</td>
              <td class="text-right font-weight-medium">{{ r.aiResult.final_score.toFixed(1) }}</td>
              <td class="text-right">{{ r.aiResult.scores.skills?.toFixed(1) }}</td>
              <td class="text-right">{{ r.aiResult.scores.experience?.toFixed(1) }}</td>
              <td class="text-right">{{ r.aiResult.scores.education?.toFixed(1) }}</td>
              <td class="text-right">{{ r.aiResult.scores.semantic?.toFixed(1) }}</td>
              <td class="text-right">{{ r.aiResult.scores.location?.toFixed(1) }}</td>
              <td>
                <v-chip :color="recommendationColor(r.aiResult.evaluation.recommendation)" size="small" variant="flat">
                  {{ recommendationLabel(r.aiResult.evaluation.recommendation) }}
                </v-chip>
              </td>
            </tr>
          </tbody>
        </v-table>
      </v-card>

      <v-expansion-panels v-model="openPanels" multiple variant="accordion">
        <v-expansion-panel v-for="(r, i) in scored" :id="`candidate-${r._id}`" :key="r._id" :value="r._id">
          <v-expansion-panel-title>
            <div class="d-flex align-center ga-3 w-100">
              <v-avatar color="primary" size="32">
                <span class="text-body-2">#{{ i + 1 }}</span>
              </v-avatar>
              <div class="flex-grow-1">
                <div class="font-weight-medium">{{ r.parsedCv.name || cvFileName(r.cvUrl) }}</div>
                <div class="text-caption text-medium-emphasis">{{ cvFileName(r.cvUrl) }}</div>
              </div>
              <v-chip :color="recommendationColor(r.aiResult.evaluation.recommendation)" variant="flat">
                {{ r.aiResult.final_score.toFixed(1) }} · {{ recommendationLabel(r.aiResult.evaluation.recommendation)
                }}
              </v-chip>
            </div>
          </v-expansion-panel-title>

          <v-expansion-panel-text>
            <v-row>
              <v-col cols="12" md="6">
                <div class="text-subtitle-2 mb-2">Scores</div>
                <div v-for="m in metrics(r)" :key="m.label" class="mb-2">
                  <div class="d-flex justify-space-between text-body-2 mb-1">
                    <span>{{ m.label }}</span>
                    <span>{{ m.value.toFixed(1) }}</span>
                  </div>
                  <v-progress-linear :model-value="m.value" height="8" rounded color="primary" />
                </div>
              </v-col>

              <v-col cols="12" md="6">
                <div class="text-subtitle-2 mb-2">Location</div>
                <div class="text-body-2 mb-1">
                  <strong>JD:</strong>
                  {{ jd.work_location?.raw_address || jd.work_location?.city }} ({{ jd.work_location?.work_mode }})
                </div>
                <div class="text-body-2 mb-3">
                  <strong>CV:</strong>
                  {{ r.parsedCv.candidate_location?.raw_address || 'not stated' }}
                  <span v-if="r.parsedCv.candidate_location?.willing_to_relocate !== null">
                    · relocate: {{ r.parsedCv.candidate_location?.willing_to_relocate }}
                  </span>
                </div>

                <div class="text-subtitle-2 mb-2">Verdict</div>
                <div class="text-body-2">
                  <strong>Experience:</strong> {{ r.aiResult.evaluation.experience_verdict }} — {{
                    r.aiResult.evaluation.experience_detail }}
                </div>
                <div class="text-body-2">
                  <strong>Education:</strong> {{ r.aiResult.evaluation.education_verdict }}
                </div>
                <div class="text-body-2 mb-3">
                  <strong>Seniority:</strong> {{ r.aiResult.evaluation.seniority_match }} — {{
                    r.aiResult.evaluation.seniority_detail }}
                </div>
              </v-col>
            </v-row>

            <v-divider class="my-3" />

            <div class="mb-3">
              <div class="text-subtitle-2 mb-1">Skill match rate: {{ r.aiResult.evaluation.skill_match_rate }}%</div>
              <div v-if="r.aiResult.evaluation.missing_must_have?.length" class="mb-1">
                <v-chip v-for="s in r.aiResult.evaluation.missing_must_have" :key="s" size="small" color="error"
                  variant="tonal" class="mr-1 mb-1">
                  missing: {{ s }}
                </v-chip>
              </div>
              <div v-if="r.aiResult.evaluation.missing_preferred?.length" class="mb-1">
                <v-chip v-for="s in r.aiResult.evaluation.missing_preferred" :key="s" size="small" variant="outlined"
                  class="mr-1 mb-1">
                  preferred: {{ s }}
                </v-chip>
              </div>
              <div v-if="r.aiResult.evaluation.bonus_skills?.length">
                <v-chip v-for="s in r.aiResult.evaluation.bonus_skills" :key="s" size="small" color="success"
                  variant="tonal" class="mr-1 mb-1">
                  bonus: {{ s }}
                </v-chip>
              </div>
            </div>

            <div class="text-subtitle-2 mb-1">Narrative</div>
            <p class="text-body-2 mb-3" style="white-space: pre-line">{{ r.aiResult.evaluation.narrative }}</p>

            <div class="d-flex flex-wrap align-center ga-2">
              <JsonViewer :data="r.parsedCv" label="Parsed CV JSON" />
              <a :href="r.cvUrl" target="_blank" rel="noopener noreferrer" class="text-body-2">
                <v-icon icon="mdi-open-in-new" size="16" class="mr-1" />CV URL
              </a>
            </div>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </template>

    <v-dialog v-model="detailsDialog" max-width="560" persistent>
      <v-card>
        <v-card-title>Screening Details</v-card-title>
        <v-card-text>
          <v-text-field v-model="editName" label="Screening name" prepend-inner-icon="mdi-tag-outline"
            :disabled="rerunning" required />

          <div class="text-subtitle-2 mt-2 mb-1">
            Dimension weights (Wi)
            <span class="text-body-2 ml-2" :class="weightSumValid ? 'text-medium-emphasis' : 'text-error'">
              sum: {{ weightSum.toFixed(2) }} / 1.00
            </span>
          </div>

          <v-row comfortable>
            <v-col v-for="dim in weightDims" :key="dim.key" cols="6">
              <v-text-field v-model.number="editWeights[dim.key]" :label="dim.label" type="number" step="0.01" min="0"
                max="1" density="compact" :disabled="rerunning" />
            </v-col>
          </v-row>

          <v-alert v-if="dialogError" type="error" variant="tonal" class="mt-2" closable
            @click:close="dialogError = null">
            {{ dialogError }}
          </v-alert>

          <v-alert v-if="rerunning" type="warning" variant="tonal" class="mt-2">
            Re-running screening — this can take a while.
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" :disabled="rerunning" @click="detailsDialog = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" prepend-icon="mdi-refresh" :loading="rerunning"
            :disabled="!weightSumValid || !editName.trim()" @click="saveAndRerun">
            Save &amp; Re-run
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
interface ScreeningResultItem {
  _id: string
  cvUrl: string
  parsedCv?: any
  aiResult?: any
  error?: string
  createdAt: string
}

interface ScreeningDetail {
  _id: string
  name: string
  weights: Record<string, number> | null
  createdAt: string
  jobDescription: { jdText: string, parsedJd: any }
  results: ScreeningResultItem[]
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

const route = useRoute()
const { data: screening, pending, error, refresh } = await useFetch<ScreeningDetail>(`/api/screenings/${route.params.id}`)

const detailsDialog = ref(false)
const editName = ref('')
const editWeights = reactive<Record<string, number>>({ ...DEFAULT_WEIGHTS })
const rerunning = ref(false)
const dialogError = ref<string | null>(null)

const weightSum = computed(() =>
  weightDims.reduce((sum, d) => sum + (Number(editWeights[d.key]) || 0), 0),
)
const weightSumValid = computed(() => Math.abs(weightSum.value - 1.0) < 1e-6)

function openDetailsDialog() {
  editName.value = screening.value?.name ?? ''
  const current = screening.value?.weights ?? DEFAULT_WEIGHTS
  for (const dim of weightDims) editWeights[dim.key] = current[dim.key] ?? DEFAULT_WEIGHTS[dim.key] ?? 0
  dialogError.value = null
  detailsDialog.value = true
}

async function saveAndRerun() {
  if (!weightSumValid.value || !editName.value.trim()) return
  rerunning.value = true
  dialogError.value = null

  try {
    await $fetch(`/api/screenings/${route.params.id}`, {
      method: 'PATCH',
      body: {
        name: editName.value.trim(),
        weights: { ...editWeights },
      },
    })
    await refresh()
    detailsDialog.value = false
  } catch (e: any) {
    dialogError.value = e?.data?.statusMessage || e?.message || 'Failed to re-run screening'
  } finally {
    rerunning.value = false
  }
}

const jd = computed(() => screening.value?.jobDescription?.parsedJd ?? {})
const scored = computed(() => (screening.value?.results ?? []).filter(r => r.aiResult))
const failed = computed(() => (screening.value?.results ?? []).filter(r => !r.aiResult))
const openPanels = ref<string[]>([])

function metrics(r: ScreeningResultItem) {
  return [
    { label: 'Skills', value: r.aiResult.scores.skills ?? 0 },
    { label: 'Experience', value: r.aiResult.scores.experience ?? 0 },
    { label: 'Education', value: r.aiResult.scores.education ?? 0 },
    { label: 'Semantic', value: r.aiResult.scores.semantic ?? 0 },
    { label: 'Location', value: r.aiResult.scores.location ?? 0 },
  ]
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString()
}

function scrollTo(id: string) {
  if (!openPanels.value.includes(id)) openPanels.value.push(id)
  nextTick(() => {
    document.getElementById(`candidate-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}
</script>
