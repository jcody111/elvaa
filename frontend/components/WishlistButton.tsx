'use client'
import {useEffect,useState} from 'react'
import {Heart} from 'lucide-react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {api,errorMessage} from '@/lib/api'
import type {Page,Product} from '@/lib/types'
import {useAuth} from '@/store/auth'
import {useGuestWishlist} from '@/store/wishlist'
import {useUI} from '@/store/ui'
type Saved={id:number;product:number;product_detail:Product}
export default function WishlistButton({product,className=''}:{product:Product;className?:string}){
 const user=useAuth(s=>s.user);const local=useGuestWishlist(s=>s.items);const toggle=useGuestWishlist(s=>s.toggle);const show=useUI(s=>s.show);const client=useQueryClient();const [mounted,setMounted]=useState(false)
 useEffect(()=>setMounted(true),[])
 const {data}=useQuery({queryKey:['wishlist',user?.id],queryFn:()=>api.get<Page<Saved>>('/wishlist/').then(r=>r.data),enabled:!!user})
 const item=data?.results.find(x=>x.product===product.id);const active=mounted&&(user?!!item:local.some(x=>x.id===product.id))
 const mutation=useMutation({mutationFn:async()=>{if(item)await api.delete(`/wishlist/${item.id}/`);else await api.post('/wishlist/',{product:product.id})},onSuccess:()=>{client.invalidateQueries({queryKey:['wishlist']});show(active?'Removed from your wishlist':'Saved to your wishlist')},onError:e=>show(errorMessage(e))})
 return <button className={`wishlist-button ${className}`} aria-label={active?'Remove from wishlist':'Add to wishlist'} aria-pressed={active} disabled={mutation.isPending} onClick={e=>{e.preventDefault();e.stopPropagation();if(user)mutation.mutate();else{toggle(product);show(active?'Removed from your wishlist':'Saved to your wishlist')}}}><Heart size={19} fill={active?'currentColor':'none'} strokeWidth={1.5}/></button>
}
