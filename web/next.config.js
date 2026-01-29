/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8115/api/:path*',
      },
      {
        source: '/stream/:path*',
        destination: 'http://localhost:8115/stream/:path*',
      },
    ]
  },
}

module.exports = nextConfig
