"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import { Upload, TrendingUp, BarChart3 } from "lucide-react"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

type BenchmarkData = {
  n: number
  time_spimi?: number
  time_postgresql?: number
  time_knn_sequential?: number
  time_knn_indexed?: number
  time_pgvector?: number
  precision_spimi?: number
  precision_postgresql?: number
  precision_knn_sequential?: number
  precision_knn_indexed?: number
  precision_pgvector?: number
}

const DEMO_TEXT_RETRIEVAL_DATA: BenchmarkData[] = [
  { n: 100, time_spimi: 12, time_postgresql: 25, precision_spimi: 0.92, precision_postgresql: 0.95 },
  { n: 500, time_spimi: 45, time_postgresql: 89, precision_spimi: 0.93, precision_postgresql: 0.94 },
  { n: 1000, time_spimi: 98, time_postgresql: 234, precision_spimi: 0.91, precision_postgresql: 0.95 },
  { n: 5000, time_spimi: 567, time_postgresql: 1234, precision_spimi: 0.90, precision_postgresql: 0.95 },
  { n: 10000, time_spimi: 1234, time_postgresql: 2567, precision_spimi: 0.89, precision_postgresql: 0.94 },
]

const DEMO_MULTIMEDIA_RETRIEVAL_DATA: BenchmarkData[] = [
  {
    n: 100,
    time_knn_sequential: 45,
    time_knn_indexed: 12,
    time_pgvector: 18,
    precision_knn_sequential: 0.88,
    precision_knn_indexed: 0.87,
    precision_pgvector: 0.89,
  },
  {
    n: 500,
    time_knn_sequential: 234,
    time_knn_indexed: 67,
    time_pgvector: 89,
    precision_knn_sequential: 0.87,
    precision_knn_indexed: 0.86,
    precision_pgvector: 0.88,
  },
  {
    n: 1000,
    time_knn_sequential: 567,
    time_knn_indexed: 145,
    time_pgvector: 187,
    precision_knn_sequential: 0.86,
    precision_knn_indexed: 0.85,
    precision_pgvector: 0.87,
  },
  {
    n: 5000,
    time_knn_sequential: 2890,
    time_knn_indexed: 678,
    time_pgvector: 834,
    precision_knn_sequential: 0.85,
    precision_knn_indexed: 0.84,
    precision_pgvector: 0.86,
  },
  {
    n: 10000,
    time_knn_sequential: 5678,
    time_knn_indexed: 1345,
    time_pgvector: 1678,
    precision_knn_sequential: 0.84,
    precision_knn_indexed: 0.83,
    precision_pgvector: 0.85,
  },
]

