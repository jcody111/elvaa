import type {Metadata} from 'next'
import {serverProduct} from '@/lib/server-api'
import ProductDetails from '@/components/ProductDetails'
type Props={params:Promise<{slug:string}>}
export async function generateMetadata({params}:Props):Promise<Metadata>{const {slug}=await params;const p=await serverProduct(slug);return p?{title:p.name,description:p.description,openGraph:{title:`${p.name} | ELVAA`,description:p.description,images:p.images[0]?.image?[p.images[0].image]:[]}}:{title:'Product'}}
export default async function ProductPage({params}:Props){const {slug}=await params;const product=await serverProduct(slug);return <ProductDetails slug={slug} initialProduct={product}/>}
