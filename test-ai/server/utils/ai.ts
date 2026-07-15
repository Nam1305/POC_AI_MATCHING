interface ParseJdResponse {
  parsed_jd: Record<string, any>
  jd_embedding: number[]
  error?: string | null
}

interface ParseCvResult {
  url: string
  cv_raw_text?: string | null
  parsed_cv?: Record<string, any> | null
  cv_embedding?: number[] | null
  error?: string | null
}

interface ParseCvResponse {
  results: ParseCvResult[]
}

interface ScoreResponse {
  final_score: number
  scores: Record<string, number>
  weights_used: Record<string, number>
  evaluation: Record<string, any>
}

function aiBaseUrl(): string {
  return useRuntimeConfig().aiServiceUrl
}

const WEIGHT_DIMENSIONS = ['semantic', 'skills', 'experience', 'education', 'location'] as const

/**
 * Mirrors the ScoreRequest.weights validator in the AI service (app/api/score.py)
 * so bad input is rejected before any parsing/scoring work happens.
 */
export function assertValidWeights(weights: Record<string, number> | null | undefined): void {
  if (weights == null) return

  const keys = Object.keys(weights).sort()
  const expected = [...WEIGHT_DIMENSIONS].sort()
  if (keys.length !== expected.length || keys.some((k, i) => k !== expected[i])) {
    throw createError({
      statusCode: 400,
      statusMessage: `weights must have exactly the keys ${expected.join(', ')}`,
    })
  }

  if (Object.values(weights).some(w => typeof w !== 'number' || w < 0 || w > 1)) {
    throw createError({ statusCode: 400, statusMessage: 'each weight must be between 0 and 1' })
  }

  const total = Object.values(weights).reduce((a, b) => a + b, 0)
  if (Math.abs(total - 1.0) > 1e-6) {
    throw createError({ statusCode: 400, statusMessage: `weights must sum to 1.0, got ${total}` })
  }
}

export async function parseJd(jdText: string): Promise<ParseJdResponse> {
  return $fetch<ParseJdResponse>('/ai/parse-jd', {
    baseURL: aiBaseUrl(),
    method: 'POST',
    body: { jd_text: jdText },
  })
}

export async function parseCvs(cvUrls: string[]): Promise<ParseCvResult[]> {
  const res = await $fetch<ParseCvResponse>('/ai/parse-cv', {
    baseURL: aiBaseUrl(),
    method: 'POST',
    body: { cv_urls: cvUrls },
  })
  return res.results
}

export async function scoreCv(params: {
  parsedCv: Record<string, any>
  parsedJd: Record<string, any>
  cvEmbedding: number[]
  jdEmbedding: number[]
  weights?: Record<string, number> | null
  includeNarrative?: boolean
}): Promise<ScoreResponse> {
  return $fetch<ScoreResponse>('/ai/score', {
    baseURL: aiBaseUrl(),
    method: 'POST',
    body: {
      parsed_cv: params.parsedCv,
      parsed_jd: params.parsedJd,
      cv_embedding: params.cvEmbedding,
      jd_embedding: params.jdEmbedding,
      weights: params.weights ?? null,
      include_narrative: params.includeNarrative ?? false,
    },
  })
}