export function PerformanceBenchmark() {
  const [textData, setTextData] = useState<BenchmarkData[]>(DEMO_TEXT_RETRIEVAL_DATA)
  const [multimediaData, setMultimediaData] = useState<BenchmarkData[]>(DEMO_MULTIMEDIA_RETRIEVAL_DATA)
  const [loadingFile, setLoadingFile] = useState(false)

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>, type: "text" | "multimedia") => {
    const file = e.target.files?.[0]
    if (!file) return

    setLoadingFile(true)
    try {
      // Intentar cargar del backend
      const formData = new FormData()
      formData.append("file", file)
      formData.append("type", type)

      const response = await fetch("http://localhost:8000/upload_benchmark", {
        method: "POST",
        body: formData,
      }).catch(() => null)

      if (response && response.ok) {
        const data = await response.json()
        if (data.ok && data.data) {
          if (type === "text") {
            setTextData(data.data)
          } else {
            setMultimediaData(data.data)
          }
          toast.success("Benchmark data loaded successfully")
        } else {
          throw new Error(data.error || "Upload failed")
        }
      } else {
        toast.info("Using demo data. Backend not available.")
      }
    } catch (err) {
      console.error("Upload error:", err)
      toast.error("Failed to load data. Using demo data.")
    } finally {
      setLoadingFile(false)
    }
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="animate-fade-in">
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-foreground/70 bg-clip-text text-transparent">
          Performance & Benchmark
        </h1>
        <p className="text-muted-foreground mt-2">
          Comparación de rendimiento entre diferentes técnicas de búsqueda
        </p>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="text" className="space-y-6">
        <TabsList className="grid w-full max-w-md grid-cols-2 bg-white/5 border border-white/10">
          <TabsTrigger value="text">Text Retrieval</TabsTrigger>
          <TabsTrigger value="multimedia">Multimedia Retrieval</TabsTrigger>
        </TabsList>

        {/* Text Retrieval Tab */}
        <TabsContent value="text" className="space-y-6 animate-fade-in">
          {/* Upload Card */}
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5 text-primary" />
                Load Custom Data
              </CardTitle>
              <CardDescription>Upload JSON or CSV with benchmark data</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <label className="flex-1">
                  <input
                    type="file"
                    accept=".json,.csv"
                    onChange={(e) => handleFileUpload(e, "text")}
                    disabled={loadingFile}
                    className="hidden"
                  />
                  <Button
                    variant="outline"
                    className="w-full cursor-pointer"
                    disabled={loadingFile}
                  >
                    {loadingFile ? "Loading..." : "Upload Benchmark Data"}
                  </Button>
                </label>
              </div>
            </CardContent>
          </Card>

          {/* Time Comparison */}
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle>Execution Time Comparison</CardTitle>
              <CardDescription>Time (ms) vs Dataset Size (N)</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={textData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="n" stroke="rgba(255,255,255,0.5)" />
                  <YAxis stroke="rgba(255,255,255,0.5)" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(0,0,0,0.8)",
                      border: "1px solid rgba(255,255,255,0.2)",
                      borderRadius: "8px",
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="time_spimi"
                    stroke="#3b82f6"
                    name="SPIMI"
                    isAnimationActive={true}
                  />
                  <Line
                    type="monotone"
                    dataKey="time_postgresql"
                    stroke="#ec4899"
                    name="PostgreSQL"
                    isAnimationActive={true}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Precision Comparison */}
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle>Precision Comparison</CardTitle>
              <CardDescription>Accuracy vs Dataset Size (N)</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={textData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="n" stroke="rgba(255,255,255,0.5)" />
                  <YAxis stroke="rgba(255,255,255,0.5)" domain={[0, 1]} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(0,0,0,0.8)",
                      border: "1px solid rgba(255,255,255,0.2)",
                      borderRadius: "8px",
                    }}
                  />
                  <Legend />
                  <Bar
                    dataKey="precision_spimi"
                    fill="#3b82f6"
                    name="SPIMI Precision"
                    radius={[8, 8, 0, 0]}
                  />
                  <Bar
                    dataKey="precision_postgresql"
                    fill="#ec4899"
                    name="PostgreSQL Precision"
                    radius={[8, 8, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Statistics */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="glass-card border-white/10 bg-gradient-to-br from-blue-500/10 to-transparent">
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Fastest Method</p>
                    <p className="text-2xl font-bold text-blue-400">SPIMI</p>
                    <p className="text-xs text-muted-foreground mt-2">avg: ~900ms</p>
                  </div>
                  <TrendingUp className="h-8 w-8 text-blue-400/50" />
                </div>
              </CardContent>
            </Card>

            <Card className="glass-card border-white/10 bg-gradient-to-br from-primary/10 to-transparent">
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Best Precision</p>
                    <p className="text-2xl font-bold text-primary">PostgreSQL</p>
                    <p className="text-xs text-muted-foreground mt-2">avg: 0.946</p>
                  </div>
                  <BarChart3 className="h-8 w-8 text-primary/50" />
                </div>
              </CardContent>
            </Card>

            <Card className="glass-card border-white/10 bg-gradient-to-br from-secondary/10 to-transparent">
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Performance Ratio</p>
                    <p className="text-2xl font-bold text-secondary">2.1x</p>
                    <p className="text-xs text-muted-foreground mt-2">SPIMI vs PostgreSQL</p>
                  </div>
                  <TrendingUp className="h-8 w-8 text-secondary/50" />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Multimedia Retrieval Tab */}
        <TabsContent value="multimedia" className="space-y-6 animate-fade-in">
          {/* Upload Card */}
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5 text-primary" />
                Load Custom Data
              </CardTitle>
              <CardDescription>Upload JSON or CSV with benchmark data</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <label className="flex-1">
                  <input
                    type="file"
                    accept=".json,.csv"
                    onChange={(e) => handleFileUpload(e, "multimedia")}
                    disabled={loadingFile}
                    className="hidden"
                  />
                  <Button
                    variant="outline"
                    className="w-full cursor-pointer"
                    disabled={loadingFile}
                  >
                    {loadingFile ? "Loading..." : "Upload Benchmark Data"}
                  </Button>
                </label>
              </div>
            </CardContent>
          </Card>

          {/* Time Comparison */}
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle>Execution Time Comparison</CardTitle>
              <CardDescription>Time (ms) vs Dataset Size (N)</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={multimediaData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="n" stroke="rgba(255,255,255,0.5)" />
                  <YAxis stroke="rgba(255,255,255,0.5)" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(0,0,0,0.8)",
                      border: "1px solid rgba(255,255,255,0.2)",
                      borderRadius: "8px",
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="time_knn_sequential"
                    stroke="#ef4444"
                    name="KNN Sequential"
                    isAnimationActive={true}
                  />
                  <Line
                    type="monotone"
                    dataKey="time_knn_indexed"
                    stroke="#10b981"
                    name="KNN Indexed"
                    isAnimationActive={true}
                  />
                  <Line
                    type="monotone"
                    dataKey="time_pgvector"
                    stroke="#8b5cf6"
                    name="pgVector"
                    isAnimationActive={true}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Precision Comparison */}
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle>Precision Comparison</CardTitle>
              <CardDescription>Accuracy vs Dataset Size (N)</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={multimediaData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="n" stroke="rgba(255,255,255,0.5)" />
                  <YAxis stroke="rgba(255,255,255,0.5)" domain={[0, 1]} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(0,0,0,0.8)",
                      border: "1px solid rgba(255,255,255,0.2)",
                      borderRadius: "8px",
                    }}
                  />
                  <Legend />
                  <Bar
                    dataKey="precision_knn_sequential"
                    fill="#ef4444"
                    name="KNN Sequential"
                    radius={[8, 8, 0, 0]}
                  />
                  <Bar
                    dataKey="precision_knn_indexed"
                    fill="#10b981"
                    name="KNN Indexed"
                    radius={[8, 8, 0, 0]}
                  />
                  <Bar
                    dataKey="precision_pgvector"
                    fill="#8b5cf6"
                    name="pgVector"
                    radius={[8, 8, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Statistics */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="glass-card border-white/10 bg-gradient-to-br from-green-500/10 to-transparent">
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Fastest Method</p>
                    <p className="text-2xl font-bold text-green-400">KNN Indexed</p>
                    <p className="text-xs text-muted-foreground mt-2">avg: ~641ms</p>
                  </div>
                  <TrendingUp className="h-8 w-8 text-green-400/50" />
                </div>
              </CardContent>
            </Card>

            <Card className="glass-card border-white/10 bg-gradient-to-br from-primary/10 to-transparent">
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Best Precision</p>
                    <p className="text-2xl font-bold text-primary">pgVector</p>
                    <p className="text-xs text-muted-foreground mt-2">avg: 0.869</p>
                  </div>
                  <BarChart3 className="h-8 w-8 text-primary/50" />
                </div>
              </CardContent>
            </Card>

            <Card className="glass-card border-white/10 bg-gradient-to-br from-secondary/10 to-transparent">
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Performance Ratio</p>
                    <p className="text-2xl font-bold text-secondary">4.2x</p>
                    <p className="text-xs text-muted-foreground mt-2">Sequential vs Indexed</p>
                  </div>
                  <TrendingUp className="h-8 w-8 text-secondary/50" />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
