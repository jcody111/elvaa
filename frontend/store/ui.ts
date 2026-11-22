import {create} from 'zustand'
type UI={message:string;show:(message:string)=>void;dismiss:()=>void}
let timeout:ReturnType<typeof setTimeout>
export const useUI=create<UI>((set)=>({message:'',show:(message)=>{clearTimeout(timeout);set({message});timeout=setTimeout(()=>set({message:''}),3500)},dismiss:()=>set({message:''})}))
