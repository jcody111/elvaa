'use client'
import Link from 'next/link'
import {useEffect,useState} from 'react'
import {X} from 'lucide-react'
import type {Product} from '@/lib/types'
import {euro} from '@/lib/types'
import WishlistButton from './WishlistButton'
import ProductBuyBox from './ProductBuyBox'
export default function ProductCard({p}:{p:Product}){
 const [open,setOpen]=useState(false)
 useEffect(()=>{if(!open)return;const fn=(e:KeyboardEvent)=>{if(e.key==='Escape')setOpen(false)};document.addEventListener('keydown',fn);return()=>document.removeEventListener('keydown',fn)},[open])
 return <article className="product-card">
   <div className="product-image-wrap"><Link href={`/product/${p.slug}`} tabIndex={-1} aria-hidden="true"><img src={p.images[0]?.image||'/images/collection-essentials.jpg'} alt={p.images[0]?.alt||p.name} loading="lazy"/></Link>
    {p.is_new&&<span className="product-badge">NEW</span>}<WishlistButton product={p} className="product-heart"/>
    <button className="quick-view" onClick={()=>setOpen(true)}>QUICK VIEW</button>
   </div>
   <div className="product-card-info"><div><Link className="product-name" href={`/product/${p.slug}`}>{p.name}</Link><p>{p.specifications?.Colour||p.category_name}</p></div><span className="card-price">{euro(p.price)}</span></div>
   {open&&<div className="modal-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)setOpen(false)}}><div className="quick-modal" role="dialog" aria-modal="true" aria-label={`Quick view: ${p.name}`}><button className="modal-close icon-button" onClick={()=>setOpen(false)} aria-label="Close quick view"><X size={20}/></button><img src={p.images[0]?.image||'/images/collection-essentials.jpg'} alt={p.name}/><div className="quick-modal-content"><ProductBuyBox product={p} compact onAdded={()=>setOpen(false)}/></div></div></div>}
 </article>
}
