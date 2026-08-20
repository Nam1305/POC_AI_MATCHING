export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')

  const batch = await ScreeningBatch.findById(id).populate('jobDescriptionId').lean()
  if (!batch) {
    throw createError({ statusCode: 404, statusMessage: 'Screening batch not found' })
  }

  const results = await ScreeningResult.find({ batchId: id }).sort({ order: 1 }).lean()

  return {
    _id: batch._id,
    name: batch.name,
    weights: batch.weights ?? null,
    createdAt: batch.createdAt,
    jobDescription: batch.jobDescriptionId,
    results,
  }
})
