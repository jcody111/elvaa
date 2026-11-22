'use client'
import Link from 'next/link'
import {useEffect,useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {useRouter} from 'next/navigation'
import {api} from '@/lib/api'
import {Search,Heart,UserRound,ShoppingBag,Menu,X,ArrowRight} from 'lucide-react'
import {useCart} from '@/store/cart'
import Logo from './Logo'

const links=[{label:'New arrivals',href:'/shop?is_new=true'},{label:'Clothing',href:'/shop?category=clothing'},{label:'Accessories',href:'/shop?category=accessories'},{label:'Our story',href:'/about'}]
export default function Header(){
 const router=useRouter()
 const [menu,setMenu]=useState(false);const [search,setSearch]=useState(false);const [q,setQ]=useState('');const [mounted,setMounted]=useState(false)
 const {data:settings}=useQuery({queryKey:['store-settings'],queryFn:()=>api.get<{free_shipping_threshold:string}>('/settings/store/').then(r=>r.data)})
 const count=useCart(s=>s.items.reduce((n,i)=>n+i.quantity,0))
 useEffect(()=>setMounted(true),[])
 useEffect(()=>{const fn=(e:KeyboardEvent)=>{if(e.key==='Escape'){setMenu(false);setSearch(false)}};window.addEventListener('keydown',fn);return()=>window.removeEventListener('keydown',fn)},[])
 return <header className="site-header">
   <div className="announcement"><span>COMPLIMENTARY STANDARD SHIPPING {settings?`ON ORDERS OF €${Number(settings.free_shipping_threshold).toLocaleString('en-DE')} OR MORE`:'ON ELIGIBLE ORDERS'}</span><Link href="/shipping">Discover more <ArrowRight size={12}/></Link></div>
   <div className="header-main page-width">
    <button className="icon-button mobile-menu-button" onClick={()=>setMenu(!menu)} aria-label={menu?'Close menu':'Open menu'} aria-expanded={menu}>{menu?<X size={22}/>:<Menu size={22}/>}</button>
    <nav className="desktop-nav" aria-label="Main navigation">{links.map(l=><Link key={l.label} href={l.href}>{l.label}</Link>)}</nav>
    <Logo/>
    <div className="header-actions">
      <button className="icon-button" onClick={()=>setSearch(v=>!v)} aria-label={search?'Close search':'Open search'} aria-expanded={search}><Search size={20}/></button>
      <Link className="icon-button account-icon" href="/account" aria-label="Account"><UserRound size={20}/></Link>
      <Link className="icon-button wishlist-icon" href="/wishlist" aria-label="Wishlist"><Heart size={20}/></Link>
      <Link className="icon-button bag-icon" href="/cart" aria-label={`Shopping bag${mounted&&count?`, ${count} items`:''}`}><ShoppingBag size={20}/>{mounted&&count>0&&<span className="bag-count">{count}</span>}</Link>
    </div>
   </div>
   {search&&<form className="header-search" onSubmit={e=>{e.preventDefault();if(q.trim()){router.push(`/shop?search=${encodeURIComponent(q.trim())}`);setSearch(false)}}}>
    <div className="page-width search-inner"><Search size={19}/><input value={q} onChange={e=>setQ(e.target.value)} placeholder="What are you looking for?" aria-label="Search products" autoFocus/><button type="submit" className="search-submit">SEARCH <ArrowRight size={16}/></button><button type="button" onClick={()=>setSearch(false)} aria-label="Close search" className="icon-button"><X size={19}/></button></div>
   </form>}
   {menu&&<div className="mobile-nav-wrap"><nav className="mobile-nav" aria-label="Mobile navigation">{links.map(l=><Link onClick={()=>setMenu(false)} key={l.label} href={l.href}>{l.label}<ArrowRight size={17}/></Link>)}<Link onClick={()=>setMenu(false)} href="/account">My account<ArrowRight size={17}/></Link><Link onClick={()=>setMenu(false)} href="/wishlist">Wishlist<ArrowRight size={17}/></Link></nav></div>}
 </header>
}
