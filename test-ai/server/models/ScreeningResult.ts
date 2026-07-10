import { defineMongooseModel } from '#nuxt/mongoose'

export const ScreeningResult = defineMongooseModel({
  name: 'ScreeningResult',
  schema: {
    batchId: {
      type: 'ObjectId',
      ref: 'ScreeningBatch',
      required: true,
    },
    cvUrl: {
      type: 'String',
      required: true,
    },
    parsedCv: {
      type: 'Mixed',
    },
    cvEmbedding: {
      type: ['Number'],
    },
    aiResult: {
      type: 'Mixed',
    },
    error: {
      type: 'String',
    },
  },
  options: {
    timestamps: true,
  },
})
