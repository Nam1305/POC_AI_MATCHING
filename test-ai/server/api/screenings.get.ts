export default defineEventHandler(async () => {
  const batches = await ScreeningBatch.find()
    .populate({ path: 'jobDescriptionId', select: 'parsedJd.title' })
    .sort({ createdAt: -1 })
    .lean()

  const counts = await ScreeningResult.aggregate([
    { $match: { batchId: { $in: batches.map(b => b._id) } } },
    { $group: { _id: '$batchId', count: { $sum: 1 } } },
  ])
  const countByBatch = new Map(counts.map(c => [String(c._id), c.count]))

  return batches.map(b => ({
    _id: b._id,
    name: b.name,
    jdTitle: (b.jobDescriptionId as any)?.parsedJd?.title ?? null,
    candidateCount: countByBatch.get(String(b._id)) ?? 0,
    createdAt: b.createdAt,
  }))
})
