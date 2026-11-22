'use client'
import {Suspense,useEffect,useState} from 'react'
import {useSearchParams} from 'next/navigation'
import Link from 'next/link'
import {api,errorMessage} from '@/lib/api'
function Verify(){const token=useSearchParams().get('token');const [message,setMessage]=useState('Verifying your email…');useEffect(()=>{if(!token){setMessage('Missing verification token.');return}api.post('/auth/verify-email/',{token}).then(r=>setMessage(r.data.detail)).catch(e=>setMessage(errorMessage(e)))},[token]);return <div className="account-wrap"><span className="eyebrow">YOUR ACCOUNT</span><h1>Email verification.</h1><p role="status">{message}</p><Link href="/account" className="button button-dark">GO TO ACCOUNT</Link></div>}
export default function VerifyPage(){return <Suspense><Verify/></Suspense>}
