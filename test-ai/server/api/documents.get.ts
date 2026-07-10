import { Document } from '~~/server/models/Document'

export default defineEventHandler(async () => {
  return Document.find().sort({ createdAt: -1 })
})
