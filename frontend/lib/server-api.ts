import type {Product} from './types'

export async function fetchBackend(path: string): Promise<Response | null> {
  // Vercel injects the private binding into functions at runtime.
  const upstream = process.env.BACKEND_INTERNAL_URL
    || process.env.API_UPSTREAM
    || (process.env.VERCEL === '1' ? '' : 'http://127.0.0.1:8000')
  if (!upstream) return null

  try {
    const response = await fetch(`${upstream.replace(/\/+$/, '')}${path}`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(5000),
    })
    return response.ok ? response : null
  } catch {
    return null
  }
}

export async function serverProduct(slug: string): Promise<Product | null> {
  const response = await fetchBackend(`/api/v1/products/${encodeURIComponent(slug)}/`)
  if (!response) return null

  try {
    return await response.json()
  } catch {
    return null
  }
}
