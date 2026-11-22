'use client'
import Link from 'next/link'
import {useRouter} from 'next/navigation'
import axios from 'axios'
import {useEffect,useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {useForm} from 'react-hook-form'
import {zodResolver} from '@hookform/resolvers/zod'
import {z} from 'zod'
import {ArrowLeft,ArrowRight,CheckCircle2} from 'lucide-react'
import {api,errorMessage,fetchQuote,fetchShipping} from '@/lib/api'
import {euro} from '@/lib/types'
import {useCart} from '@/store/cart'
const schema=z.object({email:z.email('Enter a valid email address.'),full_name:z.string().min(2,'Please enter your full name.'),street:z.string().min(3,'Please enter your street address.'),city:z.string().min(2,'Please enter your city.'),postal_code:z.string().min(2,'Please enter your postal code.'),country:z.string().min(2,'Please enter your country.')})
type FormData=z.infer<typeof schema>
const names=['CONTACT','ADDRESS','DELIVERY','REVIEW','PAYMENT']
export default function Checkout(){
 const router=useRouter()
 const {items,couponCode,clear}=useCart();const [mounted,setMounted]=useState(false);const [step,setStep]=useState(0);const [shipping,setShipping]=useState<number|null>(null);const [accepted,setAccepted]=useState(false);const [paymentMethod,setPaymentMethod]=useState<'stripe'|'manual'|''>('');const [checkoutKey,setCheckoutKey]=useState('');const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');const [canCancel,setCanCancel]=useState(false);const [order,setOrder]=useState<{order_number:string;total:string}|null>(null)
 const {register,trigger,getValues,formState:{errors}}=useForm<FormData>({resolver:zodResolver(schema),defaultValues:{email:'',full_name:'',street:'',city:'',postal_code:'',country:'Germany'}})
 useEffect(()=>{setMounted(true);const key=sessionStorage.getItem('elvaa-checkout-key')||window.crypto.randomUUID();sessionStorage.setItem('elvaa-checkout-key',key);setCheckoutKey(key)},[])
 const methods=useQuery({queryKey:['shipping'],queryFn:fetchShipping})
 useEffect(()=>{if(!shipping&&methods.data?.results.length)setShipping(methods.data.results[0].id)},[methods.data,shipping])
 const settings=useQuery({queryKey:['store-settings'],queryFn:()=>api.get<{manual_checkout_enabled:boolean;stripe_checkout_enabled:boolean;free_shipping_threshold:string}>('/settings/store/').then(r=>r.data)})
 useEffect(()=>{if(settings.data&&!paymentMethod)setPaymentMethod(settings.data.stripe_checkout_enabled?'stripe':settings.data.manual_checkout_enabled?'manual':'')},[settings.data,paymentMethod])
 const body={items:items.map(i=>({product_id:i.productId,variant_id:i.variantId,quantity:i.quantity})),coupon_code:couponCode,shipping_method_id:shipping}
 const quote=useQuery({queryKey:['checkout-quote',body],queryFn:()=>fetchQuote(body),enabled:mounted&&items.length>0&&!!shipping,retry:false})
 async function next(){setError('');if(step===0&&!await trigger('email'))return;if(step===1&&!await trigger(['full_name','street','city','postal_code','country']))return;if(step===2&&!shipping){setError('Please select a delivery method.');return}setStep(s=>s+1);window.scrollTo({top:0,behavior:'smooth'})}
 async function place(){
  if(paymentMethod==='manual'&&!accepted){setError('Please acknowledge that this is an unpaid demo order.');return}
  if(!paymentMethod||!checkoutKey)return
  setBusy(true);setError('');setNotice('');setCanCancel(false)
  const v=getValues()
  try{
   const r=await api.post('/checkout/',{...body,email:v.email,shipping_address:{full_name:v.full_name,street:v.street,city:v.city,postal_code:v.postal_code,country:v.country},payment_method:paymentMethod,idempotency_key:checkoutKey})
   if(paymentMethod==='stripe'){
    if(r.data.checkout_url){const url=new URL(r.data.checkout_url);if(url.protocol!=='https:'||url.hostname!=='checkout.stripe.com')throw new Error('Invalid payment URL');window.location.assign(url.toString());return}
    if(r.data.payment_status==='paid'){router.push(`/checkout/success?order=${encodeURIComponent(r.data.order_number)}`);return}
    throw new Error('Payment session unavailable.')
   }
   setOrder(r.data);clear();sessionStorage.removeItem('elvaa-checkout-key')
  }catch(e){setError(errorMessage(e));setCanCancel(axios.isAxiosError(e)&&[409,503].includes(e.response?.status||0))}finally{setBusy(false)}
 }
 async function cancelPrevious(){
  if(!checkoutKey)return
  setBusy(true);setError('');setNotice('')
  try{
   await api.post('/checkout/cancel/',{idempotency_key:checkoutKey})
   const key=window.crypto.randomUUID();sessionStorage.setItem('elvaa-checkout-key',key);setCheckoutKey(key)
   setCanCancel(false);setNotice('The previous unpaid checkout was cancelled. You may review your details and try again.')
  }catch(e){setError(errorMessage(e))}finally{setBusy(false)}
 }
 if(!mounted)return <div className="loading-state">Preparing your checkout…</div>
 if(order)return <div className="content-page" style={{textAlign:'center'}}><CheckCircle2 size={39} style={{margin:'0 auto 22px',color:'#8a755f'}}/><span className="eyebrow">ORDER REQUEST RECEIVED</span><h1>Thank you.</h1><p>Your demonstration order <strong>{order.order_number}</strong> has been created. No payment was collected, and this is not a completed purchase.</p><p>Order total: {euro(order.total)} · Payment status: unpaid</p><Link href="/shop" className="button button-dark">CONTINUE EXPLORING <ArrowRight size={16}/></Link></div>
 if(!items.length)return <div className="empty-bag"><h2>Your bag is empty.</h2><p>Start with something you love.</p><Link href="/shop" className="button button-dark">SHOP THE COLLECTION</Link></div>
 return <div className="page-width checkout-layout"><div className="checkout-form"><h1 className="page-title">Checkout.</h1><div className="checkout-steps">{names.map((n,i)=><span key={n} className={i===step?'active':''}>{i+1}. {n}{i<4?' / ':''}</span>)}</div>
 {step===0&&<><h2>Let’s start with you.</h2><p className="summary-note">We’ll use this email for your order details.</p><div className="field"><label htmlFor="co-email">Email address</label><input id="co-email" type="email" {...register('email')}/>{errors.email&&<span className="form-error">{errors.email.message}</span>}</div></>}
 {step===1&&<><h2>Delivery address.</h2><div className="field"><label htmlFor="co-name">Full name</label><input id="co-name" {...register('full_name')}/>{errors.full_name&&<span className="form-error">{errors.full_name.message}</span>}</div><div className="field"><label htmlFor="co-street">Street address</label><input id="co-street" {...register('street')}/>{errors.street&&<span className="form-error">{errors.street.message}</span>}</div><div className="field-grid"><div className="field"><label htmlFor="co-city">City</label><input id="co-city" {...register('city')}/>{errors.city&&<span className="form-error">{errors.city.message}</span>}</div><div className="field"><label htmlFor="co-postal">Postal code</label><input id="co-postal" {...register('postal_code')}/>{errors.postal_code&&<span className="form-error">{errors.postal_code.message}</span>}</div></div><div className="field"><label htmlFor="co-country">Country</label><input id="co-country" {...register('country')}/>{errors.country&&<span className="form-error">{errors.country.message}</span>}</div></>}
 {step===2&&<><h2>Choose your delivery.</h2>{methods.isError&&<div className="error-box">Delivery methods could not be loaded.</div>}{methods.data?.results.map(m=><label key={m.id} className="shipping-choice"><input type="radio" name="shipping" checked={shipping===m.id} onChange={()=>setShipping(m.id)}/><span><strong>{m.name}</strong><small>{m.estimated_days}</small></span><span className="shipping-cost">{m.free_over_threshold&&Number(quote.data?.subtotal||0)-Number(quote.data?.discount||0)>=Number(settings.data?.free_shipping_threshold||Infinity)?'Complimentary':euro(m.price)}</span></label>)}</>}
 {step===3&&<><h2>Review the details.</h2><p className="summary-note"><strong>Contact</strong><br/>{getValues('email')}</p><p className="summary-note"><strong>Deliver to</strong><br/>{getValues('full_name')}<br/>{getValues('street')}<br/>{getValues('postal_code')} {getValues('city')}<br/>{getValues('country')}</p><p className="summary-note"><strong>Delivery</strong><br/>{methods.data?.results.find(m=>m.id===shipping)?.name}</p></>}
 {step===4&&<><h2>Payment.</h2>{settings.data?.stripe_checkout_enabled&&<label className="shipping-choice"><input type="radio" name="payment" checked={paymentMethod==='stripe'} onChange={()=>setPaymentMethod('stripe')}/><span><strong>Secure card payment</strong><small>Continue to Stripe’s hosted checkout. Card details are never entered on ELVAA.</small></span></label>}{settings.data?.manual_checkout_enabled&&<><label className="shipping-choice"><input type="radio" name="payment" checked={paymentMethod==='manual'} onChange={()=>setPaymentMethod('manual')}/><span><strong>Unpaid demonstration order</strong><small>No payment will be collected.</small></span></label>{paymentMethod==='manual'&&<><div className="notice"><strong>Demo checkout only.</strong> This creates an unpaid demonstration order, not a completed purchase.</div><label style={{display:'flex',gap:10,alignItems:'start',margin:'22px 0',fontSize:12}}><input type="checkbox" checked={accepted} onChange={e=>setAccepted(e.target.checked)}/> I understand this is an unpaid demonstration order.</label></>}</>}{settings.data&&!settings.data.manual_checkout_enabled&&!settings.data.stripe_checkout_enabled&&<p className="form-error">Checkout is currently unavailable until a payment provider is configured.</p>}</>}
 {error&&<p className="form-error" role="alert">{error}</p>}{notice&&<p className="form-success" role="status">{notice}</p>}{canCancel&&<button type="button" className="remove-link" disabled={busy} onClick={cancelPrevious}>Cancel previous checkout before retrying</button>}{quote.error&&<p className="form-error">{errorMessage(quote.error)}</p>}
 <div style={{display:'flex',gap:12,alignItems:'center',marginTop:28}}>{step>0&&<button type="button" className="button button-outline" onClick={()=>{setStep(step-1);setError('')}}><ArrowLeft size={15}/> BACK</button>}{step<4?<button type="button" className="button button-dark" onClick={next}>CONTINUE <ArrowRight size={16}/></button>:<button type="button" className="button button-dark" onClick={place} disabled={busy||!paymentMethod||!checkoutKey||!quote.data}>{busy?'PLEASE WAIT…':paymentMethod==='stripe'?'CONTINUE TO SECURE PAYMENT':'CREATE DEMO ORDER'} <ArrowRight size={16}/></button>}</div></div>
 <aside className="checkout-summary"><h2>Your order</h2>{items.map(i=><div className="checkout-product" key={i.key}><img src={i.image} alt=""/><div><p>{i.name}</p><small>{i.variantName||'One size'} · Qty {i.quantity}</small></div><span>{euro(i.price*i.quantity)}</span></div>)}<div className="summary-line"><span>Subtotal</span><span>{quote.data?euro(quote.data.subtotal):'—'}</span></div>{!!Number(quote.data?.discount)&&<div className="summary-line"><span>Discount ({couponCode})</span><span>− {euro(quote.data!.discount)}</span></div>}<div className="summary-line"><span>Delivery</span><span>{quote.data?Number(quote.data.shipping)?euro(quote.data.shipping):'Complimentary':'—'}</span></div><div className="summary-line summary-total"><span>Total</span><span>{quote.data?euro(quote.data.total):'—'}</span></div><p className="summary-note">Includes {quote.data?euro(quote.data.tax_included):'—'} estimated VAT.</p><Link href="/cart" className="remove-link">Edit shopping bag</Link></aside></div>
}
