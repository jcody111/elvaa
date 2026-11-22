'use client'
import {useState} from 'react'
import Link from 'next/link'
import {api,errorMessage} from '@/lib/api'

export default function Cancel(){
 const [busy,setBusy]=useState(false)
 const [cancelled,setCancelled]=useState(false)
 const [error,setError]=useState('')
 async function cancelSession(){
  const key=sessionStorage.getItem('elvaa-checkout-key')
  if(!key){setError('No checkout key was found in this browser. Contact support if a payment was attempted.');return}
  setBusy(true);setError('')
  try{
   await api.post('/checkout/cancel/',{idempotency_key:key})
   sessionStorage.removeItem('elvaa-checkout-key');setCancelled(true)
  }catch(e){setError(errorMessage(e))}finally{setBusy(false)}
 }
 return <div className="content-page" style={{textAlign:'center'}}>
  <span className="eyebrow">CHECKOUT</span><h1>Your bag is still here.</h1>
  {cancelled?<p>The unpaid checkout was cancelled and its reservation released. Your bag has not been changed.</p>:<><p>Returning from payment does not automatically close the hosted session. Cancel it before starting a different checkout; if payment is already processing, contact support.</p><button type="button" className="button button-dark" disabled={busy} onClick={cancelSession}>{busy?'CHECKING PAYMENT…':'CANCEL PAYMENT SESSION'}</button></>}
  {error&&<p className="form-error" role="alert">{error}</p>}
  <p><Link href="/cart" className="button button-outline">RETURN TO YOUR BAG</Link></p>
 </div>
}
