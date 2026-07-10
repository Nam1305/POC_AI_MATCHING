import { defineMongooseModel } from '#nuxt/mongoose'

export const JobDescription = defineMongooseModel({
  name: 'JobDescription',
  schema: {
    jdText: {
      type: 'String',
      required: true,
    },
    parsedJd: {
      type: 'Mixed',
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
