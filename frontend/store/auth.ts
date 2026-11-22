import {create} from 'zustand'
import type {User} from '@/lib/types'
type AuthState={access:string|null;user:User|null;initialized:boolean;setSession:(access:string,user:User)=>void;clearSession:()=>void;setInitialized:()=>void}
// Access token stays in memory. The rotating refresh token is an HttpOnly cookie.
export const useAuth=create<AuthState>((set)=>({access:null,user:null,initialized:false,
  setSession:(access,user)=>set({access,user,initialized:true}),
  clearSession:()=>set({access:null,user:null,initialized:true}),setInitialized:()=>set({initialized:true})}))
