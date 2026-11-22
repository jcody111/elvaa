import type {MetadataRoute} from 'next'
export default function robots():MetadataRoute.Robots{const site=(process.env.NEXT_PUBLIC_SITE_URL||'https://example.com').replace(/\/$/,'');return {rules:{userAgent:'*',allow:'/',disallow:['/admin/','/account/','/checkout/']},sitemap:`${site}/sitemap.xml`}}
