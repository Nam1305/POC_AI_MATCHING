export function cvFileName(url: string): string {
  try {
    return decodeURIComponent(url.split('/').pop() || url)
  } catch {
    return url
  }
}
