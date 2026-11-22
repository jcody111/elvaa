import {describe,it,expect,vi} from 'vitest'
import {render,screen} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Newsletter from '@/components/Newsletter'
const post=vi.fn().mockResolvedValue({data:{detail:'If eligible, please check your inbox for a confirmation link.'}})
vi.mock('@/lib/api',()=>({api:{post:(...args:unknown[])=>post(...args)},errorMessage:()=> 'Error'}))
describe('Newsletter',()=>{it('submits the email and confirms success',async()=>{render(<Newsletter/>);await userEvent.type(screen.getByLabelText('Email address'),'reader@example.com');await userEvent.click(screen.getByRole('button',{name:'Subscribe to newsletter'}));expect(post).toHaveBeenCalledWith('/newsletter/',{email:'reader@example.com'});expect(await screen.findByText('If eligible, please check your inbox for a confirmation link.')).toBeInTheDocument()})})
