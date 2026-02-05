import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "Yijie STRM Gateway",
  description: "多网盘 STRM 文件管理系统",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body className="font-sans antialiased">{children}</body>
    </html>
  )
}
