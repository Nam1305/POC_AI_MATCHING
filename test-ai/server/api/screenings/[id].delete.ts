export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')

  const batch = await ScreeningBatch.findById(id).lean()
  if (!batch) {
    throw createError({ statusCode: 404, statusMessage: 'Screening batch not found' })
  }

  await ScreeningResult.deleteMany({ batchId: id })
  await ScreeningBatch.findByIdAndDelete(id)

  return { success: true }
})
