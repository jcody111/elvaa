'use client'
import {useState} from 'react'
import axios from 'axios'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import {api,errorMessage} from '@/lib/api'
import type {Page,Product} from '@/lib/types'

type Movement={id:number;product_name:string;variant_name:string;quantity_change:number;reason:string;reference:string;actor_name:string;created_at:string}

export default function Inventory(){
 const qc=useQueryClient()
 const [searchInput,setSearchInput]=useState('')
 const [search,setSearch]=useState('')
 const [productPage,setProductPage]=useState(1)
 const [selected,setSelected]=useState<Product|null>(null)
 const [variant,setVariant]=useState('')
 const [stock,setStock]=useState('')
 const [reason,setReason]=useState('')
 const [message,setMessage]=useState('')
 const [error,setError]=useState('')
 const [conflict,setConflict]=useState(false)
 const [busy,setBusy]=useState(false)
 const [page,setPage]=useState(1)
 const products=useQuery({queryKey:['inventory-products',search,productPage],queryFn:()=>api.get<Page<Product>>('/products/',{params:{search,page:productPage,ordering:'name'}}).then(r=>r.data)})
 const history=useQuery({queryKey:['inventory-history',page],queryFn:()=>api.get<Page<Movement>>('/inventory-movements/',{params:{page}}).then(r=>r.data)})
 const options=products.data?.results||[]
 const selectedOutsidePage=selected&&!options.some(p=>p.id===selected.id)
 const selectedVariant=variant?selected?.variants.find(v=>v.id===Number(variant)):null
 // Keep the quantity the operator actually saw. Do not silently replace it on a background refetch.
 const expected=variant?selectedVariant?.stock:selected?.stock

 function chooseProduct(id:string){
  const product=options.find(p=>p.id===Number(id))||(selected?.id===Number(id)?selected:null)
  setSelected(product||null);setVariant('');setStock('');setConflict(false);setError('');setMessage('')
 }
 async function refreshSelection(){
  if(!selected)return
  setBusy(true);setError('');setMessage('')
  try{
   const fresh=(await api.get<Product>(`/products/${encodeURIComponent(selected.slug)}/`)).data
   setSelected(fresh)
   if(variant&&!fresh.variants.some(v=>v.id===Number(variant)))setVariant('')
   setStock('');setConflict(false);setMessage('Stock refreshed. Review the current quantity and enter a new quantity.')
   await qc.invalidateQueries({queryKey:['inventory-products']})
  }catch(e){setError(errorMessage(e))}finally{setBusy(false)}
 }
 async function adjust(e:React.FormEvent){
  e.preventDefault()
  if(!selected||expected===undefined||conflict||busy)return
  setBusy(true);setError('');setMessage('')
  try{
   const nextStock=Number(stock)
   await api.post('/inventory-adjustments/',{product_id:selected.id,variant_id:variant?Number(variant):null,expected_stock:expected,new_stock:nextStock,reason})
   setSelected(p=>p?variant?{...p,variants:p.variants.map(v=>v.id===Number(variant)?{...v,stock:nextStock}:v)}:{...p,stock:nextStock}:p)
   setMessage('Stock adjustment recorded.');setStock('');setReason('')
   await Promise.all([qc.invalidateQueries({queryKey:['inventory-products']}),qc.invalidateQueries({queryKey:['inventory-history']}),qc.invalidateQueries({queryKey:['admin-products']})])
  }catch(e){
   if(axios.isAxiosError(e)&&e.response?.status===409)setConflict(true)
   setError(errorMessage(e))
  }finally{setBusy(false)}
 }
 return <div>
  <div className="admin-topline"><span>CATALOG</span><span>INVENTORY</span></div>
  <span className="eyebrow">INVENTORY MANAGEMENT</span><h1 className="page-title">Inventory.</h1>
  <p className="summary-note">Adjust stock and review recorded movements.</p>
  <div className="admin-panel">
   <h2 className="page-title" style={{fontSize:25}}>Adjust stock</h2>
   <p className="admin-note">Product and variant quantities are tracked separately and both are checked at checkout. Search by product name or SKU, or browse all pages.</p>
   <form onSubmit={e=>{e.preventDefault();setSearch(searchInput.trim());setProductPage(1)}} className="admin-toolbar" style={{marginTop:20}}>
    <label htmlFor="inv-search" className="admin-note">Find product</label>
    <input id="inv-search" placeholder="Search products or SKU" value={searchInput} onChange={e=>setSearchInput(e.target.value)}/>
    <button type="submit" className="button button-outline">SEARCH</button>
   </form>
   {products.error&&<div className="error-box" role="alert">{errorMessage(products.error)}</div>}
   {products.isLoading?<p className="admin-note">Loading products…</p>:products.data&&<p className="admin-note" role="status">{products.data.count} {products.data.count===1?'product':'products'} found · Page {productPage}</p>}
   {(productPage>1||products.data?.next)&&<div className="pagination" aria-label="Product pages">
    <button type="button" disabled={productPage===1||products.isFetching} onClick={()=>setProductPage(p=>p-1)}>PREVIOUS PRODUCTS</button>
    <button type="button" disabled={!products.data?.next||products.isFetching} onClick={()=>setProductPage(p=>p+1)}>NEXT PRODUCTS</button>
   </div>}
   <form onSubmit={adjust} style={{marginTop:20}}>
    <div className="admin-form-grid">
     <div className="field"><label htmlFor="inv-product">Product</label><select id="inv-product" required value={selected?.id||''} onChange={e=>chooseProduct(e.target.value)}>
      <option value="">Select a product</option>
      {selectedOutsidePage&&<option value={selected.id}>{selected.name} · {selected.stock} in stock (selected)</option>}
      {options.map(p=><option key={p.id} value={p.id}>{p.name} · {p.stock} in stock{p.is_active?'':' · hidden'}</option>)}
     </select></div>
     <div className="field"><label htmlFor="inv-variant">Variant</label><select id="inv-variant" value={variant} disabled={!selected} onChange={e=>{setVariant(e.target.value);setStock('');setConflict(false);setError('');setMessage('')}}>
      <option value="">Product-level stock</option>{selected?.variants.map(v=><option key={v.id} value={v.id}>{v.name} · {v.stock} in stock</option>)}
     </select></div>
     <div className="field"><label htmlFor="inv-stock">New stock quantity</label><input id="inv-stock" type="number" min="0" max="1000000" step="1" required value={stock} onChange={e=>setStock(e.target.value)}/></div>
     <div className="field"><label htmlFor="inv-reason">Reason</label><input id="inv-reason" minLength={3} maxLength={120} required value={reason} onChange={e=>setReason(e.target.value)}/></div>
    </div>
    {selected&&expected!==undefined&&<p className="admin-note">Last observed {variant?'variant':'product'} quantity: <strong>{expected}</strong>. Changes made since selection will require a refresh.</p>}
    <button className="button button-dark" disabled={busy||!selected||expected===undefined||conflict}>{busy?'PLEASE WAIT…':'RECORD ADJUSTMENT'}</button>
    {selected&&<button type="button" className="button button-outline" disabled={busy} onClick={refreshSelection} style={{marginLeft:8}}>REFRESH STOCK</button>}
    {message&&<p className="form-success" role="status">{message}</p>}
    {error&&<p className="form-error" role="alert">{error}</p>}
   </form>
  </div>
  <div className="admin-panel">
   <div className="admin-panel-head"><h2>Movement history</h2><span>{history.data?.count??0} RECORDS</span></div>
   {history.error&&<div className="error-box" role="alert">{errorMessage(history.error)}</div>}
   <div className="table-wrap" style={{marginTop:18}}><table className="data-table"><thead><tr><th>DATE</th><th>PRODUCT</th><th>VARIANT</th><th>CHANGE</th><th>REASON / REFERENCE</th><th>BY</th></tr></thead><tbody>
    {history.data?.results.map(m=><tr key={m.id}><td>{new Date(m.created_at).toLocaleString()}</td><td>{m.product_name}</td><td>{m.variant_name||'Product'}</td><td>{m.quantity_change>0?'+':''}{m.quantity_change}</td><td>{m.reason}{m.reference?` · ${m.reference}`:''}</td><td>{m.actor_name||'System'}</td></tr>)}
   </tbody></table></div>
   {history.data&&!history.data.results.length&&<p className="empty-state">No movements recorded yet.</p>}
   {(page>1||history.data?.next)&&<div className="pagination" aria-label="Movement pages"><button type="button" disabled={page===1||history.isFetching} onClick={()=>setPage(p=>p-1)}>PREVIOUS</button><button type="button" disabled={!history.data?.next||history.isFetching} onClick={()=>setPage(p=>p+1)}>NEXT</button></div>}
  </div>
 </div>
}
