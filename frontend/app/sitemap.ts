import type {MetadataRoute} from 'next'
import {fetchBackend} from '@/lib/server-api'
import {siteUrl} from '@/lib/site-url'
import type {Page, Product} from '@/lib/types'

export const dynamic = 'force-dynamic'

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const paths = ['', '/shop', '/about', '/journal', '/contact', '/faq', '/shipping', '/privacy', '/terms']
  const response = await fetchBackend('/api/v1/products/')
  const data: Page<Product> | null = await response?.json().catch(() => null) ?? null
  if (Array.isArray(data?.results)) {
    paths.push(...data.results.map(({slug}) => `/product/${encodeURIComponent(slug)}`))
  }
  return paths.map(path => ({url: `${siteUrl}${path}`, lastModified: new Date()}))
}
