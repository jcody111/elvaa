import type {Product} from './types'

const upstream = (
  process.env.BACKEND_INTERNAL_URL ||
  process.env.API_UPSTREAM ||
  'http://127.0.0.1:8000'
).replace(/\/$/, '')

export async function serverProduct(slug: string): Promise<Product | null> {
  try {
    const url = `${upstream}/api/v1/products/${encodeURIComponent(slug)}/`
    const response = await fetch(url, {cache: 'no-store'})

    if (!response.ok) return null

    return await response.json()
  } catch {
    return null
  }
}
