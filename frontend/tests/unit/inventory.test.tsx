import {beforeEach,describe,expect,it,vi} from 'vitest'
import {render,screen} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import Inventory from '@/app/admin/inventory/page'
import type {Product} from '@/lib/types'

const mocks=vi.hoisted(()=>({get:vi.fn(),post:vi.fn()}))
vi.mock('@/lib/api',()=>({api:{get:mocks.get,post:mocks.post},errorMessage:(e:unknown)=>(e as {response?:{data?:{detail?:string}}})?.response?.data?.detail||'Error'}))
const product=(id:number,stock:number):Product=>({id,name:`Product ${id}`,slug:`product-${id}`,sku:`SKU-${id}`,price:'20.00',compare_at_price:null,stock,brand_name:'ELVAA',category_name:'',category_slug:'',category:null,brand:null,description:'',specifications:{},images:[],variants:[],is_active:true,is_featured:false,is_new:false,avg_rating:null,review_count:0,created_at:''})
const p1=product(1,2),p25=product(25,4)
function renderPage(){const queryClient=new QueryClient({defaultOptions:{queries:{retry:false}}});return render(<QueryClientProvider client={queryClient}><Inventory/></QueryClientProvider>)}

describe('Inventory adjustment',()=>{
 beforeEach(()=>{
  mocks.get.mockReset();mocks.post.mockReset()
  mocks.get.mockImplementation(async(url:string,config?:{params?:{page?:number;search?:string}})=>{
   if(url==='/inventory-movements/')return {data:{count:0,next:null,previous:null,results:[]}}
   if(url==='/products/product-25/')return {data:product(25,3)}
   if(url==='/products/'){
    if(config?.params?.search)return {data:{count:1,next:null,previous:null,results:[p25]}}
    if(config?.params?.page===2)return {data:{count:25,next:null,previous:'previous',results:[p25]}}
    return {data:{count:25,next:'next',previous:null,results:[p1]}}
   }
   throw new Error(`Unexpected URL ${url}`)
  })
 })
 it('finds a product beyond the first page and requires a refresh after a conflict',async()=>{
  const user=userEvent.setup();renderPage()
  await screen.findByText('25 products found · Page 1')
  await user.click(screen.getByRole('button',{name:'NEXT PRODUCTS'}))
  await screen.findByRole('option',{name:/Product 25/})
  await user.selectOptions(screen.getByLabelText('Product'),'25')
  await user.type(screen.getByLabelText('New stock quantity'),'6')
  await user.type(screen.getByLabelText('Reason'),'Counted stock')
  mocks.post.mockRejectedValueOnce({isAxiosError:true,response:{status:409,data:{detail:'Stock changed. Refresh before adjusting.'}}})
  await user.click(screen.getByRole('button',{name:'RECORD ADJUSTMENT'}))
  expect(await screen.findByRole('alert')).toHaveTextContent('Stock changed')
  expect(mocks.post).toHaveBeenCalledWith('/inventory-adjustments/',{product_id:25,variant_id:null,expected_stock:4,new_stock:6,reason:'Counted stock'})
  expect(screen.getByRole('button',{name:'RECORD ADJUSTMENT'})).toBeDisabled()
  await user.click(screen.getByRole('button',{name:'REFRESH STOCK'}))
  await screen.findByText(/Stock refreshed/)
  expect(screen.getByText(/Last observed product quantity/)).toHaveTextContent('3')
  expect(screen.getByLabelText('New stock quantity')).toHaveValue(null)
  await user.type(screen.getByLabelText('New stock quantity'),'5')
  mocks.post.mockResolvedValueOnce({data:{}})
  await user.click(screen.getByRole('button',{name:'RECORD ADJUSTMENT'}))
  await screen.findByText('Stock adjustment recorded.')
  expect(mocks.post).toHaveBeenLastCalledWith('/inventory-adjustments/',{product_id:25,variant_id:null,expected_stock:3,new_stock:5,reason:'Counted stock'})
 })
 it('searches server-side and preserves the selected product when the result page changes',async()=>{
  const user=userEvent.setup();renderPage();await screen.findByText('25 products found · Page 1')
  await user.selectOptions(screen.getByLabelText('Product'),'1')
  await user.type(screen.getByLabelText('Find product'),'SKU-25')
  await user.click(screen.getByRole('button',{name:'SEARCH'}))
  await screen.findByText('1 product found · Page 1')
  expect(screen.getByLabelText('Product')).toHaveValue('1')
  expect(screen.getByRole('option',{name:/Product 1.*selected/})).toBeInTheDocument()
  expect(screen.getByRole('option',{name:/Product 25/})).toBeInTheDocument()
 })
})
