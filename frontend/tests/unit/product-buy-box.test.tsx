import {describe,it,expect,beforeEach,vi} from 'vitest'
import {render,screen} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ProductBuyBox from '@/components/ProductBuyBox'
import {useCart} from '@/store/cart'
import type {Product} from '@/lib/types'
vi.mock('next/link',()=>({default:({children,href}:{children:React.ReactNode;href:string})=><a href={href}>{children}</a>}))
vi.mock('@/components/WishlistButton',()=>({default:()=> <button aria-label="wishlist"/>}))
const product:Product={id:1,name:'Studio Blazer',slug:'studio-blazer',sku:'SKU',price:'100.00',compare_at_price:null,stock:3,brand_name:'ELVAA',category_name:'Tailoring',category_slug:'tailoring',category:1,brand:1,description:'A blazer.',specifications:{Colour:'Oat'},images:[],variants:[{id:2,product:1,name:'M',sku:'SKU-M',price:null,stock:2,attributes:{size:'M'}}],is_active:true,is_featured:true,is_new:false,avg_rating:null,review_count:0,created_at:''}
describe('ProductBuyBox',()=>{
 beforeEach(()=>{useCart.setState({items:[],couponCode:''})})
 it('requires a size before adding a variant product',async()=>{render(<ProductBuyBox product={product}/>);await userEvent.click(screen.getByRole('button',{name:/add to bag/i}));expect(screen.getByRole('alert')).toHaveTextContent('Please select a size');expect(useCart.getState().items).toHaveLength(0)})
 it('adds the selected variant to the persistent cart',async()=>{render(<ProductBuyBox product={product}/>);await userEvent.click(screen.getByRole('button',{name:'M'}));await userEvent.click(screen.getByRole('button',{name:/add to bag/i}));expect(useCart.getState().items[0]).toMatchObject({productId:1,variantId:2,quantity:1,price:100})})
 it('does not allow a quantity beyond variant stock',async()=>{useCart.getState().add(product,product.variants[0],2);render(<ProductBuyBox product={product}/>);await userEvent.click(screen.getByRole('button',{name:'M'}));await userEvent.click(screen.getByRole('button',{name:/add to bag/i}));expect(screen.getByRole('alert')).toHaveTextContent('quantity is not available');expect(useCart.getState().items[0].quantity).toBe(2)})
})
