import type React from "react"
import { GeistSans } from "geist/font/sans"
import { GeistMono } from "geist/font/mono"
import { Toaster } from "sonner"
import "./globals.css"

export const metadata = {
  title: "UTEC Database System",
  description: "Multimodal Database Management System",
  generator: "v0.app",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable} dark`}>
      <body className="antialiased">
        {children}
        <Toaster position="top-right" theme="dark" />
      </body>
    </html>
  )
}
