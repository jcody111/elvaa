import type {MetadataRoute} from 'next'
export default async function sitemap():Promise<MetadataRoute.Sitemap>{
 const site=(process.env.NEXT_PUBLIC_SITE_URL||'https://example.com').replace(/\/$/,'')
 const paths=['','/shop','/about','/journal','/contact','/faq','/shipping','/privacy','/terms']
 let products:string[]=[]
 try{const base=(process.env.API_UPSTREAM||'http://127.0.0.1:8000').replace(/\/$/,'');const r=await fetch(`${base}/api/v1/products/`,{next:{revalidate:3600}});if(r.ok){const d=await r.json();products=d.results.map((p:{slug:string})=>`/product/${p.slug}`)}}catch{}
 return [...paths,...products].map(path=>({url:`${site}${path}`,lastModified:new Date()}))
}
