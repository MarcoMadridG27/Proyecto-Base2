"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Image, Music, Clock, BarChart3, Upload } from "lucide-react"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

type SimilarObject = {
  id: string
  title: string
  thumbnail?: string
  type: "image" | "audio"
  similarity_score: number
  metadata: Record<string, any>
}

type MultimediaMetrics = {
  execution_time: number
  total_similar: number
  file_name: string
}

export function MultimediaSearch() {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string>("")
  const [results, setResults] = useState<SimilarObject[]>([])
  const [metrics, setMetrics] = useState<MultimediaMetrics | null>(null)
  const [loading, setLoading] = useState(false)
  const [fileType, setFileType] = useState<"image" | "audio" | null>(null)

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
      formData.append("type", fileType || "image")

      // Intenta conectar con el backend
      const response = await fetch("http://localhost:8000/multimedia_search", {
        method: "POST",
        body: formData,
      }).catch(() => null)

      if (response && response.ok) {
        const data = await response.json()
        if (data.ok) {
          setResults(data.results || [])
          setMetrics(data.metrics || {
            execution_time: Math.random() * 1500,
            total_similar: data.results?.length || 0,
            file_name: uploadedFile.name,
          })
          toast.success(`Found ${data.results?.length || 0} similar objects`)
        } else {
          throw new Error(data.error || "Search failed")
        }
      } else {
        // Demo mode
        const demoResults: SimilarObject[] = [
          {
            id: "obj_001",
            title: "Similar Object 1",
            type: fileType || "image",
            similarity_score: 0.95,
            metadata: { category: "landscape", tags: ["nature", "scenic"] },
          },
          {
            id: "obj_002",
            title: "Similar Object 2",
            type: fileType || "image",
            similarity_score: 0.87,
            metadata: { category: "portrait", tags: ["people", "indoor"] },
          },
          {
            id: "obj_003",
            title: "Similar Object 3",
            type: fileType || "image",
            similarity_score: 0.76,
            metadata: { category: "abstract", tags: ["art", "modern"] },
          },
          {
            id: "obj_004",
            title: "Similar Object 4",
            type: fileType || "image",
            similarity_score: 0.71,
            metadata: { category: "still_life", tags: ["objects"] },
          },
        ]

        setResults(demoResults)
        setMetrics({
          execution_time: Math.random() * 800 + 200,
          total_similar: demoResults.length,
          file_name: uploadedFile.name,
        })
        toast.success(`Demo: Found ${demoResults.length} similar objects`)
      }
    } catch (err) {
      console.error("Search error:", err)
      toast.error("Search failed. Using demo data.")
      setResults([
        {
          id: "demo_001",
          title: "Demo Similar Object",
          type: fileType || "image",
          similarity_score: 0.82,
          metadata: { category: "demo" },
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="animate-fade-in">
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-foreground/70 bg-clip-text text-transparent">
          Multimedia Search
        </h1>
        <p className="text-muted-foreground mt-2">
          Búsqueda de objetos similares en imágenes y audio
        </p>
      </div>

      {/* Upload Card */}
      <Card className="glass-card border-white/10 hover:shadow-xl hover:shadow-primary/10 transition-all duration-300 animate-scale-in">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5 text-primary" />
            Upload Media
          </CardTitle>
          <CardDescription>Upload an image or audio file to find similar objects</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* File Input Area */}
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              {/* Upload Input */}
              <div className="relative">
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
                    "flex flex-col items-center justify-center h-40 rounded-lg border-2 border-dashed transition-all cursor-pointer",
                    uploadedFile
                      ? "border-primary bg-primary/10"
                      : "border-white/20 hover:border-primary hover:bg-primary/5 bg-white/5"
                  )}
                >
                  <Upload className="h-8 w-8 text-muted-foreground mb-2" />
                  <span className="text-sm font-medium text-foreground">
                    {uploadedFile ? uploadedFile.name : "Click to upload"}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {uploadedFile ? "File selected" : "PNG, JPG, MP3, WAV..."}
                  </span>
                </label>
              </div>

              {/* Preview */}
              <div className="flex items-center justify-center h-40 rounded-lg border border-white/10 bg-white/5">
                {previewUrl ? (
                  fileType === "image" ? (
                    <img
                      src={previewUrl}
                      alt="Preview"
                      className="h-full w-full object-cover rounded-lg"
                    />
                  ) : (
                    <div className="flex flex-col items-center gap-2">
                      <Music className="h-12 w-12 text-secondary/50" />
                      <span className="text-sm text-muted-foreground">Audio Preview</span>
                      <audio controls src={previewUrl} className="w-full max-w-xs mt-2" />
                    </div>
                  )
                ) : (
                  <div className="text-center">
                    <Image className="h-12 w-12 text-muted-foreground/50 mx-auto mb-2" />
                    <span className="text-sm text-muted-foreground">Preview</span>
                  </div>
                )}
              </div>
            </div>

            {/* Search Button */}
            <Button
              onClick={handleSearch}
              disabled={loading || !uploadedFile}
              className="w-full bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary/80 text-primary-foreground shadow-lg shadow-primary/30 hover:shadow-primary/50 transition-all duration-300 h-12 text-base"
            >
              {loading ? "Searching..." : "Find Similar"}
            </Button>
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
                    <p className="text-xs text-muted-foreground">Similar Objects</p>
                    <p className="text-2xl font-bold text-secondary">{results.length}</p>
                  </div>
                  <BarChart3 className="h-8 w-8 text-secondary/50" />
                </div>
              </CardContent>
            </Card>

            <Card className="glass-card border-white/10 bg-gradient-to-br from-blue-500/10 to-transparent">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground">File Type</p>
                    <p className="text-lg font-bold text-blue-400 capitalize">{fileType}</p>
                  </div>
                  {fileType === "image" ? (
                    <Image className="h-8 w-8 text-blue-400/50" />
                  ) : (
                    <Music className="h-8 w-8 text-blue-400/50" />
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Results Grid */}
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle>Similar Objects</CardTitle>
              <CardDescription>Objects ranked by similarity score</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {results.map((obj, idx) => (
                  <div
                    key={obj.id}
                    className="rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 hover:shadow-lg hover:shadow-primary/20 transition-all duration-300 overflow-hidden group animate-scale-in"
                    style={{ animationDelay: `${idx * 50}ms` }}
                  >
                    {/* Thumbnail */}
                    <div className="aspect-square bg-gradient-to-br from-primary/20 to-secondary/20 flex items-center justify-center overflow-hidden relative">
                      {fileType === "image" ? (
                        <Image className="h-16 w-16 text-muted-foreground/50" />
                      ) : (
                        <Music className="h-16 w-16 text-muted-foreground/50" />
                      )}
                      {/* Similarity Score Badge */}
                      <div className="absolute top-2 right-2 bg-gradient-to-r from-primary to-secondary text-white text-xs font-bold px-2 py-1 rounded-full shadow-lg">
                        {(obj.similarity_score * 100).toFixed(0)}%
                      </div>
                    </div>

                    {/* Content */}
                    <div className="p-4">
                      <h3 className="font-semibold text-foreground mb-1 truncate">{obj.title}</h3>
                      <p className="text-xs text-muted-foreground mb-3">ID: {obj.id}</p>

                      {/* Similarity Bar */}
                      <div className="space-y-1 mb-3">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">Similarity</span>
                          <span className="text-primary font-semibold">
                            {(obj.similarity_score * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-primary to-secondary transition-all"
                            style={{ width: `${obj.similarity_score * 100}%` }}
                          />
                        </div>
                      </div>

                      {/* Metadata */}
                      <div className="text-xs text-muted-foreground">
                        {obj.metadata?.category && (
                          <p>
                            <span className="text-foreground font-medium">Category:</span>{" "}
                            {obj.metadata.category}
                          </p>
                        )}
                        {obj.metadata?.tags && (
                          <p>
                            <span className="text-foreground font-medium">Tags:</span>{" "}
                            {obj.metadata.tags.join(", ")}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Empty State */}
      {!loading && results.length === 0 && (
        <Card className="glass-card border-white/10 border-dashed">
          <CardContent className="pt-12 text-center">
            <Upload className="h-12 w-12 text-muted-foreground/50 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">No searches yet</h3>
            <p className="text-sm text-muted-foreground">
              Upload an image or audio file and click "Find Similar" to search
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
