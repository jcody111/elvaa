'use client'
import {useState} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import {api,errorMessage} from '@/lib/api'
import type {Page} from '@/lib/types'

type Coupon={id:number;code:string;discount_type:string;discount_value:string;minimum_order:string;usage_limit:number|null;expires_at:string|null;is_active:boolean;used_count:number}
type Subscriber={id:number;email:string;is_active:boolean;confirmation_sent_at:string|null;confirmed_at:string|null;unsubscribed_at:string|null;created_at:string}

function CouponRow({coupon,refresh}:{coupon:Coupon;refresh:()=>Promise<unknown>}){
 const [busy,setBusy]=useState(false);const [error,setError]=useState('')
 async function toggle(){setBusy(true);setError('');try{await api.patch(`/coupons/${coupon.id}/`,{is_active:!coupon.is_active});await refresh()}catch(e){setError(errorMessage(e))}finally{setBusy(false)}}
 async function remove(){if(!window.confirm(`Delete discount code ${coupon.code}?`))return;setBusy(true);setError('');try{await api.delete(`/coupons/${coupon.id}/`);await refresh()}catch(e){setError(errorMessage(e))}finally{setBusy(false)}}
 return <tr><td>{coupon.code}</td><td>{coupon.discount_value}{coupon.discount_type==='percent'?'%':' EUR'}</td><td>{coupon.used_count}{coupon.usage_limit!==null?` / ${coupon.usage_limit}`:''}</td><td>{coupon.is_active?'Active':'Inactive'}{coupon.expires_at?` · ends ${new Date(coupon.expires_at).toLocaleDateString()}`:''}</td><td className="admin-actions"><button type="button" disabled={busy} onClick={toggle}>{coupon.is_active?'DEACTIVATE':'ACTIVATE'}</button><button type="button" disabled={busy} onClick={remove}>DELETE</button>{error&&<span className="form-error" role="alert">{error}</span>}</td></tr>
}
function SubscriberRow({subscriber,refresh}:{subscriber:Subscriber;refresh:()=>Promise<unknown>}){
 const [busy,setBusy]=useState(false);const [message,setMessage]=useState('');const [error,setError]=useState('')
 const state=subscriber.is_active?'Confirmed':subscriber.confirmation_sent_at?'Pending confirmation':subscriber.unsubscribed_at?'Unsubscribed':'Unconfirmed'
 async function unsubscribe(){
  if(!window.confirm(`Unsubscribe ${subscriber.email} and invalidate any pending confirmation?`))return
  setBusy(true);setError('');setMessage('')
  try{await api.post(`/newsletter/${subscriber.id}/unsubscribe/`);await refresh();setMessage('Unsubscribed.')}
  catch(e){setError(errorMessage(e))}finally{setBusy(false)}
 }
 return <tr><td>{subscriber.email}</td><td>{state}</td><td>{subscriber.confirmed_at?new Date(subscriber.confirmed_at).toLocaleDateString():'—'}</td><td>{new Date(subscriber.created_at).toLocaleDateString()}</td><td>{(subscriber.is_active||subscriber.confirmation_sent_at)&&<button type="button" className="admin-link" disabled={busy} onClick={unsubscribe}>UNSUBSCRIBE</button>}{message&&<span className="admin-note" role="status">{message}</span>}{error&&<span className="form-error" role="alert">{error}</span>}</td></tr>
}
export default function Marketing(){
 const qc=useQueryClient()
 const [code,setCode]=useState('');const [kind,setKind]=useState('percent');const [value,setValue]=useState('');const [minimum,setMinimum]=useState('0');const [limit,setLimit]=useState('');const [expires,setExpires]=useState('');const [busy,setBusy]=useState(false);const [message,setMessage]=useState('');const [error,setError]=useState('')
 const [couponSearch,setCouponSearch]=useState('');const [couponPage,setCouponPage]=useState(1)
 const [subscriberSearch,setSubscriberSearch]=useState('');const [subscriberPage,setSubscriberPage]=useState(1)
 const coupons=useQuery({queryKey:['admin-coupons',couponSearch,couponPage],queryFn:()=>api.get<Page<Coupon>>('/coupons/',{params:{search:couponSearch,page:couponPage}}).then(r=>r.data)})
 const subscribers=useQuery({queryKey:['admin-subscribers',subscriberSearch,subscriberPage],queryFn:()=>api.get<Page<Subscriber>>('/newsletter/',{params:{search:subscriberSearch,page:subscriberPage}}).then(r=>r.data)})
 const refreshCoupons=()=>qc.invalidateQueries({queryKey:['admin-coupons']})
 const refreshSubscribers=()=>qc.invalidateQueries({queryKey:['admin-subscribers']})
 async function save(e:React.FormEvent){
  e.preventDefault();setBusy(true);setMessage('');setError('')
  try{
   await api.post('/coupons/',{code:code.toUpperCase(),discount_type:kind,discount_value:value,minimum_order:minimum,usage_limit:limit?Number(limit):null,expires_at:expires?new Date(expires).toISOString():null,is_active:true})
   setCode('');setValue('');setMinimum('0');setLimit('');setExpires('');setMessage('Discount code created.');await refreshCoupons()
  }catch(e){setError(errorMessage(e))}finally{setBusy(false)}
 }
 return <div>
  <div className="admin-topline"><span>GROWTH</span><span>MARKETING</span></div><span className="eyebrow">PROMOTIONS</span><h1 className="page-title">Marketing.</h1><p className="summary-note">Manage discount codes and newsletter consent.</p>
  {message&&<p className="form-success" role="status">{message}</p>}{error&&<p className="form-error" role="alert">{error}</p>}
  <div className="admin-panel">
   <div className="admin-panel-head"><h2>Discount codes</h2><span>{coupons.data?.count??0} CODES</span></div>
   <div className="admin-toolbar"><label htmlFor="coupon-search" className="admin-note">Search codes</label><input id="coupon-search" value={couponSearch} onChange={e=>{setCouponSearch(e.target.value);setCouponPage(1)}} placeholder="Search code"/></div>
   {coupons.error&&<div className="error-box" role="alert">{errorMessage(coupons.error)}</div>}
   <div className="table-wrap" style={{marginTop:18}}><table className="data-table"><thead><tr><th>CODE</th><th>DISCOUNT</th><th>USES</th><th>STATUS</th><th>ACTIONS</th></tr></thead><tbody>{coupons.data?.results.map(c=><CouponRow key={c.id} coupon={c} refresh={refreshCoupons}/>)}</tbody></table></div>
   {coupons.data&&!coupons.data.results.length&&<p className="admin-note">No matching codes.</p>}
   {(couponPage>1||coupons.data?.next)&&<div className="pagination"><button type="button" disabled={couponPage===1||coupons.isFetching} onClick={()=>setCouponPage(p=>p-1)}>PREVIOUS CODES</button><button type="button" disabled={!coupons.data?.next||coupons.isFetching} onClick={()=>setCouponPage(p=>p+1)}>NEXT CODES</button></div>}
   <form onSubmit={save} style={{marginTop:25}}><h3>Create a code</h3><div className="admin-form-grid">
    <div className="field"><label htmlFor="coupon-code">Code</label><input id="coupon-code" required maxLength={50} pattern="[A-Za-z0-9_-]+" value={code} onChange={e=>setCode(e.target.value)}/></div>
    <div className="field"><label htmlFor="coupon-kind">Discount type</label><select id="coupon-kind" value={kind} onChange={e=>setKind(e.target.value)}><option value="percent">Percentage</option><option value="fixed">Fixed amount</option></select></div>
    <div className="field"><label htmlFor="coupon-value">Value</label><input id="coupon-value" type="number" min="0" max={kind==='percent'?100:undefined} step="0.01" required value={value} onChange={e=>setValue(e.target.value)}/></div>
    <div className="field"><label htmlFor="coupon-minimum">Minimum order (EUR)</label><input id="coupon-minimum" type="number" min="0" step="0.01" required value={minimum} onChange={e=>setMinimum(e.target.value)}/></div>
    <div className="field"><label htmlFor="coupon-limit">Usage limit (optional)</label><input id="coupon-limit" type="number" min="1" step="1" value={limit} onChange={e=>setLimit(e.target.value)}/></div>
    <div className="field"><label htmlFor="coupon-expiry">Expires at (optional)</label><input id="coupon-expiry" type="datetime-local" value={expires} onChange={e=>setExpires(e.target.value)}/></div>
   </div><button className="button button-dark" disabled={busy}>{busy?'SAVING…':'CREATE CODE'}</button></form>
  </div>
  <div className="admin-panel">
   <div className="admin-panel-head"><h2>Newsletter addresses</h2><span>{subscribers.data?.count??0} ADDRESSES</span></div>
   <p className="admin-note">Only confirmed addresses are active. New requests require email confirmation; no campaign-sending tool is included.</p>
   <div className="admin-toolbar"><label htmlFor="subscriber-search" className="admin-note">Search addresses</label><input id="subscriber-search" value={subscriberSearch} onChange={e=>{setSubscriberSearch(e.target.value);setSubscriberPage(1)}} placeholder="Search email"/></div>
   {subscribers.error&&<div className="error-box" role="alert">{errorMessage(subscribers.error)}</div>}
   <div className="table-wrap" style={{marginTop:18}}><table className="data-table"><thead><tr><th>EMAIL</th><th>STATUS</th><th>CONFIRMED</th><th>REQUESTED</th><th>ACTIONS</th></tr></thead><tbody>{subscribers.data?.results.map(s=><SubscriberRow key={s.id} subscriber={s} refresh={refreshSubscribers}/>)}</tbody></table></div>
   {subscribers.data&&!subscribers.data.results.length&&<p className="admin-note">No matching addresses.</p>}
   {(subscriberPage>1||subscribers.data?.next)&&<div className="pagination"><button type="button" disabled={subscriberPage===1||subscribers.isFetching} onClick={()=>setSubscriberPage(p=>p-1)}>PREVIOUS ADDRESSES</button><button type="button" disabled={!subscribers.data?.next||subscribers.isFetching} onClick={()=>setSubscriberPage(p=>p+1)}>NEXT ADDRESSES</button></div>}
  </div>
 </div>
}
