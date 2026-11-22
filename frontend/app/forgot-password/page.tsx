'use client'
import {useState} from 'react'
import Link from 'next/link'
import {api,errorMessage} from '@/lib/api'
export default function ForgotPassword(){const [email,setEmail]=useState('');const [message,setMessage]=useState('');return <div className="account-wrap"><span className="eyebrow">YOUR ACCOUNT</span><h1>Reset your password.</h1><p>Enter your email and we’ll send a link if an account exists.</p><form onSubmit={async e=>{e.preventDefault();try{const r=await api.post('/auth/forgot-password/',{email});setMessage(r.data.detail)}catch(err){setMessage(errorMessage(err))}}}><div className="field"><label htmlFor="reset-email">Email address</label><input id="reset-email" required type="email" value={email} onChange={e=>setEmail(e.target.value)}/></div><button className="button button-dark">SEND RESET LINK</button></form>{message&&<p className="form-success" role="status">{message}</p>}<div className="account-links"><Link href="/account">Back to sign in</Link></div></div>}
