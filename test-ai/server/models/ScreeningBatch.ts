import { defineMongooseModel } from '#nuxt/mongoose'
import { Schema, Types } from 'mongoose'

export interface IScreeningBatch {
  name: string
  jobDescriptionId: Types.ObjectId
  weights?: unknown
  enforcePenalty: boolean
  includeNarrative: boolean
  createdAt: Date
  updatedAt: Date
}

export const ScreeningBatch = defineMongooseModel<IScreeningBatch>({
  name: 'ScreeningBatch',
  schema: {
    name: {
      type: 'String',
      required: true,
      trim: true,
    },
    jobDescriptionId: {
      type: Schema.Types.ObjectId,
      ref: 'JobDescription',
      required: true,
    },
    weights: {
      type: Schema.Types.Mixed,
      required: false,
    },
    enforcePenalty: {
      type: 'Boolean',
      required: true,
      default: true,
    },
    includeNarrative: {
      type: 'Boolean',
      required: true,
      default: false,
    },
  },
  options: {
    timestamps: true,
  },
})
