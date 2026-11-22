import {beforeEach,describe,expect,it,vi} from 'vitest'
import {render,screen} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Cancel from '@/app/checkout/cancel/page'
const mocks=vi.hoisted(()=>({post:vi.fn()}))
vi.mock('next/link',()=>({default:({children,href}:{children:React.ReactNode;href:string})=><a href={href}>{children}</a>}))
vi.mock('@/lib/api',()=>({api:{post:mocks.post},errorMessage:()=> 'Payment state could not be confirmed.'}))

describe('checkout cancellation',()=>{
 beforeEach(()=>{sessionStorage.clear();mocks.post.mockReset()})
 it('keeps the checkout key when the provider cannot confirm cancellation',async()=>{
  sessionStorage.setItem('elvaa-checkout-key','test-key');mocks.post.mockRejectedValueOnce(new Error('offline'))
  render(<Cancel/>);await userEvent.click(screen.getByRole('button',{name:'CANCEL PAYMENT SESSION'}))
  expect(await screen.findByRole('alert')).toHaveTextContent('could not be confirmed')
  expect(sessionStorage.getItem('elvaa-checkout-key')).toBe('test-key')
 })
 it('clears the key only after the server confirms cancellation',async()=>{
  sessionStorage.setItem('elvaa-checkout-key','test-key');mocks.post.mockResolvedValueOnce({data:{status:'cancelled'}})
  render(<Cancel/>);await userEvent.click(screen.getByRole('button',{name:'CANCEL PAYMENT SESSION'}))
  expect(await screen.findByText(/reservation released/)).toBeInTheDocument()
  expect(mocks.post).toHaveBeenCalledWith('/checkout/cancel/',{idempotency_key:'test-key'})
  expect(sessionStorage.getItem('elvaa-checkout-key')).toBeNull()
 })
})
