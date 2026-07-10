export default defineEventHandler(async (event) => {
  const body = await readBody(event)

  if (body === undefined || body === null) {
    throw createError({ statusCode: 400, statusMessage: 'Request body must be JSON' })
  }

  const doc = await Document.create({ data: body })

  return doc
})
