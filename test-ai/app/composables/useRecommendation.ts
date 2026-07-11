export function recommendationColor(recommendation?: string | null): string {
  const rec = (recommendation ?? '').toUpperCase()
  if (rec.includes('STRONG') || rec.includes('EXCELLENT')) return 'success'
  if (rec.includes('POSSIBLE') || rec.includes('GOOD')) return 'warning'
  if (rec.includes('POOR') || rec.includes('NOT') || rec.includes('REJECT')) return 'error'
  return 'default'
}

export function recommendationLabel(recommendation?: string | null): string {
  if (!recommendation) return 'Unknown'
  return recommendation
    .split('_')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

export function cvFileName(url: string): string {
  try {
    return decodeURIComponent(url.split('/').pop() || url)
  } catch {
    return url
  }
}
