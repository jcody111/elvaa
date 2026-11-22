'use client'
import {useState} from 'react'
import Link from 'next/link'
import {Minus,Plus,ArrowRight} from 'lucide-react'
import type {Product,Variant} from '@/lib/types'
import {euro} from '@/lib/types'
import {useCart} from '@/store/cart'
import {useUI} from '@/store/ui'
import WishlistButton from './WishlistButton'
export default function ProductBuyBox({product,compact=false,onAdded}:{product:Product;compact?:boolean;onAdded?:()=>void}){
 const [selected,setSelected]=useState<Variant|null>(null);const [quantity,setQuantity]=useState(1);const [error,setError]=useState('');const add=useCart(s=>s.add);const show=useUI(s=>s.show)
 const hasVariants=product.variants.length>0;const available=product.stock>0
 const price=selected?.price??product.price
 function handleAdd(){if(hasVariants&&!selected){setError('Please select a size.');return}if(!add(product,selected,quantity)){setError('That quantity is not available.');return}setError('');show('Added to your bag');onAdded?.()}
 return <div className={`buy-box ${compact?'buy-box-compact':''}`}>
  <span className="eyebrow">{product.category_name||'THE ELVAA COLLECTION'}</span>
  <h1>{product.name}</h1><div className="product-price">{euro(price)} {product.compare_at_price&&<del>{euro(product.compare_at_price)}</del>}</div>
  <p className="product-description">{product.description}</p>
  {product.specifications?.Colour&&<p className="option-label">COLOUR <span>{product.specifications.Colour}</span></p>}
  {product.specifications?.Colour&&<span className="colour-dot" title={product.specifications.Colour}/>}
  {hasVariants&&<><p className="option-label">SELECT SIZE <span>Choose your usual size</span></p><div className="size-options">{product.variants.map(v=><button key={v.id} className={selected?.id===v.id?'selected':''} disabled={v.stock===0} onClick={()=>{setSelected(v);setError('')}} aria-pressed={selected?.id===v.id}>{v.name}</button>)}</div></>}
  <p className="stock-note">{available?'Available to order':'Currently out of stock'}</p>
  <div className="add-row"><div className="quantity-control"><button aria-label="Decrease quantity" onClick={()=>setQuantity(Math.max(1,quantity-1))}><Minus size={14}/></button><span>{quantity}</span><button aria-label="Increase quantity" onClick={()=>setQuantity(Math.min(20,quantity+1))}><Plus size={14}/></button></div><button className="button button-dark add-button" disabled={!available} onClick={handleAdd}>ADD TO BAG <ArrowRight size={16}/></button><WishlistButton product={product} className="buy-heart"/></div>
  {error&&<p className="form-error" role="alert">{error}</p>}
  {compact&&<Link className="text-link details-link" href={`/product/${product.slug}`}>VIEW FULL DETAILS <ArrowRight size={14}/></Link>}
 </div>
}
