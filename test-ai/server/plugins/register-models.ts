import { JobDescription } from '../models/JobDescription'
import { ScreeningBatch } from '../models/ScreeningBatch'
import { ScreeningResult } from '../models/ScreeningResult'

export default defineNitroPlugin(() => {
  void JobDescription
  void ScreeningBatch
  void ScreeningResult
})
