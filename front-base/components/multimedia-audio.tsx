"use client"

import { useState, useEffect } from "react"
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

function MultimediaSearch({
  focus = "both", // "both" | "image" | "audio"
  initialTab = "search" // "search" | "build"
}: { focus?: "both" | "image" | "audio"; initialTab?: "search" | "build" } = {}) {
  // Search State
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string>("")
  const [results, setResults] = useState<SimilarObject[]>([])
  const [metrics, setMetrics] = useState<MultimediaMetrics | null>(null)
  const [loading, setLoading] = useState(false)
  const [fileType, setFileType] = useState<"image" | "audio" | null>(null)
  const [topK, setTopK] = useState(5)
  const [searchIndexName, setSearchIndexName] = useState("default")
  const [searchMethod, setSearchMethod] = useState<"sequential" | "index">("sequential") // New state for search method

  // Build Index State
  const [zipFile, setZipFile] = useState<File | null>(null)
  const [buildingIndex, setBuildingIndex] = useState(false)
  const [buildIndexName, setBuildIndexName] = useState("default")
  const [kClusters, setKClusters] = useState(100)
  // choose build type: mixed | image | audio
  const [buildIndexType, setBuildIndexType] = useState<"mixed" | "image" | "audio">(
    focus === "audio" ? "audio" : "mixed"
  )
  const [useServerCSV, setUseServerCSV] = useState(false)
  const [recordingSeconds, setRecordingSeconds] = useState(0)
  const [isRecording, setIsRecording] = useState(false)
  const [mediaRecorderRef, setMediaRecorderRef] = useState<MediaRecorder | null>(null)
  const [buildingServerIndex, setBuildingServerIndex] = useState(false)

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
    // If it's audio validate duration <= 30s; accept image preview otherwise
    if (isAudio) {
      const url = URL.createObjectURL(file)
      const audioEl = new Audio(url)
      audioEl.addEventListener("loadedmetadata", () => {
        if (audioEl.duration && audioEl.duration > 30) {
          toast.error("Audio must be <= 30 seconds")
          setUploadedFile(null)
          setPreviewUrl("")
          setFileType(null)
          URL.revokeObjectURL(url)
          return
        } else {
          setPreviewUrl(url)
        }
      })
      audioEl.addEventListener("error", () => {
        toast.error("Unable to read audio metadata")
        setUploadedFile(null)
        setPreviewUrl("")
        setFileType(null)
        URL.revokeObjectURL(url)
      })
    } else {
      const reader = new FileReader()
      reader.onload = (e) => setPreviewUrl(e.target?.result as string)
      reader.readAsDataURL(file)
    }
  }

  // Timer for recording
  useEffect(() => {
    if (!isRecording) return
    const interval = setInterval(() => {
      setRecordingSeconds((prev) => {
        if (prev >= 30) {
          if (mediaRecorderRef && mediaRecorderRef.state === "recording") {
            mediaRecorderRef.stop()
          }
          setIsRecording(false)
          return 0
        }
        return prev + 1
      })
    }, 1000)
    return () => clearInterval(interval)
  }, [isRecording, mediaRecorderRef])

  // Recording support (30s)
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream)
      const chunks: Blob[] = []
      mr.ondataavailable = (ev) => chunks.push(ev.data)
      mr.onstop = () => {
        const blob = new Blob(chunks, { type: "audio/webm" })
        const f = new File([blob], `recording_${Date.now()}.webm`, { type: "audio/webm" })
        setUploadedFile(f)
        setFileType("audio")
        const url = URL.createObjectURL(blob)
        setPreviewUrl(url)
        setIsRecording(false)
        setRecordingSeconds(0)
      }
      mr.start()
      setIsRecording(true)
      setRecordingSeconds(0)
      setMediaRecorderRef(mr)
    } catch {
      toast.error("Could not access microphone")
    }
  }
  const stopRecording = () => {
    if (mediaRecorderRef && mediaRecorderRef.state === "recording") mediaRecorderRef.stop()
    setRecordingSeconds(0)
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
      formData.append("method", searchMethod) // Add the selected search method

      const endpoint = "http://localhost:8000/multimedia/audio/search"
      const response = await fetch(endpoint, {
        method: "POST",
        body: formData,
      })

      const data = await response.json()

      if (data.ok) {
        setResults(data.results || [])
        setMetrics({
          execution_time: data.search_time_seconds * 1000, // Convert seconds to milliseconds
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
    if (!zipFile && !(buildIndexType === "audio" && useServerCSV)) {
      toast.error(buildIndexType === "audio" ? "Please select a CSV or use server CSV" : "Please select a ZIP file first")
      return
    }

    setBuildingIndex(true)
    const formData = new FormData()
    // for audio type we expect CSV
    if (zipFile) formData.append("file", zipFile)
    if (buildIndexType === "audio" && useServerCSV) formData.append("use_server_csv", "true")
    formData.append("k", kClusters.toString())
    formData.append("index_name", buildIndexName)

    try {
      // choose build endpoint according to selected type
      const buildEndpoint = buildIndexType === "audio"
        ? "http://localhost:8000/multimedia/audio/build_index"
        : "http://localhost:8000/multimedia/build_index"
      const response = await fetch(buildEndpoint, {
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

  const handleBuildServerAudioIndex = async () => {
    setBuildingServerIndex(true)
    try {
      const formData = new FormData()
      formData.append("index_name", searchIndexName)
      formData.append("k", "100")
      formData.append("use_tfidf", "true")
      formData.append("use_server_csv", "true")

      const response = await fetch("http://localhost:8000/multimedia/audio/build_index", {
        method: "POST",
        body: formData,
      })

      const data = await response.json()
      if (data.ok) {
        toast.success(`Audio index built! Indexed ${data.stats.indexed_files} tracks.`)
      } else {
        toast.error(data.error || "Failed to build index")
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Build failed")
    } finally {
      setBuildingServerIndex(false)
    }
  }

  // Helper to construct media URL (images or audio)
  const getMediaUrl = (filename: string) => {
    // Files are stored in data/mm_index_{indexName}/media/{filename}
    return `http://localhost:8000/data/mm_index_${searchIndexName}/media/${filename}`
  }

  // if component is focused only on audio, force search tab and hide build tab
  const effectiveInitialTab = focus === "audio" ? "search" : initialTab

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

      {/* Metrics */}
      {metrics && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="glass-card border-white/10 bg-gradient-to-br from-primary/10 to-transparent">
            <CardContent className="pt-6 flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Execution Time</p>
                <p className="text-2xl font-bold text-primary">
                  {metrics.execution_time.toFixed(2)} ms
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
                  {metrics.total_similar}
                </p>
              </div>
              <BarChart3 className="h-8 w-8 text-secondary/50" />
            </CardContent>
          </Card>
        </div>
      )}

      <Tabs defaultValue={effectiveInitialTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2 max-w-[400px] mb-8">
          <TabsTrigger value="search">Search</TabsTrigger>
          {/* hide build tab for audio-only pages */}
          {focus !== "audio" && <TabsTrigger value="build">Build Index</TabsTrigger>}
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
                    Query Audio (30s max)
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
                        // image or audio preview handled below
                        fileType === "audio" ? (
                          <div className="w-full h-full flex flex-col items-center justify-center p-4 bg-gradient-to-br from-purple-500/20 to-pink-500/20">
                            <Music className="h-14 w-14 text-purple-400 mb-2" />
                            {/* Elimina el reproductor de aquí */}
                          </div>
                        ) : (
                          <img src={previewUrl} alt="Preview" className="w-full h-full object-cover" />
                        )
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

                  <div className="space-y-2">
                    <label className="text-sm font-medium">Search Method</label>
                    <select
                      value={searchMethod}
                      onChange={(e) => setSearchMethod(e.target.value as "sequential" | "index")}
                      className="bg-white/5 border-white/10 rounded px-2 py-2 w-full"
                    >
                      <option value="sequential">KNN Sequential</option>
                      <option value="index">KNN with Inverted Index</option>
                    </select>
                  </div>

                  <Button
                    onClick={handleSearch}
                    disabled={loading || !uploadedFile}
                    className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
                  >
                    {loading ? "Searching..." : "Find Similar"}
                  </Button>
                  {/* Recording control only for audio mode / audio queries */}
                  <div className="mt-3 flex flex-col gap-2">
                    {isRecording && (
                      <div className="text-center">
                        <p className="text-sm font-semibold text-primary">
                          Recording: <span className="text-lg">{recordingSeconds}s / 30s</span>
                        </p>
                        <div className="w-full bg-white/10 rounded-full h-2 mt-2 overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-primary to-secondary transition-all duration-300"
                            style={{ width: `${(recordingSeconds / 30) * 100}%` }}
                          />
                        </div>
                      </div>
                    )}
                    <Button
                      onClick={() => (isRecording ? stopRecording() : startRecording())}
                      disabled={focus === "image"}
                      className={`flex-1 ${isRecording ? "bg-red-600 hover:bg-red-700" : "bg-primary"}`}
                    >
                      {isRecording ? `Stop Recording (${recordingSeconds}s)` : "Record 30s Audio"}
                    </Button>
                    <Button
                      onClick={() => {
                        setUploadedFile(null)
                        setPreviewUrl("")
                        setFileType(null)
                        setRecordingSeconds(0)
                      }}
                      variant="ghost"
                    >
                      Clear
                    </Button>
                  </div>

                  {/* Build index from server CSV button - only for audio mode */}
                  {focus === "audio" && (
                    <Button
                      onClick={handleBuildServerAudioIndex}
                      disabled={buildingServerIndex}
                      className="w-full bg-secondary/80 text-secondary-foreground hover:bg-secondary"
                    >
                      {buildingServerIndex ? "Building Index..." : "Build Index from Server CSV"}
                    </Button>
                  )}
                </CardContent>
              </Card>
              {/* Reproductor del archivo subido, abajo del upload */}
              {previewUrl && fileType === "audio" && (
                <div className="mt-6 p-4 rounded-lg bg-gradient-to-br from-purple-500/10 to-pink-500/10 shadow">
                  <h4 className="font-semibold text-primary mb-2">Reproductor de tu audio</h4>
                  <audio controls src={previewUrl} className="w-full" />
                </div>
              )}
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
                            {metrics?.execution_time !== undefined &&
                             metrics?.execution_time !== null &&
                             !isNaN(metrics.execution_time) &&
                             metrics.execution_time > 0
                              ? metrics.execution_time.toFixed(2) + "ms"
                              : results.length > 0
                                ? "Calculating..."
                                : "N/A"}
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

        {/* BUILD INDEX TAB - render only when not audio-only */}
        {focus !== "audio" && (
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

                {/* Index Type selector */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Index Type</label>
                  <select
                    value={buildIndexType}
                    onChange={(e) => setBuildIndexType(e.target.value as any)}
                    className="bg-white/5 border-white/10 rounded px-2 py-2 w-full"
                  >
                    <option value="mixed">Mixed (images + audio)</option>
                    <option value="image">Images only (ZIP)</option>
                    <option value="audio">Audio (CSV with MFCC_Vector)</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    {buildIndexType === "audio" ? "Audio CSV File (or use server CSV)" : "Images/Audios ZIP File"}
                  </label>
                  <div className="flex items-center justify-center w-full">
                    <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-white/10 border-dashed rounded-lg cursor-pointer bg-white/5 hover:bg-white/10 transition-all">
                      <div className="flex flex-col items-center justify-center pt-5 pb-6">
                        <FileArchive className="w-8 h-8 mb-3 text-muted-foreground" />
                        <p className="text-sm text-muted-foreground">
                          <span className="font-semibold">Click to upload {buildIndexType === "audio" ? "CSV" : "ZIP"}</span> or drag and drop
                        </p>
                      </div>
                      <input
                        type="file"
                        className="hidden"
                        accept={buildIndexType === "audio" ? ".csv" : ".zip"}
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
                  {buildIndexType === "audio" && (
                    <label className="flex items-center gap-2 mt-2 text-sm">
                      <input type="checkbox" checked={useServerCSV} onChange={(e) => setUseServerCSV(e.target.checked)} />
                      <span className="ml-2 text-muted-foreground">Use server CSV (audio_dataset.csv in index folder)</span>
                    </label>
                  )}
                </div>
                {/* end file block */}

                <Button
                  onClick={handleBuildIndex}
                  disabled={buildingIndex || !zipFile}
                  className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  {buildingIndex ? "Processing Images..." : "Build Index"}
                </Button>
                {/* Audio record helper for query usage (in Search tab) */}
                {/* Clear button */}
                <div className="mt-3 flex gap-2">
                  <Button
                    onClick={() => {
                      setUploadedFile(null)
                      setPreviewUrl("")
                      setFileType(null)
                    }}
                    variant="ghost"
                  >
                    Clear
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        )}
      </Tabs>
    </div>
  )
}

export default MultimediaSearch
export { MultimediaSearch }
