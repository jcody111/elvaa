import Link from 'next/link'
import {notFound} from 'next/navigation'
import {articles} from '@/lib/journal'
type Props={params:Promise<{slug:string}>}
export async function generateMetadata({params}:Props){const {slug}=await params;const a=articles.find(x=>x.slug===slug);return {title:a?.title||'Journal',description:a?.excerpt}}
export default async function Article({params}:Props){const {slug}=await params;const a=articles.find(x=>x.slug===slug);if(!a)notFound();return <><div className="article-hero"><img src={a.image} alt=""/></div><article className="content-page"><Link href="/journal" className="text-link">← BACK TO THE JOURNAL</Link><span className="eyebrow" style={{marginTop:40}}>{a.category}</span><h1>{a.title}</h1>{a.body.map(p=><p key={p}>{p}</p>)}</article></>}
