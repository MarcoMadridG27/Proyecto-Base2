"use client"

import { cn } from "@/lib/utils"
import type React from "react"
import { useState, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Upload, FileText, X, CheckCircle2 } from "lucide-react"
import { toast } from "sonner"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

export function FileUpload() {
  const [isDragging, setIsDragging] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<any[] | null>(null)
  const [headers, setHeaders] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files)
    const csvFile = files.find((file) => file.name.endsWith(".csv"))

    if (csvFile) {
      setUploadedFile(csvFile)
      toast.success("File ready to upload!", {
        description: `${csvFile.name}`,
      })
    } else {
      toast.error("Invalid file type", { description: "Please upload a CSV file." })
    }
  }, [])

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && file.name.endsWith(".csv")) {
      setUploadedFile(file)
      toast.success("File ready to upload!", { description: file.name })
    } else {
      toast.error("Invalid file type", { description: "Please upload a CSV file." })
    }
  }

  const handleRemoveFile = () => {
    setUploadedFile(null)
    setPreview(null)
    setHeaders([])
    toast.info("File removed")
  }

  const handleUploadToBackend = async () => {
    if (!uploadedFile) return

    const formData = new FormData()
    formData.append("file", uploadedFile)
    formData.append("table_name", uploadedFile.name.replace(".csv", ""))

    setLoading(true)

    try {
      const res = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData,
      })

      const data = await res.json()
      setLoading(false)

      if (data.ok) {
        setPreview(data.rows)
        setHeaders(data.headers)
        toast.success("File imported successfully!", {
          description: `${data.recordCount} records from ${data.fileName}`,
        })
      } else {
        toast.error("Error importing file", { description: data.error })
      }
    } catch (err: any) {
      setLoading(false)
      toast.error("Connection error", { description: err.message })
    }
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="animate-fade-in">
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-foreground/70 bg-clip-text text-transparent">
          File Upload
        </h1>
        <p className="text-muted-foreground mt-2">Upload CSV files to import data into the database</p>
      </div>

      {/* Upload Area */}
      <Card className="glass-card border-white/10 animate-scale-in hover:shadow-xl hover:shadow-primary/10 transition-all duration-300">
        <CardHeader>
          <CardTitle>Upload CSV File</CardTitle>
          <CardDescription>Drag and drop or click to select a file</CardDescription>
        </CardHeader>
        <CardContent>
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={cn(
              "relative rounded-lg border-2 border-dashed transition-all duration-300",
              isDragging
                ? "border-primary bg-primary/10 scale-105 shadow-lg shadow-primary/30"
                : "border-white/20 hover:border-white/40 hover:bg-white/5",
            )}
          >
            <input
              type="file"
              accept=".csv"
              onChange={handleFileInput}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <div className="flex flex-col items-center justify-center py-16 px-4 transition-all duration-300">
              <Upload
                className={cn(
                  "h-12 w-12 text-muted-foreground mb-4 transition-all duration-300",
                  isDragging && "scale-125 text-primary",
                )}
              />
              <p className="text-lg font-medium mb-2">
                {isDragging ? "Drop your file here" : "Drag & drop your CSV file"}
              </p>
              <p className="text-sm text-muted-foreground mb-4">or click to browse</p>
              <Button
                variant="outline"
                size="sm"
                className="hover:scale-105 transition-transform duration-300 bg-transparent"
              >
                Select File
              </Button>
            </div>
          </div>

          {/* Uploaded File Info */}
          {uploadedFile && (
            <div className="mt-6 flex items-center gap-4 rounded-lg border border-white/10 bg-white/5 p-4 animate-scale-in hover:bg-white/10 hover:shadow-lg hover:shadow-secondary/20 transition-all duration-300">
              <FileText className="h-8 w-8 text-primary" />
              <div className="flex-1">
                <p className="font-medium">{uploadedFile.name}</p>
                <p className="text-sm text-muted-foreground">
                  {loading ? "Uploading..." : "Ready to import"}
                </p>
              </div>
              <CheckCircle2 className="h-5 w-5 text-secondary animate-pulse" />
              <div className="flex gap-2">
                <Button
                  onClick={handleUploadToBackend}
                  disabled={loading}
                  className="hover:scale-105 hover:shadow-lg hover:shadow-primary/30 transition-all duration-300"
                >
                  {loading ? "Uploading..." : "Import to Database"}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleRemoveFile}
                  className="hover:scale-110 transition-transform duration-300"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Preview */}
      {preview && headers.length > 0 && (
        <Card className="glass-card border-white/10 animate-fade-in hover:shadow-xl hover:shadow-primary/5 transition-all duration-300">
          <CardHeader>
            <CardTitle>Data Preview</CardTitle>
            <CardDescription>First {preview.length} rows of the uploaded file</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border border-white/10 overflow-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-white/10 hover:bg-white/5">
                    {headers.map((h, i) => (
                      <TableHead key={i}>{h}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.map((row, idx) => (
                    <TableRow key={idx} className="border-white/10 hover:bg-white/10 transition-all">
                      {row.map((val: any, i: number) => (
                        <TableCell key={i} className="font-mono text-sm">
                          {val}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <Button
                variant="outline"
                onClick={handleRemoveFile}
                className="hover:scale-105 transition-transform duration-300 bg-transparent"
              >
                Cancel
              </Button>
              <Button
                onClick={handleUploadToBackend}
                disabled={loading}
                className="hover:scale-105 hover:shadow-lg hover:shadow-primary/30 transition-all duration-300"
              >
                {loading ? "Uploading..." : "Import to Database"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
