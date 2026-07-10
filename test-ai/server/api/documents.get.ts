export default defineEventHandler(async () => {
  return Document.find().sort({ createdAt: -1 })
})
