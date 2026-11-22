import Link from 'next/link'
export default function Logo({inverse=false}:{inverse?:boolean}){return <Link href="/" className={`wordmark ${inverse?'wordmark-light':''}`} aria-label="ELVAA home">ELVAA<span className="wordmark-dot">.</span></Link>}
