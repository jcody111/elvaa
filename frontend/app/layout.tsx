import './globals.css'
import type {Metadata} from 'next'
import Providers from '@/components/Providers'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
export const metadata:Metadata={metadataBase:new URL(process.env.NEXT_PUBLIC_SITE_URL||'https://example.com'),title:{default:'ELVAA | Thoughtfully Made for Every Day',template:'%s | ELVAA'},description:'Thoughtfully designed pieces for the everyday. Discover elevated essentials, timeless tailoring and accessories from ELVAA.',openGraph:{title:'ELVAA | Thoughtfully Made for Every Day',description:'Considered essentials for a life well lived.',type:'website'}}
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body><a className="skip-link" href="#main">Skip to content</a><Providers><Header/><main id="main">{children}</main><Footer/></Providers></body></html>}
