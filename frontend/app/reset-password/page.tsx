'use client'
import {Suspense,useState} from 'react'
import {useSearchParams} from 'next/navigation'
import Link from 'next/link'
import {api,errorMessage} from '@/lib/api'
function Reset(){const sp=useSearchParams();const [password,setPassword]=useState('');const [message,setMessage]=useState('');return <div className="account-wrap"><span className="eyebrow">YOUR ACCOUNT</span><h1>Choose a new password.</h1><p>Use at least 10 characters.</p><form onSubmit={async e=>{e.preventDefault();try{const r=await api.post('/auth/reset-password/',{uid:sp.get('uid'),token:sp.get('token'),password});setMessage(r.data.detail)}catch(err){setMessage(errorMessage(err))}}}><div className="field"><label htmlFor="new-password">New password</label><input id="new-password" type="password" required minLength={10} value={password} onChange={e=>setPassword(e.target.value)}/></div><button className="button button-dark">UPDATE PASSWORD</button></form>{message&&<p className="form-success" role="status">{message}</p>}<div className="account-links"><Link href="/account">Back to sign in</Link></div></div>}
export default function ResetPage(){return <Suspense><Reset/></Suspense>}
