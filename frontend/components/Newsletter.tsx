'use client'
import {useState} from 'react'
import Link from 'next/link'
import {ArrowRight} from 'lucide-react'
import {api,errorMessage} from '@/lib/api'
export default function Newsletter(){
 const [email,setEmail]=useState('');const [message,setMessage]=useState('');const [busy,setBusy]=useState(false)
 async function submit(e:React.FormEvent){e.preventDefault();setBusy(true);try{const response=await api.post<{detail:string}>('/newsletter/',{email});setMessage(response.data.detail);setEmail('')}catch(err){setMessage(errorMessage(err))}finally{setBusy(false)}}
 return <section className="newsletter"><div className="page-width newsletter-inner"><div><span className="eyebrow">A NOTE FROM US TO YOU</span><h2>Good things in your inbox.</h2><p>Be the first to discover new collections, stories and a little inspiration.</p></div><div><form onSubmit={submit} className="newsletter-form"><label htmlFor="newsletter-email" className="sr-only">Email address</label><input id="newsletter-email" required type="email" placeholder="Your email address" value={email} onChange={e=>setEmail(e.target.value)}/><button type="submit" disabled={busy} aria-label="Subscribe to newsletter"><span>{busy?'JOINING':'SUBSCRIBE'}</span><ArrowRight size={18}/></button></form><p className="newsletter-note" aria-live="polite">{message||<>Confirm by email to receive our newsletter. Unsubscribe anytime. See our <Link href="/privacy">privacy policy</Link>.</>}</p></div></div></section>
}
