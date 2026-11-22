'use client'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {useEffect,useState} from 'react'
import {api,restoreSession} from '@/lib/api'
import {useAuth} from '@/store/auth'
import {useGuestWishlist} from '@/store/wishlist'
import {useUI} from '@/store/ui'
import {Check,X} from 'lucide-react'
export default function Providers({children}:{children:React.ReactNode}){
 const [client]=useState(()=>new QueryClient({defaultOptions:{queries:{staleTime:30000,retry:1,refetchOnWindowFocus:false}}}))
 const message=useUI(s=>s.message); const dismiss=useUI(s=>s.dismiss); const user=useAuth(s=>s.user)
 useEffect(()=>{restoreSession()},[])
 useEffect(()=>{if(!user)return;const saved=useGuestWishlist.getState().items;if(!saved.length)return;Promise.allSettled(saved.map(p=>api.post('/wishlist/',{product:p.id}))).then(results=>{results.forEach((result,i)=>{if(result.status==='fulfilled')useGuestWishlist.getState().remove(saved[i].id)});client.invalidateQueries({queryKey:['wishlist']})})},[user,client])
 return <QueryClientProvider client={client}>{children}{message&&<div className="toast" role="status"><Check size={16}/><span>{message}</span><button onClick={dismiss} aria-label="Dismiss notification"><X size={15}/></button></div>}</QueryClientProvider>
}
