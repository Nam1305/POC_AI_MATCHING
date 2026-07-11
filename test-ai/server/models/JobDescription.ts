import { defineMongooseModel } from '#nuxt/mongoose'
import { Schema } from 'mongoose'

export interface IJobDescription {
  jdText: string
  parsedJd: unknown
  jdEmbedding: number[]
  createdAt: Date
  updatedAt: Date
}

export const JobDescription = defineMongooseModel<IJobDescription>({
  name: 'JobDescription',
  schema: {
    jdText: {
      type: 'String',
      required: true,
    },
    parsedJd: {
      type: Schema.Types.Mixed,
      required: true,
    },
    jdEmbedding: {
      type: ['Number'],
      required: true,
    },
  },
  options: {
    timestamps: true,
  },
})
