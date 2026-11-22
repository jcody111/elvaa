import ProductCard from './ProductCard'
import type {Product} from '@/lib/types'
export default function ProductGrid({products}:{products:Product[]}){return <div className="product-grid">{products.map(p=><ProductCard key={p.id} p={p}/>)}</div>}
