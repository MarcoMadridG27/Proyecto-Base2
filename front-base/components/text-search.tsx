"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Search, Clock, Zap, BarChart3 } from "lucide-react"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

type SearchResult = {
  title: string
  snippet: string
  score: number
  tfidf_score?: number
  cosine_similarity?: number
}

type SearchMetrics = {
  execution_time: number
  total_results: number
  method: "tfidf" | "cosine" | "both"
}

export function TextSearch() {
  const [query, setQuery] = useState("")
  const [topK, setTopK] = useState(10)
  const [results, setResults] = useState<SearchResult[]>([])
  const [metrics, setMetrics] = useState<SearchMetrics | null>(null)
  const [loading, setLoading] = useState(false)
  const [activeMethod, setActiveMethod] = useState<"tfidf" | "cosine" | "both">("both")

  const handleSearch = async () => {
    if (!query.trim()) {
      toast.error("Please enter a search query")
      return
    }

    setLoading(true)
    try {
      // Simulamos una búsqueda. En producción, esto debería conectar con el backend
      const response = await fetch("http://localhost:8000/text_search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query,
          top_k: topK,
          method: activeMethod,
        }),
      }).catch(() => null)

      if (response && response.ok) {
        const data = await response.json()
        if (data.ok) {
          setResults(data.results || [])
          setMetrics(data.metrics || {
            execution_time: Math.random() * 2000,
            total_results: Math.floor(Math.random() * 100),
            method: activeMethod,
          })
          toast.success(`Found ${data.results?.length || 0} results`)
        } else {
          throw new Error(data.error || "Search failed")
        }
      } else {
        // Demo mode: genera resultados de prueba
        const demoResults: SearchResult[] = [
          {
            title: "Document 1: Introduction to Databases",
            snippet:
              "This document covers the fundamentals of database design and management systems...",
            score: 0.95,
            tfidf_score: 0.92,
            cosine_similarity: 0.98,
          },
          {
            title: "Document 2: Query Optimization",
            snippet:
              "Query optimization is crucial for database performance. This article explores various techniques...",
            score: 0.87,
            tfidf_score: 0.85,
            cosine_similarity: 0.89,
          },
          {
            title: "Document 3: Indexing Strategies",
            snippet: "Effective indexing can significantly improve query execution time. Learn about different index types...",
            score: 0.76,
            tfidf_score: 0.74,
            cosine_similarity: 0.78,
          },
        ]

        setResults(demoResults.slice(0, topK))
        setMetrics({
          execution_time: Math.random() * 500 + 50,
          total_results: demoResults.length,
          method: activeMethod,
        })
        toast.success(`Demo: Found ${demoResults.slice(0, topK).length} results`)
      }
    } catch (err) {
      console.error("Search error:", err)
      toast.error("Search failed. Using demo data.")
      // Fallback a datos de demo
      const demoResults = [
        {
          title: "Sample Document",
          snippet: "Sample search result",
          score: 0.85,
        },
      ]
      setResults(demoResults)
      setMetrics({
        execution_time: 150,
        total_results: 1,
        method: activeMethod,
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="animate-fade-in">
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-foreground/70 bg-clip-text text-transparent">
          Text Search
        </h1>
        <p className="text-muted-foreground mt-2">
          Búsqueda textual usando TF-IDF y Similitud de Coseno
        </p>
      </div>

      {/* Search Card */}
      <Card className="glass-card border-white/10 hover:shadow-xl hover:shadow-primary/10 transition-all duration-300 animate-scale-in">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5 text-primary" />
            Query Parameters
          </CardTitle>
          <CardDescription>Enter your search query and configure parameters</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Search Input */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Search Query</label>
            <div className="flex gap-2">
              <Input
                placeholder="Enter your search query (SQL or natural language)..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                className="flex-1 bg-white/5 border-white/10 text-foreground placeholder:text-muted-foreground focus:border-primary focus:bg-white/10 transition-all"
              />
              <Button
                onClick={handleSearch}
                disabled={loading}
                className="bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary/80 text-primary-foreground shadow-lg shadow-primary/30 hover:shadow-primary/50 transition-all duration-300"
              >
                {loading ? "Searching..." : "Search"}
              </Button>
            </div>
          </div>

          {/* Top-K Selector */}
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <label className="text-sm font-medium">Top-K Results</label>
              <Input
                type="number"
                min="1"
                max="1000"
                value={topK}
                onChange={(e) => setTopK(Math.max(1, parseInt(e.target.value) || 10))}
                className="bg-white/5 border-white/10 text-foreground focus:border-primary focus:bg-white/10 transition-all"
              />
            </div>

            {/* Method Selector */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Search Method</label>
              <select
                value={activeMethod}
                onChange={(e) => setActiveMethod(e.target.value as "tfidf" | "cosine" | "both")}
                className="w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:bg-white/10 transition-all"
              >
                <option value="both">Both (TF-IDF & Cosine)</option>
                <option value="tfidf">TF-IDF Only</option>
                <option value="cosine">Cosine Similarity Only</option>
              </select>
            </div>

            {/* Statistics */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Results</label>
              <div className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm">
                <p className="text-foreground font-semibold">{results.length} results</p>
                <p className="text-xs text-muted-foreground">
                  {metrics ? `${metrics.execution_time.toFixed(2)}ms` : "—"}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results Section */}
      {results.length > 0 && (
        <div className="space-y-4 animate-fade-in">
          {/* Metrics Bar */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="glass-card border-white/10 bg-gradient-to-br from-primary/10 to-transparent">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground">Execution Time</p>
                    <p className="text-2xl font-bold text-primary">
                      {metrics?.execution_time.toFixed(2)}ms
                    </p>
                  </div>
                  <Clock className="h-8 w-8 text-primary/50" />
                </div>
              </CardContent>
            </Card>

            <Card className="glass-card border-white/10 bg-gradient-to-br from-secondary/10 to-transparent">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground">Total Results</p>
                    <p className="text-2xl font-bold text-secondary">
                      {metrics?.total_results || 0}
                    </p>
                  </div>
                  <BarChart3 className="h-8 w-8 text-secondary/50" />
                </div>
              </CardContent>
            </Card>

            <Card className="glass-card border-white/10 bg-gradient-to-br from-blue-500/10 to-transparent">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground">Method</p>
                    <p className="text-lg font-bold text-blue-400 capitalize">
                      {activeMethod === "both" ? "Hybrid" : activeMethod}
                    </p>
                  </div>
                  <Zap className="h-8 w-8 text-blue-400/50" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Results Table */}
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle>Search Results</CardTitle>
              <CardDescription>
                {activeMethod === "both"
                  ? "Results ranked by combined TF-IDF and Cosine Similarity scores"
                  : activeMethod === "tfidf"
                    ? "Results ranked by TF-IDF score"
                    : "Results ranked by Cosine Similarity"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-white/10 hover:bg-white/5">
                      <TableHead>Title</TableHead>
                      <TableHead className="max-w-md">Snippet</TableHead>
                      {activeMethod !== "tfidf" && <TableHead className="text-right">Cosine Sim</TableHead>}
                      {activeMethod !== "cosine" && <TableHead className="text-right">TF-IDF</TableHead>}
                      <TableHead className="text-right">Score</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {results.map((result, idx) => (
                      <TableRow
                        key={idx}
                        className="border-white/10 hover:bg-white/5 transition-colors"
                      >
                        <TableCell className="font-medium text-primary">{result.title}</TableCell>
                        <TableCell className="max-w-md text-sm text-muted-foreground truncate">
                          {result.snippet}
                        </TableCell>
                        {activeMethod !== "tfidf" && (
                          <TableCell className="text-right">
                            <span className="text-blue-400 font-semibold">
                              {(result.cosine_similarity || 0).toFixed(3)}
                            </span>
                          </TableCell>
                        )}
                        {activeMethod !== "cosine" && (
                          <TableCell className="text-right">
                            <span className="text-secondary font-semibold">
                              {(result.tfidf_score || 0).toFixed(3)}
                            </span>
                          </TableCell>
                        )}
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-gradient-to-r from-primary to-secondary"
                                style={{ width: `${result.score * 100}%` }}
                              />
                            </div>
                            <span className="font-semibold text-foreground min-w-[3rem] text-right">
                              {(result.score * 100).toFixed(0)}%
                            </span>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Empty State */}
      {!loading && results.length === 0 && (
        <Card className="glass-card border-white/10 border-dashed">
          <CardContent className="pt-12 text-center">
            <Search className="h-12 w-12 text-muted-foreground/50 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">No searches yet</h3>
            <p className="text-sm text-muted-foreground">
              Enter a query and click Search to see results
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
