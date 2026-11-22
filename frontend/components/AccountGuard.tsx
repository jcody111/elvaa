'use client'
import Link from 'next/link'
import {useAuth} from '@/store/auth'
export default function AccountGuard({children}:{children:React.ReactNode}){const {user,initialized}=useAuth();if(!initialized)return <div className="loading-state">Loading your account…</div>;if(!user)return <div className="empty-bag"><h2>Make yourself at home.</h2><p>Please sign in to view your account.</p><Link href="/account" className="button button-dark">SIGN IN</Link></div>;return <>{children}</>}
