"use client"

import React, { useState } from "react"
import { cn } from "@/lib/utils"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Network, GitBranch, Hash, Database, MapPin } from "lucide-react"
import { toast } from "sonner"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

const indexTypes = [
  {
    id: "sequential",
    name: "Sequential Index",
    icon: Database,
    description: "Linear search through ordered data",
    complexity: "O(n)",
    color: "text-blue-400",
  },
  {
    id: "isam",
    name: "ISAM",
    icon: GitBranch,
    description: "Indexed Sequential Access Method",
    complexity: "O(log n)",
    color: "text-purple-400",
  },
  {
    id: "hash",
    name: "Hash Index",
    icon: Hash,
    description: "Direct access using hash function",
    complexity: "O(1)",
    color: "text-emerald-400",
  },
  {
    id: "btree",
    name: "B+ Tree",
    icon: Network,
    description: "Balanced tree structure for range queries",
    complexity: "O(log n)",
    color: "text-orange-400",
  },
  {
    id: "rtree",
    name: "R-Tree",
    icon: MapPin,
    description: "Spatial indexing for geographic data",
    complexity: "O(log n)",
    color: "text-pink-400",
  },
]

export function IndexExplorer() {
  const [selectedIndex, setSelectedIndex] = useState("sequential")
  const [loading, setLoading] = useState(false)

  const handleCreateIndex = async (indexType: string) => {
    setLoading(true)
    try {
      const res = await fetch("http://localhost:8000/create_index", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          index_type: indexType.toLowerCase(),
          table_name: "uploaded_table", // 👈 aquí puedes cambiar dinámicamente la tabla
        }),
      })

      const data = await res.json()
      if (data.ok) {
        toast.success("Index created successfully!", {
          description: data.message,
        })
      } else {
        toast.error("Error creating index", { description: data.error })
      }
    } catch (err: any) {
      toast.error("Connection error", { description: err.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="animate-fade-in">
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-foreground/70 bg-clip-text text-transparent">
          Index Explorer
        </h1>
        <p className="text-muted-foreground mt-2">Visualize and compare different indexing structures</p>
      </div>

      {/* Index Types Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {indexTypes.map((index, idx) => (
          <Card
            key={index.id}
            className={cn(
              "glass-card border-white/10 cursor-pointer transition-all duration-300 hover:scale-105 hover:shadow-xl animate-scale-in",
              `stagger-${idx + 1}`,
              selectedIndex === index.id && "ring-2 ring-primary shadow-lg shadow-primary/30",
            )}
            onClick={() => setSelectedIndex(index.id)}
          >
            <CardHeader>
              <div className="flex items-center justify-between">
                <index.icon className={cn("h-8 w-8 transition-transform hover:scale-125 duration-300", index.color)} />
                <span className="text-xs font-mono text-muted-foreground bg-white/5 px-2 py-1 rounded">
                  {index.complexity}
                </span>
              </div>
              <CardTitle className="mt-4">{index.name}</CardTitle>
              <CardDescription>{index.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                variant="outline"
                size="sm"
                disabled={loading}
                className="w-full bg-transparent hover:bg-gradient-to-r hover:from-primary/10 hover:to-transparent hover:scale-105 transition-all duration-300"
                onClick={(e) => {
                  e.stopPropagation()
                  handleCreateIndex(index.id)
                }}
              >
                {loading ? "Creating..." : "Create Index"}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Index Visualization */}
      <Card className="glass-card border-white/10 animate-fade-in hover:shadow-xl hover:shadow-primary/5 transition-all duration-300">
        <CardHeader>
          <CardTitle>Index Visualization</CardTitle>
          <CardDescription>
            Visual representation of {indexTypes.find((i) => i.id === selectedIndex)?.name}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="structure" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="structure" className="transition-all duration-300">
                Structure
              </TabsTrigger>
              <TabsTrigger value="performance" className="transition-all duration-300">
                Performance
              </TabsTrigger>
              <TabsTrigger value="operations" className="transition-all duration-300">
                Operations
              </TabsTrigger>
            </TabsList>
            <TabsContent value="structure" className="space-y-4">
              <div className="rounded-lg border border-white/10 bg-gradient-to-br from-black/60 via-black/40 to-black/60 p-8 min-h-[400px] flex items-center justify-center animate-scale-in">
                <div className="text-center space-y-4">
                  <div className="flex justify-center">
                    {indexTypes.find((i) => i.id === selectedIndex)?.icon && (
                      <div className="relative animate-glow-pulse">
                        {React.createElement(indexTypes.find((i) => i.id === selectedIndex)!.icon, {
                          className: cn(
                            "h-24 w-24 transition-transform hover:scale-110 duration-300",
                            indexTypes.find((i) => i.id === selectedIndex)?.color,
                          ),
                        })}
                      </div>
                    )}
                  </div>
                  <h3 className="text-2xl font-bold">{indexTypes.find((i) => i.id === selectedIndex)?.name}</h3>
                  <p className="text-muted-foreground max-w-md">
                    {selectedIndex === "sequential" &&
                      "Data is stored in sequential order. Search requires scanning through records linearly."}
                    {selectedIndex === "isam" &&
                      "Combines sequential organization with an index. Provides faster access through index lookup."}
                    {selectedIndex === "hash" &&
                      "Uses hash function to compute record location. Provides constant-time access for exact matches."}
                    {selectedIndex === "btree" &&
                      "Self-balancing tree structure. Maintains sorted data and allows efficient range queries."}
                    {selectedIndex === "rtree" &&
                      "Spatial data structure for indexing multi-dimensional information like geographic coordinates."}
                  </p>
                </div>
              </div>
            </TabsContent>
            <TabsContent value="performance" className="space-y-4">
              <div className="space-y-4">
                <div className="rounded-lg border border-white/10 bg-white/5 p-4 hover:bg-white/10 transition-all duration-300 animate-fade-in stagger-1">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium">Search Time</span>
                    <span className="text-sm font-mono text-primary font-semibold">
                      {indexTypes.find((i) => i.id === selectedIndex)?.complexity}
                    </span>
                  </div>
                  <div className="h-2 bg-black/40 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-primary to-primary/80 transition-all duration-700 ease-out"
                      style={{
                        width: selectedIndex === "hash" ? "95%" : selectedIndex === "sequential" ? "30%" : "70%",
                      }}
                    />
                  </div>
                </div>
                <div className="rounded-lg border border-white/10 bg-white/5 p-4 hover:bg-white/10 transition-all duration-300 animate-fade-in stagger-2">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium">Insert Time</span>
                    <span className="text-sm font-mono text-secondary font-semibold">
                      {selectedIndex === "sequential" ? "O(1)" : "O(log n)"}
                    </span>
                  </div>
                  <div className="h-2 bg-black/40 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-secondary to-secondary/80 transition-all duration-700 ease-out"
                      style={{
                        width: selectedIndex === "sequential" ? "90%" : "60%",
                      }}
                    />
                  </div>
                </div>
                <div className="rounded-lg border border-white/10 bg-white/5 p-4 hover:bg-white/10 transition-all duration-300 animate-fade-in stagger-3">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium">Space Efficiency</span>
                    <span className="text-sm font-mono text-blue-400 font-semibold">
                      {selectedIndex === "sequential" ? "High" : selectedIndex === "hash" ? "Medium" : "Low"}
                    </span>
                  </div>
                  <div className="h-2 bg-black/40 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-blue-400 to-blue-400/80 transition-all duration-700 ease-out"
                      style={{
                        width: selectedIndex === "sequential" ? "85%" : selectedIndex === "hash" ? "60%" : "45%",
                      }}
                    />
                  </div>
                </div>
              </div>
            </TabsContent>
            <TabsContent value="operations" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg border border-white/10 bg-white/5 p-4 hover:bg-white/10 hover:scale-105 transition-all duration-300 animate-fade-in stagger-1">
                  <h4 className="font-medium mb-2">Supported Operations</h4>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    <li className="flex items-center gap-2">
                      <div className="h-1.5 w-1.5 rounded-full bg-secondary animate-pulse" />
                      Point Query
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="h-1.5 w-1.5 rounded-full bg-secondary animate-pulse" />
                      {selectedIndex === "rtree" ? "Spatial Range Query" : "Range Query"}
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="h-1.5 w-1.5 rounded-full bg-secondary animate-pulse" />
                      Insert
                    </li>
                    <li className="flex items-center gap-2">
                      <div className="h-1.5 w-1.5 rounded-full bg-secondary animate-pulse" />
                      Delete
                    </li>
                  </ul>
                </div>
                <div className="rounded-lg border border-white/10 bg-white/5 p-4 hover:bg-white/10 hover:scale-105 transition-all duration-300 animate-fade-in stagger-2">
                  <h4 className="font-medium mb-2">Best Use Cases</h4>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    {selectedIndex === "sequential" && (
                      <>
                        <li>• Small datasets</li>
                        <li>• Sequential access patterns</li>
                        <li>• Simple implementation</li>
                      </>
                    )}
                    {selectedIndex === "isam" && (
                      <>
                        <li>• Static or rarely updated data</li>
                        <li>• Batch processing</li>
                        <li>• Historical records</li>
                      </>
                    )}
                    {selectedIndex === "hash" && (
                      <>
                        <li>• Exact match queries</li>
                        <li>• High-speed lookups</li>
                        <li>• Unique key access</li>
                      </>
                    )}
                    {selectedIndex === "btree" && (
                      <>
                        <li>• Range queries</li>
                        <li>• Sorted data access</li>
                        <li>• Database indexes</li>
                      </>
                    )}
                    {selectedIndex === "rtree" && (
                      <>
                        <li>• Geographic data</li>
                        <li>• Spatial queries</li>
                        <li>• Map applications</li>
                      </>
                    )}
                  </ul>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}
