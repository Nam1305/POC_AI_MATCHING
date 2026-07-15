export default defineEventHandler(async (event) => {
  const body = await readBody<{
    name?: string
    jdText?: string
    cvUrls?: string[]
    weights?: Record<string, number> | null
    includeNarrative?: boolean
  }>(event)

  if (!body?.name?.trim()) {
    throw createError({ statusCode: 400, statusMessage: 'name is required' })
  }
  if (!body?.jdText?.trim()) {
    throw createError({ statusCode: 400, statusMessage: 'jdText is required' })
  }
  if (!body?.cvUrls?.length) {
    throw createError({ statusCode: 400, statusMessage: 'cvUrls must be a non-empty array' })
  }
  assertValidWeights(body.weights)

  const { parsed_jd: parsedJd, jd_embedding: jdEmbedding } = await parseJd(body.jdText)

  const jobDescription = await JobDescription.create({
    jdText: body.jdText,
    parsedJd,
    jdEmbedding,
  })

  const batch = await ScreeningBatch.create({
    name: body.name,
    jobDescriptionId: jobDescription._id,
    weights: body.weights ?? undefined,
    includeNarrative: body.includeNarrative ?? false,
  })

  const cvResults = await parseCvs(body.cvUrls)

  const results = []
  for (const cv of cvResults) {
    if (cv.error || !cv.parsed_cv || !cv.cv_embedding) {
      results.push(await ScreeningResult.create({
        batchId: batch._id,
        cvUrl: cv.url,
        error: cv.error || 'CV parsing failed',
      }))
      continue
    }

    const aiResult = await scoreCv({
      parsedCv: cv.parsed_cv,
      parsedJd,
      cvEmbedding: cv.cv_embedding,
      jdEmbedding,
      weights: body.weights,
      includeNarrative: batch.includeNarrative,
    })

    const saved = await ScreeningResult.create({
      batchId: batch._id,
      cvUrl: cv.url,
      parsedCv: cv.parsed_cv,
      cvEmbedding: cv.cv_embedding,
      aiResult,
    })

    results.push(saved)
  }

  return { batch, jobDescription, results }
})
