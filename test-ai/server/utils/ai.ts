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
  penalty_applied: number
  penalty_reasons: string[]
  evaluation: Record<string, any>
}

function aiBaseUrl(): string {
  return useRuntimeConfig().aiServiceUrl
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
}): Promise<ScoreResponse> {
  return $fetch<ScoreResponse>('/ai/score', {
    baseURL: aiBaseUrl(),
    method: 'POST',
    body: {
      parsed_cv: params.parsedCv,
      parsed_jd: params.parsedJd,
      cv_embedding: params.cvEmbedding,
      jd_embedding: params.jdEmbedding,
    },
  })
}
