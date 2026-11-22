'use client'
import Link from 'next/link'
import {useQuery} from '@tanstack/react-query'
import AccountGuard from '@/components/AccountGuard'
import {useAuth} from '@/store/auth'
import {api,errorMessage} from '@/lib/api'
import {euro} from '@/lib/types'
import type {Order,Page} from '@/lib/types'
export default function MyOrders(){const user=useAuth(s=>s.user);const q=useQuery({queryKey:['my-orders',user?.id],queryFn:()=>api.get<Page<Order>>('/orders/').then(r=>r.data),enabled:!!user});return <AccountGuard><div className="page-width dashboard-wrap"><nav className="breadcrumbs"><Link href="/account">My account</Link> / <span>Orders</span></nav><h1 className="page-title">Your orders.</h1><p className="summary-note">All of your orders, in one place.</p>{q.isLoading?<p className="empty-state">Loading…</p>:q.error?<div className="error-box">{errorMessage(q.error)}</div>:q.data?.results.length?<div className="table-wrap"><table className="data-table"><thead><tr><th>ORDER</th><th>DATE</th><th>STATUS</th><th>PAYMENT</th><th>TOTAL</th><th>TRACKING</th></tr></thead><tbody>{q.data.results.map(o=><tr key={o.id}><td>{o.order_number}</td><td>{new Date(o.created_at).toLocaleDateString()}</td><td>{o.status}</td><td>{o.payment_status}</td><td>{euro(o.total)}</td><td>{o.tracking_number||'—'}</td></tr>)}</tbody></table></div>:<div className="empty-state">You haven’t placed an order yet. <Link href="/shop" style={{textDecoration:'underline'}}>Explore the collection</Link>.</div>}</div></AccountGuard>}
