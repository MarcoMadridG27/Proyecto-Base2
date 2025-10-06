"use client"

import { cn } from "@/lib/utils"
import { useEffect, useState } from "react"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Database, FileText, Search, Map, TrendingUp, Clock } from "lucide-react"
import Link from "next/link"
import { Button } from "@/components/ui/button"

type SystemStats = {
  total_records: number
  total_tables: number
  total_indexes: number
  tables: string[]
}

export function Dashboard() {
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch("http://localhost:8000/system_stats")
        const data = await res.json()
        if (data.ok) {
          setStats(data.stats)
        }
      } catch (err) {
        console.error("Failed to fetch stats:", err)
      } finally {
        setLoading(false)
      }
    }
    fetchStats()
  }, [])

  const statsCards = [
    {
      title: "Total Records",
      value: stats ? stats.total_records.toLocaleString() : "Loading...",
      change: "+0%",
      icon: Database,
      color: "text-primary",
    },
    {
      title: "Tables",
      value: stats ? stats.total_tables.toString() : "Loading...",
      change: "+0",
      icon: FileText,
      color: "text-secondary",
    },
    {
      title: "Indexes",
      value: stats ? stats.total_indexes.toString() : "Loading...",
      icon: Search,
      color: "text-blue-400",
    },
    {
      title: "Active Tables",
      value: stats ? stats.tables.length.toString() : "Loading...",
      change: stats ? stats.tables.join(", ") : "",
      icon: Map,
      color: "text-emerald-400",
    },
  ]

  const recentActivity = [
    { action: "System initialized", file: "Backend connected", time: "Just now" },
    { action: "Tables loaded", file: stats ? stats.tables.join(", ") : "Loading...", time: "Just now" },
    { action: "Indexes ready", file: stats ? `${stats.total_indexes} indexes` : "Loading...", time: "Just now" },
    { action: "Database ready", file: "All systems operational", time: "Just now" },
  ]
  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="animate-fade-in">
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-foreground/70 bg-clip-text text-transparent">
          Dashboard
        </h1>
        <p className="text-muted-foreground mt-2">Welcome to the UTEC Multimodal Database Management System</p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {statsCards.map((stat, index) => (
          <Card
            key={stat.title}
            className={cn(
              "glass-card border-white/10 hover:shadow-xl hover:shadow-primary/10 hover:scale-105 transition-all duration-300 animate-scale-in",
              `stagger-${index + 1}`,
            )}
          >
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{stat.title}</CardTitle>
              <stat.icon className={cn("h-5 w-5 transition-transform hover:scale-125 duration-300", stat.color)} />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stat.value}</div>
              <div className="flex items-center gap-1 mt-2">
                <TrendingUp className="h-3 w-3 text-secondary" />
                <span className="text-xs text-secondary font-semibold">{stat.change}</span>
                <span className="text-xs text-muted-foreground">from last week</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick Actions */}
      <Card className="glass-card border-white/10 animate-fade-in hover:shadow-xl hover:shadow-primary/5 transition-all duration-300">
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>Common tasks and operations</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Link href="/upload">
              <Button
                variant="outline"
                className="w-full h-24 flex flex-col gap-2 bg-transparent hover:bg-gradient-to-br hover:from-primary/10 hover:to-transparent hover:scale-105 hover:shadow-lg hover:shadow-primary/20 transition-all duration-300"
              >
                <FileText className="h-6 w-6" />
                <span>Upload CSV</span>
              </Button>
            </Link>
            <Link href="/query">
              <Button
                variant="outline"
                className="w-full h-24 flex flex-col gap-2 bg-transparent hover:bg-gradient-to-br hover:from-primary/10 hover:to-transparent hover:scale-105 hover:shadow-lg hover:shadow-primary/20 transition-all duration-300"
              >
                <Database className="h-6 w-6" />
                <span>Run Query</span>
              </Button>
            </Link>
            <Link href="/indexes">
              <Button
                variant="outline"
                className="w-full h-24 flex flex-col gap-2 bg-transparent hover:bg-gradient-to-br hover:from-primary/10 hover:to-transparent hover:scale-105 hover:shadow-lg hover:shadow-primary/20 transition-all duration-300"
              >
                <Search className="h-6 w-6" />
                <span>Explore Indexes</span>
              </Button>
            </Link>
            <Link href="/spatial">
              <Button
                variant="outline"
                className="w-full h-24 flex flex-col gap-2 bg-transparent hover:bg-gradient-to-br hover:from-secondary/10 hover:to-transparent hover:scale-105 hover:shadow-lg hover:shadow-secondary/20 transition-all duration-300"
              >
                <Map className="h-6 w-6" />
                <span>Spatial Search</span>
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card className="glass-card border-white/10 animate-fade-in hover:shadow-xl hover:shadow-primary/5 transition-all duration-300">
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>Latest operations and changes</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {recentActivity.map((activity, index) => (
              <div
                key={index}
                className={cn(
                  "flex items-start gap-4 rounded-lg border border-white/5 bg-white/5 p-4 hover:bg-white/10 hover:border-white/20 hover:scale-[1.02] transition-all duration-300 animate-fade-in",
                  `stagger-${index + 1}`,
                )}
              >
                <Clock className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div className="flex-1 space-y-1">
                  <p className="text-sm font-medium">{activity.action}</p>
                  <p className="text-sm text-muted-foreground font-mono">{activity.file}</p>
                </div>
                <span className="text-xs text-muted-foreground">{activity.time}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
