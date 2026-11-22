'use client'
import {useState} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import {api,errorMessage} from '@/lib/api'
import {euro} from '@/lib/types'
import type {Page,Order} from '@/lib/types'

type Customer={id:number;username:string;email:string;first_name:string;last_name:string;phone:string;date_joined:string;email_verified:boolean;is_active:boolean;order_count:number;paid_order_value:string}

function CustomerRow({customer,refresh}:{customer:Customer;refresh:()=>Promise<unknown>}){
 const [expanded,setExpanded]=useState(false)
 const [page,setPage]=useState(1)
 const [busy,setBusy]=useState(false)
 const [message,setMessage]=useState('')
 const [error,setError]=useState('')
 const orders=useQuery({queryKey:['customer-orders',customer.id,page],queryFn:()=>api.get<Page<Order>>(`/auth/admin/users/${customer.id}/orders/`,{params:{page}}).then(r=>r.data),enabled:expanded})
 async function toggle(){
  const next=!customer.is_active
  if(!window.confirm(next?`Reactivate ${customer.email}? Previously revoked refresh sessions remain revoked.`:`Deactivate ${customer.email}? Sign-in will be blocked and refresh sessions revoked.`))return
  setBusy(true);setMessage('');setError('')
  try{
   await api.post(`/auth/admin/users/${customer.id}/status/`,{expected_active:customer.is_active,is_active:next})
   await refresh();setMessage(next?'Account reactivated.':'Account deactivated.')
  }catch(e){setError(errorMessage(e));await refresh()}finally{setBusy(false)}
 }
 return <>
  <tr>
   <td><strong>{[customer.first_name,customer.last_name].filter(Boolean).join(' ')||'—'}</strong><br/><span className="admin-note">@{customer.username}</span></td>
   <td>{customer.email}</td><td>{customer.email_verified?'Yes':'No'}</td><td>{customer.is_active?'Active':'Inactive'}</td><td>{customer.order_count}</td><td>{euro(customer.paid_order_value)}</td>
   <td className="admin-actions"><button type="button" aria-expanded={expanded} onClick={()=>setExpanded(v=>!v)}>{expanded?'HIDE ORDERS':'VIEW ORDERS'}</button><button type="button" disabled={busy} onClick={toggle}>{busy?'PLEASE WAIT…':customer.is_active?'DEACTIVATE':'REACTIVATE'}</button>{message&&<div className="admin-note" role="status">{message}</div>}{error&&<div className="form-error" role="alert">{error}</div>}</td>
  </tr>
  {expanded&&<tr><td colSpan={7}>
   <div style={{padding:'12px 0',whiteSpace:'normal'}}>
    <strong>Orders linked to {customer.email}</strong><p className="admin-note">Guest orders are not automatically linked by email. Paid value includes only fully paid orders; partially refunded orders are excluded.</p>
    {orders.isLoading&&<p className="admin-note">Loading orders…</p>}{orders.error&&<p className="form-error" role="alert">{errorMessage(orders.error)}</p>}
    {orders.data&&!orders.data.results.length&&<p className="admin-note">No account-linked orders yet.</p>}
    {orders.data?.results.map(order=><p key={order.id} className="admin-note" style={{padding:'7px 0',borderBottom:'1px solid #eee'}}><strong>{order.order_number}</strong> · {new Date(order.created_at).toLocaleDateString()} · {order.status.replaceAll('_',' ')} · {order.payment_status.replaceAll('_',' ')} · {euro(order.total)}</p>)}
    {(page>1||orders.data?.next)&&<div className="pagination"><button type="button" disabled={page===1||orders.isFetching} onClick={()=>setPage(p=>p-1)}>PREVIOUS ORDERS</button><button type="button" disabled={!orders.data?.next||orders.isFetching} onClick={()=>setPage(p=>p+1)}>NEXT ORDERS</button></div>}
   </div>
  </td></tr>}
 </>
}

export default function AdminCustomers(){
 const qc=useQueryClient();const [search,setSearch]=useState('');const [page,setPage]=useState(1)
 const q=useQuery({queryKey:['admin-customers',search,page],queryFn:()=>api.get<Page<Customer>>('/auth/admin/users/',{params:{search,page}}).then(r=>r.data)})
 return <div>
  <div className="admin-topline"><span>PEOPLE</span><span>CUSTOMERS</span></div>
  <div className="dashboard-header"><div><span className="eyebrow">CUSTOMER MANAGEMENT</span><h1 className="page-title">Customers.</h1><p className="summary-note">Browse customer accounts and linked purchase history.</p></div></div>
  <div className="admin-toolbar"><label htmlFor="customer-search" className="admin-note">Search customers</label><input id="customer-search" value={search} onChange={e=>{setSearch(e.target.value);setPage(1)}} placeholder="Search by name or email"/><span className="admin-note">{q.data?.count??0} accounts</span></div>
  {q.error&&<div className="error-box" role="alert">{errorMessage(q.error)}</div>}{q.isLoading&&<p className="admin-note">Loading customers…</p>}
  <div className="table-wrap"><table className="data-table"><thead><tr><th>NAME</th><th>EMAIL</th><th>VERIFIED</th><th>STATUS</th><th>ORDERS</th><th>PAID VALUE</th><th>ACTIONS</th></tr></thead><tbody>
   {q.data?.results.map(customer=><CustomerRow key={customer.id} customer={customer} refresh={()=>qc.invalidateQueries({queryKey:['admin-customers']})}/>)}
  </tbody></table></div>
  {q.data&&!q.data.results.length&&<p className="empty-state">No matching customer accounts.</p>}
  {(page>1||q.data?.next)&&<div className="pagination"><button type="button" disabled={page===1||q.isFetching} onClick={()=>setPage(p=>p-1)}>PREVIOUS</button><button type="button" disabled={!q.data?.next||q.isFetching} onClick={()=>setPage(p=>p+1)}>NEXT</button></div>}
 </div>
}
