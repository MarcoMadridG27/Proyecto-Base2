"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Image as ImageIcon, Music, Clock, BarChart3, Upload, Database, FileArchive } from "lucide-react"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

type SimilarObject = {
  rank: number
  doc_id: number
  filename: string
  distance: number
  similarity: number
}

type MultimediaMetrics = {
  execution_time: number
  total_similar: number
}

export function MultimediaSearch() {
  // Search State
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string>("")
  const [results, setResults] = useState<SimilarObject[]>([])
  const [metrics, setMetrics] = useState<MultimediaMetrics | null>(null)
  const [loading, setLoading] = useState(false)
  const [fileType, setFileType] = useState<"image" | "audio" | null>(null)
  const [topK, setTopK] = useState(5)
  const [searchIndexName, setSearchIndexName] = useState("default")

  // Build Index State
  const [zipFile, setZipFile] = useState<File | null>(null)
  const [buildingIndex, setBuildingIndex] = useState(false)
  const [buildIndexName, setBuildIndexName] = useState("default")
  const [kClusters, setKClusters] = useState(100)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const isImage = file.type.startsWith("image/")
    const isAudio = file.type.startsWith("audio/")

    if (!isImage && !isAudio) {
      toast.error("Please upload an image or audio file")
      return
    }

    setUploadedFile(file)
    setFileType(isImage ? "image" : "audio")

    // Create preview
    const reader = new FileReader()
    reader.onload = (e) => {
      setPreviewUrl(e.target?.result as string)
    }
    reader.readAsDataURL(file)
  }

  const handleSearch = async () => {
    if (!uploadedFile) {
      toast.error("Please upload a file first")
      return
    }

    setLoading(true)
    try {
      const formData = new FormData()
      formData.append("file", uploadedFile)
      formData.append("top_k", topK.toString())
      formData.append("index_name", searchIndexName)

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
        toast.success(`Found ${data.results?.length || 0} similar objects`)
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

  const handleBuildIndex = async () => {
    if (!zipFile) {
      toast.error("Please select a ZIP file first")
      return
    }

    setBuildingIndex(true)
    const formData = new FormData()
    formData.append("file", zipFile)
    formData.append("k", kClusters.toString())
    formData.append("index_name", buildIndexName)

    try {
      const response = await fetch("http://localhost:8000/multimedia/build_index", {
        method: "POST",
        body: formData,
      })

      const data = await response.json()

      if (data.ok) {
        const fileCount = data.stats.indexed_files || data.stats.indexed_images || 0
        toast.success(`Index built successfully! ${fileCount} files indexed.`)
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

  // Helper to construct media URL (images or audio)
  const getMediaUrl = (filename: string) => {
    // Files are stored in data/mm_index_{indexName}/media/{filename}
    return `http://localhost:8000/data/mm_index_${searchIndexName}/media/${filename}`
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="animate-fade-in">
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-foreground/70 bg-clip-text text-transparent">
          Multimedia Search
        </h1>
        <p className="text-muted-foreground mt-2">
          Content-Based Retrieval using Bag of Visual/Acoustic Words (Images & Audio)
        </p>
      </div>

      <Tabs defaultValue="search" className="w-full">
        <TabsList className="grid w-full grid-cols-2 max-w-[400px] mb-8">
          <TabsTrigger value="search">Search</TabsTrigger>
          <TabsTrigger value="build">Build Index</TabsTrigger>
        </TabsList>

        {/* SEARCH TAB */}
        <TabsContent value="search" className="space-y-8">
          <div className="grid gap-8 md:grid-cols-[300px_1fr]">
            {/* Left Column: Upload & Config */}
            <div className="space-y-6">
              <Card className="glass-card border-white/10">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Upload className="h-5 w-5 text-primary" />
                    Query Media (Image or Audio)
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="relative group">
                    <input
                      type="file"
                      accept="image/*,audio/*"
                      onChange={handleFileSelect}
                      className="hidden"
                      id="media-input"
                    />
                    <label
                      htmlFor="media-input"
                      className={cn(
                        "flex flex-col items-center justify-center h-40 rounded-lg border-2 border-dashed transition-all cursor-pointer overflow-hidden relative",
                        uploadedFile
                          ? "border-primary"
                          : "border-white/20 hover:border-primary hover:bg-primary/5 bg-white/5"
                      )}
                    >
                      {previewUrl ? (
                        <img src={previewUrl} alt="Preview" className="w-full h-full object-cover" />
                      ) : (
                        <>
                          <Upload className="h-8 w-8 text-muted-foreground mb-2" />
                          <span className="text-xs text-muted-foreground">Click to upload</span>
                        </>
                      )}

                      {/* Hover overlay */}
                      <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <p className="text-white text-sm font-medium">Change Image</p>
                      </div>
                    </label>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium">Index Name</label>
                    <Input
                      value={searchIndexName}
                      onChange={(e) => setSearchIndexName(e.target.value)}
                      className="bg-white/5 border-white/10"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium">Top-K Results</label>
                    <Input
                      type="number"
                      value={topK}
                      onChange={(e) => setTopK(parseInt(e.target.value))}
                      min={1}
                      className="bg-white/5 border-white/10"
                    />
                  </div>

                  <Button
                    onClick={handleSearch}
                    disabled={loading || !uploadedFile}
                    className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
                  >
                    {loading ? "Searching..." : "Find Similar"}
                  </Button>
                </CardContent>
              </Card>
            </div>

            {/* Right Column: Results */}
            <div className="space-y-6">
              {results.length > 0 ? (
                <div className="space-y-6 animate-fade-in">
                  {/* Metrics */}
                  <div className="grid gap-4 md:grid-cols-2">
                    <Card className="glass-card border-white/10 bg-gradient-to-br from-primary/10 to-transparent">
                      <CardContent className="pt-6 flex items-center justify-between">
                        <div>
                          <p className="text-xs text-muted-foreground">Execution Time</p>
                          <p className="text-2xl font-bold text-primary">
                            {metrics?.execution_time.toFixed(2)}ms
                          </p>
                        </div>
                        <Clock className="h-8 w-8 text-primary/50" />
                      </CardContent>
                    </Card>
                    <Card className="glass-card border-white/10 bg-gradient-to-br from-secondary/10 to-transparent">
                      <CardContent className="pt-6 flex items-center justify-between">
                        <div>
                          <p className="text-xs text-muted-foreground">Total Found</p>
                          <p className="text-2xl font-bold text-secondary">
                            {metrics?.total_similar}
                          </p>
                        </div>
                        <BarChart3 className="h-8 w-8 text-secondary/50" />
                      </CardContent>
                    </Card>
                  </div>

                  {/* Results Grid */}
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {results.map((obj, idx) => {
                      const isAudio = obj.filename.match(/\.(wav|mp3|flac|ogg|m4a)$/i)
                      const isImage = obj.filename.match(/\.(png|jpg|jpeg|bmp|gif)$/i)

                      return (
                        <Card
                          key={idx}
                          className="glass-card border-white/10 overflow-hidden hover:shadow-xl hover:shadow-primary/10 transition-all duration-300 group animate-scale-in"
                          style={{ animationDelay: `${idx * 100}ms` }}
                        >
                          <div className="aspect-square relative overflow-hidden bg-black/20">
                            {isImage ? (
                              <img
                                src={getMediaUrl(obj.filename)}
                                alt={obj.filename}
                                className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                                onError={(e) => {
                                  (e.target as HTMLImageElement).src = "https://via.placeholder.com/300?text=Image+Not+Found"
                                }}
                              />
                            ) : isAudio ? (
                              <div className="w-full h-full flex flex-col items-center justify-center p-4 bg-gradient-to-br from-purple-500/20 to-pink-500/20">
                                <Music className="h-16 w-16 text-purple-400 mb-4" />
                                <audio
                                  controls
                                  className="w-full"
                                  src={getMediaUrl(obj.filename)}
                                >
                                  Your browser does not support audio.
                                </audio>
                              </div>
                            ) : (
                              <div className="w-full h-full flex items-center justify-center">
                                <FileArchive className="h-16 w-16 text-muted-foreground" />
                              </div>
                            )}
                            <div className="absolute top-2 right-2 bg-black/70 backdrop-blur-md text-white text-xs font-bold px-2 py-1 rounded-full border border-white/10">
                              # {obj.rank}
                            </div>
                          </div>
                          <CardContent className="p-4">
                            <h3 className="font-medium text-sm truncate mb-1" title={obj.filename}>
                              {obj.filename}
                            </h3>
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-muted-foreground">Similarity</span>
                              <span className="text-primary font-bold">
                                {(obj.similarity * 100).toFixed(1)}%
                              </span>
                            </div>
                            <div className="mt-2 h-1.5 bg-white/10 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-gradient-to-r from-primary to-secondary"
                                style={{ width: `${obj.similarity * 100}%` }}
                              />
                            </div>
                          </CardContent>
                        </Card>
                      )
                    })}
                  </div>
                </div>
              ) : (
                <div className="h-full flex items-center justify-center min-h-[300px] border-2 border-dashed border-white/10 rounded-lg bg-white/5">
                  <div className="text-center p-8">
                    <ImageIcon className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-muted-foreground">No results to show</h3>
                    <p className="text-sm text-muted-foreground/60 mt-1">
                      Upload an image and search to see similar items
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        {/* BUILD INDEX TAB */}
        <TabsContent value="build" className="space-y-8">
          <Card className="glass-card border-white/10 max-w-2xl mx-auto">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5 text-primary" />
                Build Multimedia Index
              </CardTitle>
              <CardDescription>
                Upload a ZIP file containing images and/or audio files to train the Codebook and build the index.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Index Name</label>
                  <Input
                    value={buildIndexName}
                    onChange={(e) => setBuildIndexName(e.target.value)}
                    placeholder="default"
                    className="bg-white/5 border-white/10"
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
                    className="bg-white/5 border-white/10"
                  />
                  <p className="text-xs text-muted-foreground">Number of visual words (clusters)</p>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Images ZIP File</label>
                <div className="flex items-center justify-center w-full">
                  <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-white/10 border-dashed rounded-lg cursor-pointer bg-white/5 hover:bg-white/10 transition-all">
                    <div className="flex flex-col items-center justify-center pt-5 pb-6">
                      <FileArchive className="w-8 h-8 mb-3 text-muted-foreground" />
                      <p className="text-sm text-muted-foreground">
                        <span className="font-semibold">Click to upload ZIP</span> or drag and drop
                      </p>
                    </div>
                    <input
                      type="file"
                      className="hidden"
                      accept=".zip"
                      onChange={(e) => setZipFile(e.target.files?.[0] || null)}
                    />
                  </label>
                </div>
                {zipFile && (
                  <p className="text-sm text-primary flex items-center gap-2 mt-2">
                    <FileArchive className="h-4 w-4" />
                    {zipFile.name}
                  </p>
                )}
              </div>

              <Button
                onClick={handleBuildIndex}
                disabled={buildingIndex || !zipFile}
                className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
              >
                {buildingIndex ? "Processing Images..." : "Build Index"}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
