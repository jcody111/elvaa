import {beforeEach,describe,expect,it,vi} from 'vitest'
import {render,screen} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import NewsletterAction from '@/components/NewsletterAction'
const mocks=vi.hoisted(()=>({post:vi.fn()}))
vi.mock('next/link',()=>({default:({children,href}:{children:React.ReactNode;href:string})=><a href={href}>{children}</a>}))
vi.mock('@/lib/api',()=>({api:{post:mocks.post},errorMessage:()=> 'The link is invalid or has expired.'}))

describe('Newsletter confirmation links',()=>{
 beforeEach(()=>{mocks.post.mockReset();window.history.replaceState(null,'','/newsletter/confirm#token=secret-token')})
 it('does not confirm on page load and removes the token after a deliberate confirmation',async()=>{
  mocks.post.mockResolvedValueOnce({data:{detail:'Your newsletter subscription is confirmed.'}})
  render(<NewsletterAction action="confirm"/>);expect(mocks.post).not.toHaveBeenCalled()
  await userEvent.click(screen.getByRole('button',{name:'CONFIRM SUBSCRIPTION'}))
  expect(mocks.post).toHaveBeenCalledWith('/newsletter/confirm/',{token:'secret-token'})
  expect(await screen.findByRole('status')).toHaveTextContent('subscription is confirmed')
  expect(window.location.hash).toBe('')
 })
 it('keeps the token on failure so the user can retry',async()=>{
  mocks.post.mockRejectedValueOnce(new Error('offline'))
  render(<NewsletterAction action="unsubscribe"/>);await userEvent.click(screen.getByRole('button',{name:'UNSUBSCRIBE'}))
  expect(await screen.findByRole('alert')).toHaveTextContent('invalid or has expired')
  expect(window.location.hash).toBe('#token=secret-token')
 })
})
