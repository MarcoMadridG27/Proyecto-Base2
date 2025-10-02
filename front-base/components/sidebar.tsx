"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutDashboard, Upload, Database, Network, Map, GraduationCap } from "lucide-react"
import { cn } from "@/lib/utils"

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "File Upload", href: "/upload", icon: Upload },
  { name: "SQL Query", href: "/query", icon: Database },
  { name: "Index Explorer", href: "/indexes", icon: Network },
  { name: "Spatial Results", href: "/spatial", icon: Map },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-64 border-r border-border bg-sidebar/95 backdrop-blur-xl">
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center gap-3 border-b border-border px-6 animate-fade-in">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-primary/80 shadow-lg shadow-primary/30 animate-glow-pulse">
            <GraduationCap className="h-6 w-6 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-lg font-semibold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
              UTEC DB
            </h1>
            <p className="text-xs text-muted-foreground">Multimodal System</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-4">
          {navigation.map((item, index) => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-300 animate-slide-in-left",
                  `stagger-${index + 1}`,
                  isActive
                    ? "bg-gradient-to-r from-primary to-primary/90 text-primary-foreground shadow-lg shadow-primary/30 scale-105"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground hover:scale-105 hover:shadow-md",
                )}
              >
                <item.icon className={cn("h-5 w-5 transition-transform", isActive && "scale-110")} />
                {item.name}
              </Link>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="border-t border-border p-4 animate-fade-in">
          <div className="glass-card rounded-lg p-3 hover:shadow-lg hover:shadow-secondary/20 transition-all duration-300">
            <p className="text-xs font-medium text-foreground">Database Status</p>
            <div className="mt-2 flex items-center gap-2">
              <div className="relative">
                <div className="h-2 w-2 rounded-full bg-secondary animate-pulse" />
                <div className="absolute inset-0 h-2 w-2 rounded-full bg-secondary/50 animate-ping" />
              </div>
              <span className="text-xs text-muted-foreground">Connected</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}
