import { timingSafeEqual } from 'node:crypto'

function safeEqual(a: string, b: string): boolean {
  const bufA = Buffer.from(a)
  const bufB = Buffer.from(b)
  if (bufA.length !== bufB.length) return false
  return timingSafeEqual(bufA, bufB)
}

export default defineEventHandler((event) => {
  const config = useRuntimeConfig()
  if (!config.authUsername || !config.authPassword) return

  const header = getHeader(event, 'authorization')
  if (header?.startsWith('Basic ')) {
    const decoded = Buffer.from(header.slice(6), 'base64').toString('utf-8')
    const sepIndex = decoded.indexOf(':')
    const user = decoded.slice(0, sepIndex)
    const pass = decoded.slice(sepIndex + 1)
    if (safeEqual(user, config.authUsername) && safeEqual(pass, config.authPassword)) {
      return
    }
  }

  setResponseHeader(event, 'WWW-Authenticate', 'Basic realm="Restricted", charset="UTF-8"')
  throw createError({ statusCode: 401, statusMessage: 'Authentication required' })
})
