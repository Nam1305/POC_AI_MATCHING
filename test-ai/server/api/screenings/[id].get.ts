export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')

  const batch = await ScreeningBatch.findById(id).populate('jobDescriptionId').lean()
  if (!batch) {
    throw createError({ statusCode: 404, statusMessage: 'Screening batch not found' })
  }

  const results = await ScreeningResult.find({ batchId: id }).lean()
  results.sort((a, b) => (b.aiResult?.final_score ?? -1) - (a.aiResult?.final_score ?? -1))

  return {
    _id: batch._id,
    name: batch.name,
    createdAt: batch.createdAt,
    jobDescription: batch.jobDescriptionId,
    results,
  }
})
