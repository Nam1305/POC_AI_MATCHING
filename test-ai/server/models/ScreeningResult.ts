import { defineMongooseModel } from '#nuxt/mongoose'
import { Schema, Types } from 'mongoose'

export interface IScreeningResult {
  batchId: Types.ObjectId
  cvUrl: string
  order: number
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
    // Position of this CV in the user's original cvUrls input — preserved on
    // read so candidates keep the order the user entered them in, rather
    // than being re-sorted by score.
    order: {
      type: 'Number',
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
