import { defineMongooseModel } from '#nuxt/mongoose'

export const ScreeningBatch = defineMongooseModel({
  name: 'ScreeningBatch',
  schema: {
    name: {
      type: 'String',
      required: true,
      trim: true,
    },
    jobDescriptionId: {
      type: 'ObjectId',
      ref: 'JobDescription',
      required: true,
    },
    weights: {
      type: 'Mixed',
      required: false,
    },
  },
  options: {
    timestamps: true,
  },
})
