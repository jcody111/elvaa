import Link from 'next/link'
import {ArrowRight} from 'lucide-react'
import {articles} from '@/lib/journal'
export const metadata={title:'The Journal'}
export default function Journal(){return <div className="page-width dashboard-wrap"><div className="page-heading"><span className="eyebrow">THE ELVAA JOURNAL</span><h1>A moment to slow down.</h1><p>Notes on style, intention and the beauty in the everyday.</p></div><div className="journal-grid">{articles.map(a=><article key={a.slug}><Link href={`/journal/${a.slug}`}><img src={a.image} alt=""/><span className="eyebrow">{a.category}</span><h2>{a.title}</h2><p>{a.excerpt}</p><span className="text-link">READ THE STORY <ArrowRight size={14}/></span></Link></article>)}</div></div>}
