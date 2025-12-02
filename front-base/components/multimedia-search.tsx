"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Image as ImageIcon, Clock, BarChart3, Upload, Database, FileArchive, Search } from "lucide-react"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

type SimilarObject = {
  rank: number
  doc_id: number
  filename: string
  distance: number
  similarity: number
  image_base64?: string
}

type MultimediaMetrics = {
  execution_time: number
  total_similar: number
}

function MultimediaSearch() {
  // Search State
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string>("")
  const [results, setResults] = useState<SimilarObject[]>([])
  const [metrics, setMetrics] = useState<MultimediaMetrics | null>(null)
  const [loading, setLoading] = useState(false)
  const [topK, setTopK] = useState(5)
  const [searchIndexName, setSearchIndexName] = useState("default")

  // Build Index State
  const [zipFile, setZipFile] = useState<File | null>(null)
  const [buildingIndex, setBuildingIndex] = useState(false)
  const [buildIndexName, setBuildIndexName] = useState("default")
  const [kClusters, setKClusters] = useState(100)

  // Direct Search State
  const [directDatasets, setDirectDatasets] = useState<string[]>([])
  const [selectedDirectDataset, setSelectedDirectDataset] = useState<string>("")
  const [directQueryFile, setDirectQueryFile] = useState<File | null>(null)
  const [directPreviewUrl, setDirectPreviewUrl] = useState<string>("")
  const [directResults, setDirectResults] = useState<SimilarObject[]>([])
  const [directMetrics, setDirectMetrics] = useState<MultimediaMetrics | null>(null)
  const [directLoading, setDirectLoading] = useState(false)
  const [directTopK, setDirectTopK] = useState(5)

  // Fetch datasets on mount
  useEffect(() => {
    fetch("http://localhost:8000/multimedia/list_datasets")
      .then(res => res.json())
      .then(data => {
        if (data.datasets) {
          setDirectDatasets(data.datasets)
          if (data.datasets.length > 0) setSelectedDirectDataset(data.datasets[0])
        }
      })
      .catch(err => console.error("Failed to load datasets", err))
  }, [])

  // --- HANDLE FILE UPLOAD (Only Images) ---
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith("image/")) {
      toast.error("Please upload an image file (PNG, JPG, etc)")
      return
    }

    setUploadedFile(file)

    // Create preview
    const reader = new FileReader()
    reader.onload = (e) => setPreviewUrl(e.target?.result as string)
    reader.readAsDataURL(file)
  }

  // --- HANDLE DIRECT FILE UPLOAD ---
  const handleDirectFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith("image/") && !file.type.startsWith("audio/")) {
      toast.error("Please upload an image or audio file")
      return
    }
    setDirectQueryFile(file)
    const reader = new FileReader()
    reader.onload = (e) => setDirectPreviewUrl(e.target?.result as string)
    reader.readAsDataURL(file)
  }

  // --- SEARCH FUNCTION ---
  const handleSearch = async () => {
    if (!uploadedFile) {
      toast.error("Please upload an image first")
      return
    }

    setLoading(true)
    setResults([])
    setMetrics(null)

    try {
      const formData = new FormData()
      formData.append("file", uploadedFile)
      formData.append("top_k", topK.toString())
      formData.append("index_name", searchIndexName)

      // Always hit the generic multimedia search (configured for images in backend)
      const response = await fetch("http://localhost:8000/multimedia/search", {
        method: "POST",
        body: formData,
      })

      const data = await response.json()

      if (data.ok) {
        setResults(data.results || [])
        setMetrics({
          execution_time: data.search_time_seconds * 1000,
          total_similar: data.results?.length || 0,
        })
        toast.success(`Found ${data.results?.length || 0} similar images`)
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

  // --- DIRECT SEARCH FUNCTION ---
  const handleDirectSearch = async () => {
    if (!directQueryFile) {
      toast.error("Please upload a query file first")
      return
    }
    if (!selectedDirectDataset) {
      toast.error("Please select a dataset")
      return
    }

    setDirectLoading(true)
    setDirectResults([])
    setDirectMetrics(null)

    try {
      const formData = new FormData()
      formData.append("file", directQueryFile)
      formData.append("dataset_name", selectedDirectDataset)
      formData.append("top_k", directTopK.toString())

      const response = await fetch("http://localhost:8000/multimedia/search_direct", {
        method: "POST",
        body: formData,
      })

      const data = await response.json()

      if (data.ok) {
        setDirectResults(data.results || [])
        setDirectMetrics({
          execution_time: data.search_time_seconds * 1000,
          total_similar: data.total_scanned || 0,
        })
        toast.success(`Scanned ${data.total_scanned} files in ${data.search_time_seconds.toFixed(2)}s`)
      } else {
        throw new Error(data.error || "Direct search failed")
      }
    } catch (err) {
      console.error("Direct search error:", err)
      toast.error(err instanceof Error ? err.message : "Direct search failed")
    } finally {
      setDirectLoading(false)
    }
  }

  // --- BUILD INDEX FUNCTION (Only ZIPs) ---
  const handleBuildIndex = async () => {
    if (!zipFile) {
      toast.error("Please select a ZIP file containing images")
      return
    }

    setBuildingIndex(true)
    const formData = new FormData()
    formData.append("file", zipFile)
    formData.append("k", kClusters.toString())
    formData.append("index_name", buildIndexName)
    // Always true for images usually
    formData.append("use_tfidf", "true")

    try {
      const response = await fetch("http://localhost:8000/multimedia/build_index", {
        method: "POST",
        body: formData,
      })

      const data = await response.json()

      if (data.ok) {
        const fileCount = data.stats.indexed_files || data.stats.num_files || 0
        toast.success(`Index built successfully! ${fileCount} images processed.`)
      } else {
        throw new Error(data.error || "Build index failed")
      }
    } catch (err) {
      console.error("Build index error:", err)
      toast.error(err instanceof Error ? err.message : "Build index failed")
    } finally {
      setBuildingIndex(false)
    }
  }

  // Helper to construct image URL
  const getMediaUrl = (filename: string) => {
    // Clean filename just in case backend sent garbage
    const cleanName = filename.replace(/\\/g, '/')
    return `http://localhost:8000/data/mm_index_${searchIndexName}/media/${cleanName}`
  }

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="animate-fade-in space-y-2">
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-primary via-purple-500 to-pink-500 bg-clip-text text-transparent">
          Visual Image Search
        </h1>
        <p className="text-muted-foreground">
          Content-Based Image Retrieval (CBIR) using Bag of Visual Words & SIFT Features.
        </p>
      </div>

      <Tabs defaultValue="search" className="w-full">
        <TabsList className="grid w-full grid-cols-3 max-w-[600px] mb-8">
          <TabsTrigger value="search">Search Images</TabsTrigger>
          <TabsTrigger value="direct">Direct Search</TabsTrigger>
          <TabsTrigger value="build">Build Index</TabsTrigger>
        </TabsList>

        {/* --- SEARCH TAB --- */}
        <TabsContent value="search" className="space-y-8">
          <div className="grid gap-8 md:grid-cols-[350px_1fr]">

            {/* Left Column: Upload & Config */}
            <div className="space-y-6">
              <Card className="glass-card border-white/10 shadow-lg">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Search className="h-5 w-5 text-primary" />
                    Query Image
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-5">
                  {/* Upload Box */}
                  <div className="relative group">
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleFileSelect}
                      className="hidden"
                      id="image-input"
                    />
                    <label
                      htmlFor="image-input"
                      className={cn(
                        "flex flex-col items-center justify-center h-64 rounded-xl border-2 border-dashed transition-all cursor-pointer overflow-hidden relative",
                        uploadedFile
                          ? "border-primary bg-black/40"
                          : "border-white/20 hover:border-primary hover:bg-primary/5 bg-white/5"
                      )}
                    >
                      {previewUrl ? (
                        <img
                          src={previewUrl}
                          alt="Preview"
                          className="w-full h-full object-contain p-2"
                        />
                      ) : (
                        <div className="flex flex-col items-center gap-2 text-muted-foreground group-hover:text-primary transition-colors">
                          <Upload className="h-10 w-10 mb-2" />
                          <span className="text-sm font-medium">Click to upload image</span>
                          <span className="text-xs opacity-70">JPG, PNG, BMP</span>
                        </div>
                      )}

                      {/* Hover overlay if file exists */}
                      {uploadedFile && (
                        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                          <p className="text-white text-sm font-medium flex items-center gap-2">
                            <Upload className="h-4 w-4" /> Change Image
                          </p>
                        </div>
                      )}
                    </label>
                  </div>

                  {/* Settings */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Index Name</label>
                      <Input
                        value={searchIndexName}
                        onChange={(e) => setSearchIndexName(e.target.value)}
                        className="bg-white/5 border-white/10"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Top K</label>
                      <Input
                        type="number"
                        value={topK}
                        onChange={(e) => setTopK(parseInt(e.target.value))}
                        min={1}
                        className="bg-white/5 border-white/10"
                      />
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="space-y-3 pt-2">
                    <Button
                      onClick={handleSearch}
                      disabled={loading || !uploadedFile}
                      className="w-full h-12 text-base font-semibold shadow-lg shadow-primary/20"
                      size="lg"
                    >
                      {loading ? (
                        <span className="flex items-center gap-2">
                          <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                          Searching...
                        </span>
                      ) : "Find Similar Images"}
                    </Button>

                    <Button
                      onClick={() => {
                        setUploadedFile(null)
                        setPreviewUrl("")
                        setResults([])
                        setMetrics(null)
                      }}
                      variant="ghost"
                      className="w-full text-muted-foreground hover:text-white"
                    >
                      Clear All
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Right Column: Results */}
            <div className="space-y-6">
              {results.length > 0 ? (
                <div className="space-y-6 animate-fade-in">

                  {/* Metrics Cards */}
                  <div className="grid gap-4 md:grid-cols-2">
                    <Card className="glass-card border-white/10 bg-primary/5">
                      <CardContent className="pt-6 flex items-center justify-between">
                        <div>
                          <p className="text-xs text-muted-foreground font-medium uppercase">Processing Time</p>
                          <p className="text-3xl font-bold text-primary tracking-tight">
                            {metrics?.execution_time ? metrics.execution_time.toFixed(0) : 0}
                            <span className="text-sm font-normal text-muted-foreground ml-1">ms</span>
                          </p>
                        </div>
                        <Clock className="h-10 w-10 text-primary/20" />
                      </CardContent>
                    </Card>
                    <Card className="glass-card border-white/10 bg-blue-500/5">
                      <CardContent className="pt-6 flex items-center justify-between">
                        <div>
                          <p className="text-xs text-muted-foreground font-medium uppercase">Matches Found</p>
                          <p className="text-3xl font-bold text-blue-400 tracking-tight">
                            {metrics?.total_similar}
                          </p>
                        </div>
                        <BarChart3 className="h-10 w-10 text-blue-500/20" />
                      </CardContent>
                    </Card>
                  </div>

                  {/* Results Grid - FORCE IMAGE RENDERING */}
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <ImageIcon className="h-5 w-5 text-primary" />
                    Search Results
                  </h3>

                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {results.map((obj, idx) => (
                      <Card
                        key={idx}
                        className="glass-card border-white/10 overflow-hidden hover:ring-2 hover:ring-primary/50 transition-all duration-300 group animate-scale-in"
                        style={{ animationDelay: `${idx * 50}ms` }}
                      >
                        <div className="aspect-square relative overflow-hidden bg-black/40">
                          {/* THE FIX: Always render img, ignore extension */}
                          <img
                            src={getMediaUrl(obj.filename)}
                            alt={obj.filename}
                            loading="lazy"
                            className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                            onError={(e) => {
                              (e.target as HTMLImageElement).src = "https://via.placeholder.com/300?text=Error+Loading"
                            }}
                          />

                          {/* Rank Badge */}
                          <div className="absolute top-2 left-2 bg-black/60 backdrop-blur-md text-white text-xs font-bold px-2 py-1 rounded-md border border-white/10">
                            #{obj.rank}
                          </div>

                          {/* Similarity Badge */}
                          <div className="absolute bottom-2 right-2 bg-primary/90 text-white text-xs font-bold px-2 py-1 rounded-full shadow-lg">
                            {(obj.similarity * 100).toFixed(0)}% Match
                          </div>
                        </div>

                        <div className="p-3">
                          <p className="text-xs text-muted-foreground truncate font-mono" title={obj.filename}>
                            {obj.filename}
                          </p>
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>
              ) : (
                // Empty State
                <div className="h-full min-h-[400px] flex flex-col items-center justify-center border-2 border-dashed border-white/10 rounded-xl bg-white/5 text-center p-8">
                  <div className="bg-white/5 p-4 rounded-full mb-4">
                    <ImageIcon className="h-12 w-12 text-muted-foreground/40" />
                  </div>
                  <h3 className="text-xl font-medium text-white">No results yet</h3>
                  <p className="text-muted-foreground mt-2 max-w-sm">
                    Upload an image from the panel on the left to start finding visually similar items in your dataset.
                  </p>
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        {/* --- DIRECT SEARCH TAB --- */}
        <TabsContent value="direct" className="space-y-8">
          <div className="grid gap-8 md:grid-cols-[350px_1fr]">
            {/* Left Column: Config */}
            <div className="space-y-6">
              <Card className="glass-card border-white/10 shadow-lg">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Database className="h-5 w-5 text-green-400" />
                    Direct Sequential
                  </CardTitle>
                  <CardDescription>
                    Scan a raw dataset ZIP without indexing.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">

                  {/* Dataset Selector */}
                  <div className="space-y-2">
                    <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Select Dataset (ZIP)</label>
                    <select
                      className="flex h-10 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      value={selectedDirectDataset}
                      onChange={(e) => setSelectedDirectDataset(e.target.value)}
                    >
                      {directDatasets.map(ds => (
                        <option key={ds} value={ds} className="bg-black text-white">{ds}</option>
                      ))}
                      {directDatasets.length === 0 && <option value="" className="bg-black text-white">No datasets found</option>}
                    </select>
                  </div>

                  {/* Upload Box */}
                  <div className="relative group">
                    <input
                      type="file"
                      accept="image/*,audio/*"
                      onChange={handleDirectFileSelect}
                      className="hidden"
                      id="direct-input"
                    />
                    <label
                      htmlFor="direct-input"
                      className={cn(
                        "flex flex-col items-center justify-center h-48 rounded-xl border-2 border-dashed transition-all cursor-pointer overflow-hidden relative",
                        directQueryFile
                          ? "border-green-500 bg-black/40"
                          : "border-white/20 hover:border-green-500 hover:bg-green-500/5 bg-white/5"
                      )}
                    >
                      {directPreviewUrl ? (
                        <img
                          src={directPreviewUrl}
                          alt="Preview"
                          className="w-full h-full object-contain p-2"
                        />
                      ) : (
                        <div className="flex flex-col items-center gap-2 text-muted-foreground group-hover:text-green-400 transition-colors">
                          <Upload className="h-8 w-8 mb-2" />
                          <span className="text-sm font-medium">Upload Query</span>
                        </div>
                      )}
                    </label>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Top K</label>
                    <Input
                      type="number"
                      value={directTopK}
                      onChange={(e) => setDirectTopK(parseInt(e.target.value))}
                      min={1}
                      className="bg-white/5 border-white/10"
                    />
                  </div>

                  <Button
                    onClick={handleDirectSearch}
                    disabled={directLoading || !directQueryFile || !selectedDirectDataset}
                    className="w-full h-12 text-base font-semibold shadow-lg shadow-green-500/20 bg-green-600 hover:bg-green-700 text-white"
                    size="lg"
                  >
                    {directLoading ? (
                      <span className="flex items-center gap-2">
                        <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                        Scanning...
                      </span>
                    ) : "Run Sequential Scan"}
                  </Button>

                </CardContent>
              </Card>
            </div>

            {/* Right Column: Results */}
            <div className="space-y-6">
              {directResults.length > 0 ? (
                <div className="space-y-6 animate-fade-in">

                  {/* Metrics */}
                  <div className="grid gap-4 md:grid-cols-2">
                    <Card className="glass-card border-white/10 bg-green-500/5">
                      <CardContent className="pt-6 flex items-center justify-between">
                        <div>
                          <p className="text-xs text-muted-foreground font-medium uppercase">Total Time</p>
                          <p className="text-3xl font-bold text-green-400 tracking-tight">
                            {directMetrics?.execution_time ? directMetrics.execution_time.toFixed(0) : 0}
                            <span className="text-sm font-normal text-muted-foreground ml-1">ms</span>
                          </p>
                        </div>
                        <Clock className="h-10 w-10 text-green-500/20" />
                      </CardContent>
                    </Card>
                    <Card className="glass-card border-white/10 bg-blue-500/5">
                      <CardContent className="pt-6 flex items-center justify-between">
                        <div>
                          <p className="text-xs text-muted-foreground font-medium uppercase">Files Scanned</p>
                          <p className="text-3xl font-bold text-blue-400 tracking-tight">
                            {directMetrics?.total_similar}
                          </p>
                        </div>
                        <Database className="h-10 w-10 text-blue-500/20" />
                      </CardContent>
                    </Card>
                  </div>

                  {/* Results List */}
                  <div className="grid gap-4">
                    {directResults.map((obj, idx) => (
                      <Card key={idx} className="glass-card border-white/10 p-4 flex items-center gap-4 hover:bg-white/5 transition-colors">
                        <div className="h-16 w-16 rounded-md bg-white/10 flex-shrink-0 overflow-hidden relative">
                          {obj.image_base64 ? (
                            <img
                              src={`data:image/jpeg;base64,${obj.image_base64}`}
                              alt={obj.filename}
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <div className="flex items-center justify-center w-full h-full font-bold text-lg">
                              #{obj.rank}
                            </div>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate text-white">{obj.filename}</p>
                          <p className="text-sm text-muted-foreground">Distance: {obj.distance.toFixed(4)}</p>
                        </div>
                        <div className="text-right">
                          <div className="text-lg font-bold text-green-400">{(obj.similarity * 100).toFixed(1)}%</div>
                          <div className="text-xs text-muted-foreground">Match</div>
                        </div>
                      </Card>
                    ))}
                  </div>

                </div>
              ) : (
                <div className="h-full min-h-[400px] flex flex-col items-center justify-center border-2 border-dashed border-white/10 rounded-xl bg-white/5 text-center p-8">
                  <div className="bg-white/5 p-4 rounded-full mb-4">
                    <Database className="h-12 w-12 text-muted-foreground/40" />
                  </div>
                  <h3 className="text-xl font-medium text-white">Ready to Scan</h3>
                  <p className="text-muted-foreground mt-2 max-w-sm">
                    Select a dataset and upload a query image to start a direct sequential scan.
                  </p>
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        {/* --- BUILD TAB --- */}
        <TabsContent value="build" className="space-y-8 animate-fade-in">
          <Card className="glass-card border-white/10 max-w-2xl mx-auto shadow-2xl">
            <CardHeader className="text-center pb-8 pt-8">
              <div className="mx-auto bg-primary/10 w-16 h-16 rounded-full flex items-center justify-center mb-4">
                <Database className="h-8 w-8 text-primary" />
              </div>
              <CardTitle className="text-2xl">Build Image Index</CardTitle>
              <CardDescription className="text-base">
                Create a new visual dictionary. Upload a ZIP file containing your dataset images.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-8 px-8 pb-8">

              <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Index Name</label>
                  <Input
                    value={buildIndexName}
                    onChange={(e) => setBuildIndexName(e.target.value)}
                    placeholder="my_dataset"
                    className="bg-white/5 border-white/10 h-11"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Vocabulary Size (K)</label>
                  <Input
                    type="number"
                    value={kClusters}
                    onChange={(e) => setKClusters(parseInt(e.target.value))}
                    min={10}
                    max={1000}
                    className="bg-white/5 border-white/10 h-11"
                  />
                  <p className="text-[10px] text-muted-foreground text-right">Clusters (Visual Words)</p>
                </div>
              </div>

              <div className="space-y-3">
                <label className="text-sm font-medium">Dataset (ZIP File)</label>
                <div className="flex items-center justify-center w-full">
                  <label className={cn(
                    "flex flex-col items-center justify-center w-full h-40 border-2 border-dashed rounded-xl cursor-pointer transition-all",
                    zipFile ? "border-primary bg-primary/5" : "border-white/10 bg-white/5 hover:bg-white/10"
                  )}>
                    <div className="flex flex-col items-center justify-center pt-5 pb-6">
                      <FileArchive className={cn("w-10 h-10 mb-3", zipFile ? "text-primary" : "text-muted-foreground")} />
                      {zipFile ? (
                        <div className="text-center">
                          <p className="text-sm font-semibold text-primary">{zipFile.name}</p>
                          <p className="text-xs text-muted-foreground">{(zipFile.size / (1024 * 1024)).toFixed(2)} MB</p>
                        </div>
                      ) : (
                        <>
                          <p className="text-sm text-muted-foreground font-medium">Click to upload ZIP</p>
                          <p className="text-xs text-muted-foreground/60 mt-1">Contains .jpg, .png files</p>
                        </>
                      )}
                    </div>
                    <input
                      type="file"
                      className="hidden"
                      accept=".zip"
                      onChange={(e) => setZipFile(e.target.files?.[0] || null)}
                    />
                  </label>
                </div>
              </div>

              <Button
                onClick={handleBuildIndex}
                disabled={buildingIndex || !zipFile}
                className="w-full h-12 text-base shadow-lg"
              >
                {buildingIndex ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                    Processing Dataset...
                  </span>
                ) : "Start Indexing"}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default MultimediaSearch;