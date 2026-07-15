export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  const body = await readBody<{
    name?: string
    weights?: Record<string, number> | null
    enforcePenalty?: boolean
    includeNarrative?: boolean
  }>(event)

  if (body && 'weights' in body) {
    assertValidWeights(body.weights)
  }

  const update: Record<string, any> = {}
  if (body?.name?.trim()) update.name = body.name.trim()
  if (body && 'weights' in body) update.weights = body.weights ?? null
  if (body && 'enforcePenalty' in body) update.enforcePenalty = body.enforcePenalty ?? true
  if (body && 'includeNarrative' in body) update.includeNarrative = body.includeNarrative ?? false

  const batch = await ScreeningBatch.findByIdAndUpdate(id, update, { new: true }).lean() as any
  if (!batch) {
    throw createError({ statusCode: 404, statusMessage: 'Screening batch not found' })
  }

  const jobDescription = await JobDescription.findById(batch.jobDescriptionId).lean() as any
  if (!jobDescription) {
    throw createError({ statusCode: 404, statusMessage: 'Job description not found for this batch' })
  }

  const results = await ScreeningResult.find({ batchId: id }).lean() as any[]

  for (const result of results) {
    if (result.error) continue

    let parsedCv = result.parsedCv
    let cvEmbedding = result.cvEmbedding

    // Results scored before cvEmbedding was persisted have no embedding to
    // re-score with — re-parse the CV from its stored URL to get one.
    if (!parsedCv || !cvEmbedding?.length) {
      const [reparsed] = await parseCvs([result.cvUrl])
      if (reparsed?.error || !reparsed?.parsed_cv || !reparsed?.cv_embedding) continue
      parsedCv = reparsed.parsed_cv
      cvEmbedding = reparsed.cv_embedding
    }

    const aiResult = await scoreCv({
      parsedCv,
      parsedJd: jobDescription.parsedJd,
      cvEmbedding,
      jdEmbedding: jobDescription.jdEmbedding,
      weights: batch.weights ?? undefined,
      enforcePenalty: batch.enforcePenalty,
      includeNarrative: batch.includeNarrative,
    })

    await ScreeningResult.findByIdAndUpdate(result._id, { parsedCv, cvEmbedding, aiResult })
  }

  const updatedResults = await ScreeningResult.find({ batchId: id }).lean() as any[]
  updatedResults.sort((a, b) => (b.aiResult?.final_score ?? -1) - (a.aiResult?.final_score ?? -1))

  return {
    _id: batch._id,
    name: batch.name,
    weights: batch.weights ?? null,
    enforcePenalty: batch.enforcePenalty,
    includeNarrative: batch.includeNarrative,
    createdAt: batch.createdAt,
    jobDescription,
    results: updatedResults,
  }
})
