"use client"

import { cn } from "@/lib/utils"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Database, FileText, Search, Map, TrendingUp, Clock } from "lucide-react"
import Link from "next/link"
import { Button } from "@/components/ui/button"

const stats = [
  {
    title: "Total Records",
    value: "1,234,567",
    change: "+12.5%",
    icon: Database,
    color: "text-primary",
  },
  {
    title: "Files Uploaded",
    value: "89",
    change: "+3",
    icon: FileText,
    color: "text-secondary",
  },
  {
    title: "Queries Executed",
    value: "456",
    change: "+23",
    icon: Search,
    color: "text-blue-400",
  },
  {
    title: "Spatial Points",
    value: "12,345",
    change: "+156",
    icon: Map,
    color: "text-emerald-400",
  },
]

const recentActivity = [
  { action: "CSV file uploaded", file: "customers.csv", time: "2 minutes ago" },
  { action: "SQL query executed", file: "SELECT * FROM users", time: "15 minutes ago" },
  { action: "Index created", file: "B+ Tree on user_id", time: "1 hour ago" },
  { action: "Spatial search", file: "Lima region query", time: "2 hours ago" },
]

export function Dashboard() {
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
        {stats.map((stat, index) => (
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
