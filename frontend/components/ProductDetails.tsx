'use client'
import Link from 'next/link'
import {useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {api,errorMessage,fetchProduct,fetchRelated} from '@/lib/api'
import type {Page,Product} from '@/lib/types'
import {useAuth} from '@/store/auth'
import ProductBuyBox from './ProductBuyBox'
import ProductGrid from './ProductGrid'
type Review={id:number;username:string;rating:number;title:string;body:string;created_at:string}
export default function ProductDetails({slug,initialProduct}:{slug:string;initialProduct:Product|null}){
 const {data:p,isLoading,isError,refetch}=useQuery({queryKey:['product',slug],queryFn:()=>fetchProduct(slug),initialData:initialProduct||undefined})
 const {data:related}=useQuery({queryKey:['related',slug],queryFn:()=>fetchRelated(slug)})
 const {data:reviews,refetch:refetchReviews}=useQuery({queryKey:['reviews',p?.id],queryFn:()=>api.get<Page<Review>>('/reviews/',{params:{product:p?.id}}).then(r=>r.data),enabled:!!p})
 const user=useAuth(s=>s.user);const [rating,setRating]=useState(5);const [body,setBody]=useState('');const [message,setMessage]=useState('')
 async function submitReview(e:React.FormEvent){e.preventDefault();try{await api.post('/reviews/',{product:p?.id,rating,body});setBody('');setMessage('Thank you. Your review has been submitted for moderation.');refetchReviews()}catch(err){setMessage(errorMessage(err))}}
 if(isLoading)return <div className="loading-state">Loading your piece…</div>
 if(isError||!p)return <div className="page-width content-page"><h1>We couldn’t find that piece.</h1><p>It may no longer be available.</p><button className="button button-outline" onClick={()=>refetch()}>TRY AGAIN</button> <Link className="text-link" href="/shop">SHOP THE COLLECTION</Link></div>
 const jsonLd={"@context":"https://schema.org","@type":"Product",name:p.name,description:p.description,sku:p.sku,image:p.images.map(i=>i.image),offers:{"@type":"Offer",priceCurrency:'EUR',price:p.price,availability:p.stock?'https://schema.org/InStock':'https://schema.org/OutOfStock'}}
 return <div className="page-width"><script type="application/ld+json" dangerouslySetInnerHTML={{__html:JSON.stringify(jsonLd).replace(/</g,'\u003c')}}/><nav className="breadcrumbs" aria-label="Breadcrumb"><Link href="/">Home</Link> / <Link href="/shop">Shop</Link> / <span>{p.name}</span></nav><div className="product-detail"><div className="product-gallery">{p.images.length?p.images.map((i)=><img key={i.id} src={i.image} alt={i.alt||p.name}/>):<img src="/images/collection-essentials.jpg" alt={p.name}/>}</div><div><ProductBuyBox product={p}/><div className="detail-accordions"><details open><summary>DETAILS & CARE</summary><ul>{Object.entries(p.specifications).map(([k,v])=><li key={k}>{k}: {v}</li>)}</ul></details><details><summary>SHIPPING & RETURNS</summary><p>Complimentary standard delivery on eligible orders. View our <Link href="/shipping" style={{textDecoration:'underline'}}>shipping and returns information</Link>.</p></details><details><summary>REVIEWS ({reviews?.count||0})</summary>{reviews?.results.map(r=><div key={r.id} style={{paddingTop:14}}><strong>{'★'.repeat(r.rating)}{'☆'.repeat(5-r.rating)}</strong><p>{r.body}</p><small>{r.username||'ELVAA customer'}</small></div>)}{user?<form onSubmit={submitReview} style={{marginTop:18}}><label className="field">Rating<select value={rating} onChange={e=>setRating(Number(e.target.value))}>{[5,4,3,2,1].map(n=><option key={n} value={n}>{n} out of 5</option>)}</select></label><label className="field">Your review<textarea required value={body} onChange={e=>setBody(e.target.value)}/></label><button className="button button-outline">SUBMIT REVIEW</button></form>:<p><Link href="/account" style={{textDecoration:'underline'}}>Sign in</Link> to share a review.</p>}{message&&<p aria-live="polite">{message}</p>}</details></div></div></div>{!!related?.length&&<section className="related-section"><div className="section-heading"><div><span className="eyebrow">YOU MAY ALSO LIKE</span><h2>More to discover.</h2></div><Link href="/shop" className="text-link">VIEW ALL</Link></div><ProductGrid products={related.slice(0,4)}/></section>}</div>
}
