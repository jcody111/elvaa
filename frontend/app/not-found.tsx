import Link from 'next/link'
export default function NotFound(){return <div className="empty-bag" style={{padding:'110px 20px'}}><span className="eyebrow">404</span><h2>We seem to have wandered off.</h2><p>Let’s find our way back to something beautiful.</p><Link className="button button-dark" href="/">RETURN HOME</Link></div>}
