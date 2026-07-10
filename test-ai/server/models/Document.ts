import { defineMongooseModel } from '#nuxt/mongoose'
import { Schema } from 'mongoose'

export interface IDocument {
  data: unknown
  createdAt: Date
  updatedAt: Date
}

export const Document = defineMongooseModel<IDocument>({
  name: 'Document',
  schema: {
    data: {
      type: Schema.Types.Mixed,
      required: true,
    },
  },
  options: {
    timestamps: true,
  },
})
