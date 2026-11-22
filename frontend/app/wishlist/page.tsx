'use client'
import Link from 'next/link'
import {useEffect,useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {Heart} from 'lucide-react'
import {api,errorMessage} from '@/lib/api'
import type {Page,Product} from '@/lib/types'
import {useAuth} from '@/store/auth'
import {useGuestWishlist} from '@/store/wishlist'
import ProductGrid from '@/components/ProductGrid'
type Saved={id:number;product:number;product_detail:Product}
export default function Wishlist(){const user=useAuth(s=>s.user);const local=useGuestWishlist(s=>s.items);const [mounted,setMounted]=useState(false);useEffect(()=>setMounted(true),[]);const q=useQuery({queryKey:['wishlist',user?.id],queryFn:()=>api.get<Page<Saved>>('/wishlist/').then(r=>r.data),enabled:!!user});const products=user?(q.data?.results.map(x=>x.product_detail)||[]):local;return <div className="page-width dashboard-wrap"><span className="eyebrow">SAVED FOR LATER</span><h1 className="page-title">Your wishlist.</h1><p className="summary-note">{user?'Your favourite pieces, all in one place.':<>Saved on this device. <Link href="/account" style={{textDecoration:'underline'}}>Sign in</Link> to save to your account.</>}</p>{q.error&&<div className="error-box">{errorMessage(q.error)}</div>}{mounted&&products.length?<ProductGrid products={products}/>:<div className="empty-bag"><Heart size={33}/><h2>Nothing saved just yet.</h2><p>Keep your favourite pieces close.</p><Link href="/shop" className="button button-dark">EXPLORE THE COLLECTION</Link></div>}</div>}
