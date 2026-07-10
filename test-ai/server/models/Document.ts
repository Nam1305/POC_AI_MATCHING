import { defineMongooseModel } from '#nuxt/mongoose'

export const Document = defineMongooseModel({
  name: 'Document',
  schema: {
    data: {
      type: 'Mixed',
      required: true,
    },
  },
  options: {
    timestamps: true,
  },
})
