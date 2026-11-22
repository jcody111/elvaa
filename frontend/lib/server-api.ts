import type {Product} from './types'
const upstream=(process.env.API_UPSTREAM||'http://127.0.0.1:8000').replace(/\/$/,'')
export async function serverProduct(slug:string):Promise<Product|null>{
 try{const r=await fetch(`${upstream}/api/v1/products/${encodeURIComponent(slug)}/`,{cache:'no-store'});if(!r.ok)return null;return await r.json()}catch{return null}
}
