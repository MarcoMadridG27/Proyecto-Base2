"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { MapPin, Circle, Square, Search } from "lucide-react"
import { toast } from "sonner"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { cn } from "@/lib/utils"

const peruCities = [
  { id: 1, name: "Lima", lat: -12.0464, lng: -77.0428, population: 9674755 },
  { id: 2, name: "Arequipa", lat: -16.409, lng: -71.5375, population: 1008290 },
  { id: 3, name: "Cusco", lat: -13.5319, lng: -71.9675, population: 428450 },
  { id: 4, name: "Trujillo", lat: -8.1116, lng: -79.0288, population: 919899 },
  { id: 5, name: "Chiclayo", lat: -6.7714, lng: -79.841, population: 600440 },
  { id: 6, name: "Piura", lat: -5.1945, lng: -80.6328, population: 484475 },
  { id: 7, name: "Iquitos", lat: -3.7437, lng: -73.2516, population: 437376 },
  { id: 8, name: "Huancayo", lat: -12.0653, lng: -75.2049, population: 376657 },
]

export function SpatialResults() {
  const [searchType, setSearchType] = useState<"circular" | "rectangular">("circular")
  const [results, setResults] = useState(peruCities)

  const handleCircularSearch = () => {
    toast.success("Circular search completed!", {
      description: `Found ${results.length} points within radius.`,
    })
  }

  const handleRectangularSearch = () => {
    toast.success("Rectangular search completed!", {
      description: `Found ${results.length} points within bounds.`,
    })
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="animate-fade-in">
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-foreground/70 bg-clip-text text-transparent">
          Spatial Results
        </h1>
        <p className="text-muted-foreground mt-2">Interactive map with geographic search capabilities</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Search Controls */}
        <Card className="glass-card border-white/10 lg:col-span-1 animate-slide-in-left hover:shadow-xl hover:shadow-primary/10 transition-all duration-300">
          <CardHeader>
            <CardTitle>Search Parameters</CardTitle>
            <CardDescription>Configure spatial query</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={searchType} onValueChange={(v) => setSearchType(v as any)}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="circular" className="gap-2 transition-all duration-300">
                  <Circle className="h-4 w-4" />
                  Circular
                </TabsTrigger>
                <TabsTrigger value="rectangular" className="gap-2 transition-all duration-300">
                  <Square className="h-4 w-4" />
                  Rectangular
                </TabsTrigger>
              </TabsList>

              <TabsContent value="circular" className="space-y-4 mt-4">
                <div className="space-y-2 animate-fade-in stagger-1">
                  <Label>Center Latitude</Label>
                  <Input
                    type="number"
                    placeholder="-12.0464"
                    defaultValue="-12.0464"
                    className="bg-black/40 border-white/10 focus:border-primary/50 focus:shadow-lg focus:shadow-primary/20 transition-all duration-300"
                  />
                </div>
                <div className="space-y-2 animate-fade-in stagger-2">
                  <Label>Center Longitude</Label>
                  <Input
                    type="number"
                    placeholder="-77.0428"
                    defaultValue="-77.0428"
                    className="bg-black/40 border-white/10 focus:border-primary/50 focus:shadow-lg focus:shadow-primary/20 transition-all duration-300"
                  />
                </div>
                <div className="space-y-2 animate-fade-in stagger-3">
                  <Label>Radius (km)</Label>
                  <Input
                    type="number"
                    placeholder="100"
                    defaultValue="500"
                    className="bg-black/40 border-white/10 focus:border-primary/50 focus:shadow-lg focus:shadow-primary/20 transition-all duration-300"
                  />
                </div>
                <Button
                  className="w-full gap-2 hover:scale-105 hover:shadow-lg hover:shadow-primary/30 transition-all duration-300 bg-gradient-to-r from-primary to-primary/90 animate-fade-in stagger-4"
                  onClick={handleCircularSearch}
                >
                  <Search className="h-4 w-4" />
                  Search
                </Button>
              </TabsContent>

              <TabsContent value="rectangular" className="space-y-4 mt-4">
                <div className="space-y-2 animate-fade-in stagger-1">
                  <Label>Min Latitude</Label>
                  <Input
                    type="number"
                    placeholder="-18.0"
                    defaultValue="-18.0"
                    className="bg-black/40 border-white/10 focus:border-primary/50 focus:shadow-lg focus:shadow-primary/20 transition-all duration-300"
                  />
                </div>
                <div className="space-y-2 animate-fade-in stagger-2">
                  <Label>Max Latitude</Label>
                  <Input
                    type="number"
                    placeholder="-3.0"
                    defaultValue="-3.0"
                    className="bg-black/40 border-white/10 focus:border-primary/50 focus:shadow-lg focus:shadow-primary/20 transition-all duration-300"
                  />
                </div>
                <div className="space-y-2 animate-fade-in stagger-3">
                  <Label>Min Longitude</Label>
                  <Input
                    type="number"
                    placeholder="-81.0"
                    defaultValue="-81.0"
                    className="bg-black/40 border-white/10 focus:border-primary/50 focus:shadow-lg focus:shadow-primary/20 transition-all duration-300"
                  />
                </div>
                <div className="space-y-2 animate-fade-in stagger-4">
                  <Label>Max Longitude</Label>
                  <Input
                    type="number"
                    placeholder="-68.0"
                    defaultValue="-68.0"
                    className="bg-black/40 border-white/10 focus:border-primary/50 focus:shadow-lg focus:shadow-primary/20 transition-all duration-300"
                  />
                </div>
                <Button
                  className="w-full gap-2 hover:scale-105 hover:shadow-lg hover:shadow-secondary/30 transition-all duration-300 bg-gradient-to-r from-secondary to-secondary/90 animate-fade-in stagger-5"
                  onClick={handleRectangularSearch}
                >
                  <Search className="h-4 w-4" />
                  Search
                </Button>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* Map Visualization */}
        <Card className="glass-card border-white/10 lg:col-span-2 animate-scale-in hover:shadow-xl hover:shadow-primary/5 transition-all duration-300">
          <CardHeader>
            <CardTitle>Map View</CardTitle>
            <CardDescription>Geographic distribution of data points in Peru</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border border-white/10 bg-gradient-to-br from-primary/10 via-background to-secondary/10 p-8 min-h-[500px] relative overflow-hidden shadow-inner">
              {/* Simplified Peru map representation */}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="relative w-full h-full max-w-md">
                  {peruCities.map((city, index) => (
                    <div
                      key={city.id}
                      className={cn("absolute group cursor-pointer animate-fade-in", `stagger-${index + 1}`)}
                      style={{
                        left: `${((city.lng + 81) / 13) * 100}%`,
                        top: `${((city.lat + 18) / 15) * 100}%`,
                      }}
                    >
                      <div className="relative">
                        <MapPin className="h-6 w-6 text-primary drop-shadow-lg group-hover:scale-150 group-hover:drop-shadow-2xl transition-all duration-300 filter group-hover:brightness-150" />
                        <div className="absolute inset-0 h-6 w-6 bg-primary/30 rounded-full blur-md group-hover:blur-lg group-hover:scale-150 transition-all duration-300" />
                        <div className="absolute left-8 top-0 opacity-0 group-hover:opacity-100 transition-all duration-300 bg-black/95 border border-primary/30 rounded-lg p-3 whitespace-nowrap z-10 shadow-xl shadow-primary/20 scale-95 group-hover:scale-100">
                          <p className="font-medium text-sm">{city.name}</p>
                          <p className="text-xs text-muted-foreground">Pop: {city.population.toLocaleString()}</p>
                          <p className="text-xs text-muted-foreground font-mono">
                            {city.lat.toFixed(4)}, {city.lng.toFixed(4)}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Results Table */}
      <Card className="glass-card border-white/10 animate-fade-in hover:shadow-xl hover:shadow-primary/5 transition-all duration-300">
        <CardHeader>
          <CardTitle>Search Results</CardTitle>
          <CardDescription>{results.length} locations found</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {results.map((city, index) => (
              <div
                key={city.id}
                className={cn(
                  "flex items-center justify-between rounded-lg border border-white/10 bg-white/5 p-4 hover:bg-white/10 hover:border-primary/30 hover:scale-[1.02] hover:shadow-lg hover:shadow-primary/10 transition-all duration-300 animate-fade-in",
                  `stagger-${index + 1}`,
                )}
              >
                <div className="flex items-center gap-4">
                  <MapPin className="h-5 w-5 text-primary" />
                  <div>
                    <p className="font-medium">{city.name}</p>
                    <p className="text-sm text-muted-foreground font-mono">
                      {city.lat.toFixed(4)}, {city.lng.toFixed(4)}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium">{city.population.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground">population</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
