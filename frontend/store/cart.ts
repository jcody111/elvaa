import {create} from 'zustand'
import {persist} from 'zustand/middleware'
import type {Product,Variant} from '@/lib/types'
export interface CartItem {key:string;productId:number;variantId:number|null;variantName:string;slug:string;name:string;price:number;image:string;quantity:number;stock:number}
type CartState={items:CartItem[];couponCode:string;setCoupon:(code:string)=>void;add:(product:Product,variant:Variant|null,quantity:number)=>boolean;remove:(key:string)=>void;update:(key:string,quantity:number)=>void;clear:()=>void}
export const useCart=create<CartState>()(persist((set,get)=>({
  items:[],couponCode:'',setCoupon:(code)=>set({couponCode:code}),
  add:(p,v,qty)=>{const key=`${p.id}-${v?.id||0}`;const stock=Math.min(p.stock,v?.stock??p.stock);const old=get().items.find(i=>i.key===key)
    if(qty<1 || qty+(old?.quantity||0)>stock || qty+(old?.quantity||0)>20)return false
    if(old)set({items:get().items.map(i=>i.key===key?{...i,quantity:i.quantity+qty}:i)})
    else set({items:[...get().items,{key,productId:p.id,variantId:v?.id||null,variantName:v?.name||'',slug:p.slug,name:p.name,price:Number(v?.price??p.price),image:p.images[0]?.image||'',quantity:qty,stock}]})
    return true},
  remove:key=>set(s=>({items:s.items.filter(i=>i.key!==key)})),
  update:(key,quantity)=>set(s=>({items:s.items.map(i=>i.key===key?{...i,quantity:Math.min(20,i.stock,Math.max(1,quantity||1))}:i)})),
  clear:()=>set({items:[],couponCode:''})
}),{name:'elvaa-cart-v2'}))
