/** @type {import('next').NextConfig} */
const nextConfig = {
  // 生产环境使用静态导出
  output: process.env.NODE_ENV === 'production' ? 'export' : undefined,

  // 开发环境使用 rewrites
  async rewrites() {
    // 生产环境不需要 rewrites (静态文件由 FastAPI 托管)
    if (process.env.NODE_ENV === 'production') {
      return []
    }

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
