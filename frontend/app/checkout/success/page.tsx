'use client'
import {Suspense} from 'react'
import Link from 'next/link'
import {useSearchParams} from 'next/navigation'
import {CheckCircle2} from 'lucide-react'
import {useCart} from '@/store/cart'
import {useUI} from '@/store/ui'
function Success(){const order=useSearchParams().get('order');const clear=useCart(s=>s.clear);const show=useUI(s=>s.show);return <div className="content-page" style={{textAlign:'center'}}><CheckCircle2 size={40} style={{margin:'0 auto 22px',color:'#8a755f'}}/><span className="eyebrow">PAYMENT CONFIRMATION</span><h1>Thank you.</h1><p>We’re waiting for payment confirmation from our payment provider{order?` for order ${order}`:''}. An order is only marked paid after the provider confirms it.</p><p>Signed-in customers can check their order status in their account. Your bag remains available until you choose to clear it.</p><Link href="/account/orders" className="button button-dark">VIEW YOUR ORDERS</Link> <button className="button button-outline" onClick={()=>{clear();sessionStorage.removeItem('elvaa-checkout-key');show('Your bag has been cleared')}}>CLEAR MY BAG</button></div>}
export default function SuccessPage(){return <Suspense><Success/></Suspense>}
