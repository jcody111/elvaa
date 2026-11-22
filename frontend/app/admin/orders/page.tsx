'use client'
import {useState} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import {api,errorMessage} from '@/lib/api'
import {euro} from '@/lib/types'
import type {Order,Page} from '@/lib/types'

const transitions:Record<string,string[]>={pending:['pending','cancelled'],paid:['paid','processing'],processing:['processing','shipped'],shipped:['shipped','delivered'],delivered:['delivered','completed'],completed:['completed']}
function Row({order,refresh}:{order:Order;refresh:()=>Promise<unknown>}){
 const [status,setStatus]=useState(order.status)
 const [tracking,setTracking]=useState(order.tracking_number)
 const [expanded,setExpanded]=useState(false)
 const [msg,setMsg]=useState('')
 const [error,setError]=useState('')
 const [busy,setBusy]=useState(false)
 const terminal=['cancelled','refunded','payment_review'].includes(order.status)
 const needsReview=order.status!=='pending'&&order.payment_status!=='paid'
 const readOnly=terminal||needsReview
 const choices=(transitions[order.status]||[order.status]).filter(s=>!(s==='cancelled'&&order.payment_method==='stripe'))
 const address=order.shipping_address||{}
 async function save(){
  setBusy(true);setMsg('');setError('')
  try{await api.post(`/orders/${order.id}/status/`,{status,tracking_number:tracking});await refresh();setMsg('Saved')}
  catch(e){setError(errorMessage(e))}finally{setBusy(false)}
 }
 async function recheck(){
  setBusy(true);setMsg('');setError('')
  try{
   const r=await api.post<{result:string}>(`/orders/${order.id}/reconcile/`)
   const messages:Record<string,string>={open:'Payment session remains open.',async_pending:'Payment is still processing.',unknown:'No provider session ID is recorded; investigate manually.',cancelled:'Session expired and stock was released.',paid:'Payment confirmed.',review:'Payment requires manual review.',pending:'Payment is still pending.'}
   setMsg(messages[r.data.result]||'Payment checked.');await refresh()
  }catch(e){setError(errorMessage(e))}finally{setBusy(false)}
 }
 return <>
  <tr>
   <td><strong>{order.order_number}</strong><br/><button type="button" className="admin-link" aria-expanded={expanded} onClick={()=>setExpanded(v=>!v)}>{expanded?'HIDE DETAILS':'SHOW DETAILS'}</button></td>
   <td>{new Date(order.created_at).toLocaleDateString()}</td><td>{euro(order.total)}</td><td>{order.payment_status}<br/><span className="admin-note">{order.payment_method}</span></td>
   <td><select aria-label={`Status for ${order.order_number}`} value={status} disabled={readOnly||busy} onChange={e=>setStatus(e.target.value)}>{choices.map(s=><option key={s} value={s}>{s.replaceAll('_',' ')}</option>)}</select></td>
   <td><input aria-label={`Tracking number for ${order.order_number}`} maxLength={100} value={tracking} disabled={readOnly||busy} onChange={e=>setTracking(e.target.value)} style={{width:120,border:'1px solid #ddd',padding:7}}/></td>
   <td>{!readOnly&&<button type="button" className="admin-link" disabled={busy} onClick={save}>{busy?'Working…':'Save'}</button>}{order.payment_method==='stripe'&&order.status==='pending'&&order.payment_status==='unpaid'&&<><br/><button type="button" className="admin-link" disabled={busy} onClick={recheck}>RECHECK PAYMENT</button></>}{msg&&<div className="admin-note" role="status">{msg}</div>}{error&&<div className="form-error" role="alert">{error}</div>}{readOnly&&<span className="admin-note">{order.status==='cancelled'?'Closed':'Review payment'}</span>}</td>
  </tr>
  {expanded&&<tr><td colSpan={7}>
   <div className="admin-form-grid" style={{whiteSpace:'normal',padding:'12px 0'}}>
    <div><strong>CONTACT & DELIVERY</strong><p>{order.email}</p><p>{address.full_name}<br/>{address.street}<br/>{address.postal_code} {address.city}<br/>{address.country}</p></div>
    <div><strong>ITEMS</strong>{order.items.map(item=><p key={item.id}>{item.name}{item.variant_name?` · ${item.variant_name}`:''}<br/><span className="admin-note">{item.sku} · {item.quantity} × {euro(item.unit_price)} = {euro(item.total)}</span></p>)}</div>
    <div><strong>SUMMARY</strong><p>Subtotal: {euro(order.subtotal)}<br/>Discount{order.coupon_code?` (${order.coupon_code})`:''}: − {euro(order.discount)}<br/>Delivery: {euro(order.shipping)}<br/>Included VAT: {euro(order.tax)}<br/><strong>Total: {euro(order.total)}</strong></p></div>
   </div>
  </td></tr>}
 </>
}
export default function AdminOrders(){
 const qc=useQueryClient();const [page,setPage]=useState(1);const [search,setSearch]=useState('');const [filter,setFilter]=useState('')
 const q=useQuery({queryKey:['admin-orders',page,search,filter],queryFn:()=>api.get<Page<Order>>('/orders/',{params:{page,search,status:filter||undefined}}).then(r=>r.data)})
 return <div>
  <div className="admin-topline"><span>OPERATIONS</span><span>ORDERS</span></div>
  <div className="dashboard-header"><div><span className="eyebrow">ORDER MANAGEMENT</span><h1 className="page-title">Orders.</h1><p className="summary-note">Review order details, status and tracking information.</p></div></div>
  <div className="notice">Only confirmed paid orders can progress to fulfillment. Stripe cancellations and refunds require provider confirmation; review and refunded orders are locked here.</div>
  <div className="admin-toolbar" style={{marginTop:20}}><label htmlFor="order-search" className="admin-note">Search orders</label><input id="order-search" placeholder="Order number, email or SKU" value={search} onChange={e=>{setSearch(e.target.value);setPage(1)}}/><label htmlFor="order-filter" className="admin-note">Status</label><select id="order-filter" value={filter} onChange={e=>{setFilter(e.target.value);setPage(1)}}><option value="">All statuses</option>{['pending','paid','processing','shipped','delivered','completed','cancelled','refunded','payment_review'].map(s=><option key={s} value={s}>{s.replaceAll('_',' ')}</option>)}</select><span className="admin-note">{q.data?.count??0} orders</span></div>
  {q.error&&<div className="error-box" role="alert">{errorMessage(q.error)}</div>}
  {q.isLoading&&<p className="admin-note">Loading orders…</p>}
  <div className="table-wrap" style={{marginTop:25}}><table className="data-table"><thead><tr><th>ORDER</th><th>DATE</th><th>TOTAL</th><th>PAYMENT</th><th>STATUS</th><th>TRACKING</th><th></th></tr></thead><tbody>
   {q.data?.results.map(o=><Row key={`${o.id}-${o.status}-${o.tracking_number}`} order={o} refresh={()=>qc.invalidateQueries({queryKey:['admin-orders']})}/>)}
  </tbody></table></div>
  {q.data&&!q.data.results.length&&<p className="empty-state">No orders yet.</p>}
  {(page>1||q.data?.next)&&<div className="pagination"><button type="button" disabled={page===1||q.isFetching} onClick={()=>setPage(p=>p-1)}>PREVIOUS</button><button type="button" disabled={!q.data?.next||q.isFetching} onClick={()=>setPage(p=>p+1)}>NEXT</button></div>}
 </div>
}
