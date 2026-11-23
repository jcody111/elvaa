import axios from 'axios'
import {useAuth} from '@/store/auth'
import type {Category,Page,Product,ShippingMethod,Quote} from './types'

// Keep API requests same-origin for the refresh and CSRF cookies.
export const api=axios.create({baseURL:'/api/v1',withCredentials:true,withXSRFToken:true,
  xsrfCookieName:'csrftoken',xsrfHeaderName:'X-CSRFToken',timeout:15000})
api.interceptors.request.use(config=>{const token=useAuth.getState().access;if(token)config.headers.Authorization=`Bearer ${token}`;return config})
let refreshing:Promise<string>|null=null
function refreshAccess():Promise<string>{
  if(!refreshing) refreshing=api.post('/auth/refresh/').then(r=>{useAuth.getState().setSession(r.data.access,r.data.user);return r.data.access as string}).finally(()=>{refreshing=null})
  return refreshing
}
api.interceptors.response.use(response=>response,async error=>{
  const config=error.config
  if(error.response?.status===401 && config && !config._retried && !String(config.url).includes('/auth/')){
    config._retried=true
    try {const token=await refreshAccess();config.headers.Authorization=`Bearer ${token}`;return api(config)}
    catch {useAuth.getState().clearSession()}
  }
  return Promise.reject(error)
})
let restoring:Promise<void>|null=null
export function restoreSession(){
  if(!restoring) restoring=(async()=>{try { const response=await api.get<{has_session:boolean}>('/auth/csrf/'); if(response.data.has_session) await refreshAccess(); else useAuth.getState().clearSession() } catch {useAuth.getState().clearSession()}})().finally(()=>{restoring=null})
  return restoring
}
export const fetchProducts=(params:Record<string,unknown>={})=>api.get<Page<Product>>('/products/',{params}).then(r=>r.data)
export const fetchProduct=(slug:string)=>api.get<Product>(`/products/${encodeURIComponent(slug)}/`).then(r=>r.data)
export const fetchRelated=(slug:string)=>api.get<Product[]>(`/products/${encodeURIComponent(slug)}/related/`).then(r=>r.data)
export const fetchCategories=()=>api.get<Page<Category>>('/categories/').then(r=>r.data)
export const fetchShipping=()=>api.get<Page<ShippingMethod>>('/shipping-methods/').then(r=>r.data)
export const fetchQuote=(body:unknown)=>api.post<Quote>('/cart/quote/',body).then(r=>r.data)
export function errorMessage(error:unknown):string{
  if(axios.isAxiosError(error)){
    const d=error.response?.data
    if(typeof d?.detail==='string')return d.detail
    if(d&&typeof d==='object'){
      const values=Object.values(d).flat(Infinity).filter(v=>typeof v==='string')
      if(values.length)return values.join(' ')
    }
    if(!error.response)return 'Unable to connect. Please try again.'
  }
  return 'Something went wrong. Please try again.'
}
