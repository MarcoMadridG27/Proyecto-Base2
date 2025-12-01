"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Search, Clock, Zap, BarChart3, Upload, FileText, Database, ChevronDown, ChevronUp } from "lucide-react"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

type SearchResult = {
  doc_id: number
  score: number
  rank: number
  text?: string
  [key: string]: any
}

type SearchMetrics = {
  execution_time: number
  total_results: number
}

export function TextSearch() {
  const [query, setQuery] = useState("")
  const [topK, setTopK] = useState(10)
  const [results, setResults] = useState<SearchResult[]>([])
  const [metrics, setMetrics] = useState<SearchMetrics | null>(null)
  const [loading, setLoading] = useState(false)
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())

  // Upload state
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadIndexName, setUploadIndexName] = useState("default")

  // Search state
  const [searchIndexName, setSearchIndexName] = useState("default")
  const [availableIndices, setAvailableIndices] = useState<string[]>([])

  // Fetch indices on mount
  const fetchIndices = async () => {
    try {
      const response = await fetch("http://localhost:8000/text/indices")
      const data = await response.json()
      if (data.ok) {
        setAvailableIndices(data.indices)
      }
    } catch (err) {
      console.error("Failed to fetch indices:", err)
    }
  }

  // Initial fetch
  useEffect(() => {
    fetchIndices()
  }, [])

  const handleSearch = async () => {
    if (!query.trim()) {
      toast.error("Please enter a search query")
      return
    }

    setLoading(true)
    setExpandedRows(new Set()) // Reset expansion
    try {
      const response = await fetch("http://localhost:8000/text/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query,
          top_k: topK,
          index_name: searchIndexName
        }),
      })

      const data = await response.json()

      if (data.ok) {
        setResults(data.results || [])
        setMetrics({
          execution_time: data.search_time_seconds * 1000, // Convert to ms
          total_results: data.results ? data.results.length : 0,
        })
        toast.success(`Found ${data.results ? data.results.length : 0} results`)
      } else {
        throw new Error(data.error || "Search failed")
      }
    } catch (err) {
      console.error("Search error:", err)
      toast.error(err instanceof Error ? err.message : "Search failed")
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async () => {
    if (!file) {
      toast.error("Please select a file first")
      return
    }

    setUploading(true)
    const formData = new FormData()
    formData.append("file", file)
    formData.append("index_name", uploadIndexName)

    try {
      const response = await fetch("http://localhost:8000/text/build_index", {
        method: "POST",
        body: formData,
      })

      const data = await response.json()

      if (data.ok) {
        toast.success(`Index built successfully! ${data.stats.num_documents} documents indexed.`)
        fetchIndices() // Refresh list
      } else {
        throw new Error(data.error || "Upload failed")
      }
    } catch (err) {
      console.error("Upload error:", err)
      toast.error(err instanceof Error ? err.message : "Upload failed")
    } finally {
      setUploading(false)
    }
  }

  const toggleRow = (rank: number) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(rank)) {
      newExpanded.delete(rank)
    } else {
      newExpanded.add(rank)
    }
    setExpandedRows(newExpanded)
  }

  // Drag and drop state
  const [isDragging, setIsDragging] = useState(false)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0]
      if (droppedFile.name.endsWith('.csv')) {
        setFile(droppedFile)
      } else {
        toast.error("Please upload a CSV file")
      }
    }
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="animate-fade-in">
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-foreground/70 bg-clip-text text-transparent">
          Text Search Engine
        </h1>
        <p className="text-muted-foreground mt-2">
          Inverted Index with SPIMI & Cosine Similarity
        </p>
      </div>

      <Tabs defaultValue="search" className="w-full">
        <TabsList className="grid w-full grid-cols-2 max-w-[400px] mb-8">
          <TabsTrigger value="search">Search</TabsTrigger>
          <TabsTrigger value="upload">Upload & Index</TabsTrigger>
        </TabsList>

        {/* SEARCH TAB */}
        <TabsContent value="search" className="space-y-8">
          <Card className="glass-card border-white/10 hover:shadow-xl hover:shadow-primary/10 transition-all duration-300 animate-scale-in">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="h-5 w-5 text-primary" />
                Query Parameters
              </CardTitle>
              <CardDescription>Enter your search query (natural language supported)</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <label className="text-sm font-medium">Search Query</label>
                <div className="flex gap-2">
                  <Input
                    placeholder="e.g., machine learning algorithms..."
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

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Top-K Results</label>
                  <Input
                    type="number"
                    min="1"
                    max="100"
                    value={topK}
                    onChange={(e) => setTopK(Math.max(1, parseInt(e.target.value) || 10))}
                    className="bg-white/5 border-white/10 text-foreground focus:border-primary focus:bg-white/10 transition-all"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Select Index</label>
                  <select
                    value={searchIndexName}
                    onChange={(e) => setSearchIndexName(e.target.value)}
                    className="flex h-10 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <option value="default" className="bg-background text-foreground">default</option>
                    {availableIndices.filter(i => i !== 'default').map((idx) => (
                      <option key={idx} value={idx} className="bg-background text-foreground">
                        {idx}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Results Section */}
          {results.length > 0 && (
            <div className="space-y-4 animate-fade-in">
              {/* Metrics Bar */}
              <div className="grid gap-4 md:grid-cols-2">
                <Card className="glass-card border-white/10 bg-gradient-to-br from-primary/10 to-transparent">
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-xs text-muted-foreground">Execution Time</p>
                        <p className="text-2xl font-bold text-primary">
                          {metrics?.execution_time?.toFixed(2) ?? '0.00'}ms
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
              </div>

              {/* Results Table */}
              <Card className="glass-card border-white/10">
                <CardHeader>
                  <CardTitle>Ranked Results</CardTitle>
                  <CardDescription>
                    Documents ranked by Cosine Similarity. Click row to view metadata.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-white/10 hover:bg-white/5">
                          <TableHead className="w-[50px]"></TableHead>
                          <TableHead className="w-[80px]">Rank</TableHead>
                          <TableHead className="w-[120px]">Document ID</TableHead>
                          <TableHead>Text Preview</TableHead>
                          <TableHead className="text-right w-[140px]">Similarity Score</TableHead>
                          <TableHead className="text-right w-[120px]">Match %</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {results.map((result, idx) => (
                          <>
                            <TableRow
                              key={idx}
                              className="border-white/10 hover:bg-white/5 transition-colors cursor-pointer"
                              onClick={() => toggleRow(result.rank)}
                            >
                              <TableCell>
                                {expandedRows.has(result.rank) ? (
                                  <ChevronUp className="h-4 w-4 text-muted-foreground" />
                                ) : (
                                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                )}
                              </TableCell>
                              <TableCell className="font-medium">#{result.rank}</TableCell>
                              <TableCell className="font-mono text-primary">Doc {result.doc_id}</TableCell>
                              <TableCell className="text-sm text-muted-foreground max-w-md truncate">
                                {result.text || "No text available"}
                              </TableCell>
                              <TableCell className="text-right font-mono">
                                {result.score.toFixed(4)}
                              </TableCell>
                              <TableCell className="text-right">
                                <div className="flex items-center justify-end gap-2">
                                  <div className="w-24 h-1.5 bg-white/10 rounded-full overflow-hidden">
                                    <div
                                      className="h-full bg-gradient-to-r from-primary to-secondary"
                                      style={{ width: `${result.score * 100}%` }}
                                    />
                                  </div>
                                  <span className="font-semibold text-foreground min-w-[3rem] text-right">
                                    {(result.score * 100).toFixed(1)}%
                                  </span>
                                </div>
                              </TableCell>
                            </TableRow>
                            {expandedRows.has(result.rank) && (
                              <TableRow className="bg-white/5 hover:bg-white/5">
                                <TableCell colSpan={6} className="p-4">
                                  <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                                    <h4 className="mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider">
                                      Document Metadata
                                    </h4>
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                      {Object.entries(result).map(([key, value]) => {
                                        if (['doc_id', 'score', 'rank', 'text'].includes(key)) return null;
                                        return (
                                          <div key={key} className="space-y-1">
                                            <p className="text-xs font-medium text-muted-foreground capitalize">
                                              {key.replace(/_/g, ' ')}
                                            </p>
                                            <p className="text-sm text-foreground break-words font-mono bg-white/5 p-2 rounded">
                                              {String(value)}
                                            </p>
                                          </div>
                                        )
                                      })}
                                    </div>
                                  </div>
                                </TableCell>
                              </TableRow>
                            )}
                          </>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        {/* UPLOAD TAB */}
        <TabsContent value="upload" className="space-y-8">
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5 text-primary" />
                Build Index
              </CardTitle>
              <CardDescription>Upload a CSV file containing documents to build the inverted index</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Index Name</label>
                  <Input
                    value={uploadIndexName}
                    onChange={(e) => setUploadIndexName(e.target.value)}
                    placeholder="default"
                    className="bg-white/5 border-white/10"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">CSV File</label>
                  <div className="flex items-center justify-center w-full">
                    <label
                      className={cn(
                        "flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer transition-all",
                        isDragging
                          ? "border-primary bg-primary/10"
                          : "border-white/10 bg-white/5 hover:bg-white/10"
                      )}
                      onDragOver={handleDragOver}
                      onDragLeave={handleDragLeave}
                      onDrop={handleDrop}
                    >
                      <div className="flex flex-col items-center justify-center pt-5 pb-6">
                        <Upload className={cn("w-8 h-8 mb-3", isDragging ? "text-primary" : "text-muted-foreground")} />
                        <p className="text-sm text-muted-foreground">
                          <span className="font-semibold">Click to upload</span> or drag and drop
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          CSV with 'id' and 'text' columns
                        </p>
                      </div>
                      <input
                        type="file"
                        className="hidden"
                        accept=".csv"
                        onChange={(e) => setFile(e.target.files?.[0] || null)}
                      />
                    </label>
                  </div>

                  {file && (
                    <p className="text-sm text-primary flex items-center gap-2 mt-2">
                      <FileText className="h-4 w-4" />
                      {file.name}
                    </p>
                  )}
                </div>
              </div>

              <Button
                onClick={handleUpload}
                disabled={uploading || !file}
                className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
              >
                {uploading ? "Building Index..." : "Upload & Build Index"}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

