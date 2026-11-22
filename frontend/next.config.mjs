/** @type {import('next').NextConfig} */
if (process.env.NODE_ENV === 'production' && !process.env.API_UPSTREAM) throw new Error('API_UPSTREAM must be set for a production build.');
const upstream = (process.env.API_UPSTREAM || 'http://127.0.0.1:8000').replace(/\/$/, '');
const nextConfig = {
  skipTrailingSlashRedirect: true,
  allowedDevOrigins: ['*.e2b.app'],
  images: { remotePatterns: [{ protocol: 'https', hostname: '**' }] },
  async rewrites() { return [
    { source: '/api/:path*', destination: `${upstream}/api/:path*/` },
    { source: '/media/:path*', destination: `${upstream}/media/:path*` },
  ]; },
  async headers() { return [{ source: '/:path*', headers: [
    {key:'X-Content-Type-Options',value:'nosniff'},
    {key:'Referrer-Policy',value:'strict-origin-when-cross-origin'},
  ]}]; },
};
export default nextConfig;
