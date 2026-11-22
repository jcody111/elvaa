'use client'
import {useState} from 'react'
import Link from 'next/link'
import {api,errorMessage} from '@/lib/api'

export default function NewsletterAction({action}:{action:'confirm'|'unsubscribe'}){
 const [busy,setBusy]=useState(false);const [done,setDone]=useState(false);const [message,setMessage]=useState('');const [error,setError]=useState('')
 const isConfirm=action==='confirm'
 async function submit(){
  const token=new URLSearchParams(window.location.hash.slice(1)).get('token')
  if(!token){setError('This link is missing its token. Please request a new email or contact us.');return}
  setBusy(true);setError('')
  try{
   const response=await api.post<{detail:string}>(`/newsletter/${action}/`,{token})
   setMessage(response.data.detail);setDone(true)
   window.history.replaceState(null,'',window.location.pathname+window.location.search)
  }catch(e){setError(errorMessage(e))}finally{setBusy(false)}
 }
 return <div className="account-wrap">
  <span className="eyebrow">ELVAA NEWSLETTER</span><h1>{isConfirm?'Confirm your subscription.':'Unsubscribe.'}</h1>
  {!done&&<><p>{isConfirm?'Please confirm that you would like to receive ELVAA news and inspiration.':'Confirm that you no longer wish to receive the ELVAA newsletter.'}</p><button type="button" className="button button-dark" disabled={busy} onClick={submit}>{busy?'PLEASE WAIT…':isConfirm?'CONFIRM SUBSCRIPTION':'UNSUBSCRIBE'}</button></>}
  {message&&<p className="form-success" role="status">{message}</p>}{error&&<p className="form-error" role="alert">{error}</p>}
  <div className="account-links"><Link href="/shop">Continue exploring</Link></div>
 </div>
}
