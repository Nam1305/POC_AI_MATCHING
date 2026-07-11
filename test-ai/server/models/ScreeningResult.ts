import { defineMongooseModel } from '#nuxt/mongoose'
import { Schema, Types } from 'mongoose'

export interface IScreeningResult {
  batchId: Types.ObjectId
  cvUrl: string
  parsedCv?: unknown
  cvEmbedding?: number[]
  aiResult?: unknown
  error?: string
  createdAt: Date
  updatedAt: Date
}

export const ScreeningResult = defineMongooseModel<IScreeningResult>({
  name: 'ScreeningResult',
  schema: {
    batchId: {
      type: Schema.Types.ObjectId,
      ref: 'ScreeningBatch',
      required: true,
    },
    cvUrl: {
      type: 'String',
      required: true,
    },
    parsedCv: {
      type: Schema.Types.Mixed,
    },
    cvEmbedding: {
      type: ['Number'],
    },
    aiResult: {
      type: Schema.Types.Mixed,
    },
    error: {
      type: 'String',
    },
  },
  options: {
    timestamps: true,
  },
})
