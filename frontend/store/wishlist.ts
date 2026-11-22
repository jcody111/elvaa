import {create} from 'zustand'
import {persist} from 'zustand/middleware'
import type {Product} from '@/lib/types'
type WishlistState={items:Product[];toggle:(p:Product)=>void;remove:(id:number)=>void}
export const useGuestWishlist=create<WishlistState>()(persist((set)=>({items:[],
  toggle:p=>set(s=>({items:s.items.some(x=>x.id===p.id)?s.items.filter(x=>x.id!==p.id):[...s.items,p]})),
  remove:id=>set(s=>({items:s.items.filter(x=>x.id!==id)}))}),{name:'elvaa-wishlist-v1'}))
