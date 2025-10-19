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
import { useEffect } from "react"

// Note: removed static sample data to avoid hydration mismatches.
// Results are populated from the backend; for initial empty state use [].

export function SpatialResults() {
  const [searchType, setSearchType] = useState<"circular" | "rectangular">("circular")
  const [results, setResults] = useState<any[]>([])
  const [centerLat, setCenterLat] = useState<number | undefined>(undefined)
  const [centerLng, setCenterLng] = useState<number | undefined>(undefined)
  const [radiusKm, setRadiusKm] = useState<number>(50)
  const [loading, setLoading] = useState(false)
  const [usedIndexType, setUsedIndexType] = useState<string | null>(null)
  const [usedIndexColumns, setUsedIndexColumns] = useState<string[] | null>(null)
  const [tablesWithIndexes, setTablesWithIndexes] = useState<any[]>([])
  const [allTables, setAllTables] = useState<string[]>([])
  const [selectedTable, setSelectedTable] = useState<string | null>(null)
  const [selectedIndexKey, setSelectedIndexKey] = useState<string | null>(null) // format: table.column

  const handleCircularSearch = async () => {
    setLoading(true)
    setUsedIndexType(null)
    setUsedIndexColumns(null)
    try {
      // convert km -> approximate degrees (very rough): 1 deg ~ 111 km
      const radiusDeg = Number(radiusKm) / 111.0
  // Build SQL: use order [lon, lat] as backend expects (coordenadas IN ([lon, lat], radius))
      if (centerLat == null || centerLng == null) {
        toast.error('Please provide center latitude and longitude')
        setLoading(false)
        return
      }
      const table = selectedTable || 'atropellos'
      const lon = Number(centerLng)
      const lat = Number(centerLat)
  const sql = `SELECT * FROM ${table} WHERE coordenadas IN ([${lon}, ${lat}], ${radiusDeg});`

      const bodyPayload: any = { query: sql, use_index: true, index_hint: null }
      // pass index hint if user selected a specific index
      if (selectedIndexKey && selectedIndexKey !== 'auto' && selectedIndexKey !== 'none') bodyPayload.index_hint = selectedIndexKey

      const res = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bodyPayload),
      })
      const data = await res.json()
      if (data.ok) {
        const rows = Array.isArray(data.result) ? data.result : []
        setResults(rows.length ? rows : [])
        if (data.used_index_type) setUsedIndexType(String(data.used_index_type))
        if (data.used_index_columns) setUsedIndexColumns(Array.isArray(data.used_index_columns) ? data.used_index_columns : null)
        toast.success("Spatial search completed", { description: `Found ${rows.length} rows` })
      } else {
        toast.error("Search failed", { description: data.error || "Unknown error" })
      }
    } catch (err: any) {
      toast.error("Connection error", { description: err?.message || String(err) })
    } finally {
      setLoading(false)
    }
  }

  // Load tables with indexes so the user can pick which table to query
  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch("http://localhost:8000/tables_with_indexes")
        const data = await res.json()
        if (data.ok) {
          setTablesWithIndexes(Array.isArray(data.tables) ? data.tables : [])
          if (Array.isArray(data.tables) && data.tables.length > 0) {
            setSelectedTable(data.tables[0].table)
            // choose first index option by default
            const firstIx = data.tables[0].indexes && data.tables[0].indexes[0]
            if (firstIx) setSelectedIndexKey(`${data.tables[0].table}.${firstIx.column}`)
          }
        }
      } catch (e) {
        // ignore
      }
    }
    load()
    // also load all tables (even those without indexes) so user can choose table
    ;(async () => {
      try {
        const r = await fetch("http://localhost:8000/system_stats")
        const d = await r.json()
        if (d.ok && Array.isArray(d.stats?.tables)) {
          setAllTables(d.stats.tables)
          if (!selectedTable && d.stats.tables.length > 0) setSelectedTable(d.stats.tables[0])
        }
      } catch (e) {}
    })()
  }, [])

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
                <div className="flex items-center gap-2">
                  <div className="w-1/2">
                    <Label>Table</Label>
                    <select className="w-full p-2 rounded bg-black/30 border border-white/10" value={selectedTable ?? ''} onChange={(e) => setSelectedTable(e.target.value)}>
                      {allTables.map((t) => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                  </div>
                  <div className="w-1/2">
                    <Label>Index</Label>
                    <select className="w-full p-2 rounded bg-black/30 border border-white/10" value={selectedIndexKey ?? ''} onChange={(e) => setSelectedIndexKey(e.target.value)}>
                      <option value="auto">Auto (choose best)</option>
                      <option value="none">None (force scan)</option>
                      {tablesWithIndexes.filter((t) => t.table === selectedTable).flatMap((t) => t.indexes.map((ix: any) => ({ table: t.table, ix })) ).map((pair: any) => (
                        <option key={`${pair.table}.${pair.ix.column}`} value={`${pair.table}.${pair.ix.column}`}>{`${pair.table}.${pair.ix.column} (${pair.ix.type})`}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="text-sm text-muted-foreground mt-2">Tip: R-Tree indexes expect coordinate order [lon, lat] for the SQL spatial predicate.</div>
                <div className="space-y-2 animate-fade-in stagger-1">
                  <Label>Center Latitude</Label>
                  <Input
                    type="number"
                    placeholder="-12.0464"
                    value={centerLat == null ? '' : String(centerLat)}
                    onChange={(e) => setCenterLat(e.target.value === '' ? undefined : Number(e.target.value))}
                    className="bg-black/40 border-white/10 focus:border-primary/50 focus:shadow-lg focus:shadow-primary/20 transition-all duration-300"
                  />
                </div>
                <div className="space-y-2 animate-fade-in stagger-2">
                  <Label>Center Longitude</Label>
                  <Input
                    type="number"
                    placeholder="-77.0428"
                    value={centerLng == null ? '' : String(centerLng)}
                    onChange={(e) => setCenterLng(e.target.value === '' ? undefined : Number(e.target.value))}
                    className="bg-black/40 border-white/10 focus:border-primary/50 focus:shadow-lg focus:shadow-primary/20 transition-all duration-300"
                  />
                </div>
                <div className="space-y-2 animate-fade-in stagger-3">
                  <Label>Radius (km)</Label>
                  <Input
                    type="number"
                    placeholder="100"
                    value={String(radiusKm)}
                    onChange={(e) => setRadiusKm(Number(e.target.value))}
                    className="bg-black/40 border-white/10 focus:border-primary/50 focus:shadow-lg focus:shadow-primary/20 transition-all duration-300"
                  />
                </div>
                <Button
                  className="w-full gap-2 hover:scale-105 hover:shadow-lg hover:shadow-primary/30 transition-all duration-300 bg-gradient-to-r from-primary to-primary/90 animate-fade-in stagger-4"
                  onClick={handleCircularSearch}
                  disabled={loading}
                >
                  <Search className="h-4 w-4" />
                  {loading ? 'Searching...' : 'Search'}
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
                  {((results || []).filter(Boolean).length === 0) ? (
                    <div className="text-sm text-muted-foreground">No coordinates to display on map.</div>
                  ) : (
                    (results || []).filter(Boolean).map((row, index) => {
                    // Try to extract coordinates from several possible shapes
                    let lat = null
                    let lng = null
                    if (row && typeof row === 'object') {
                      if (Array.isArray(row.coordenadas) && row.coordenadas.length >= 2) {
                        lng = Number(row.coordenadas[0])
                        lat = Number(row.coordenadas[1])
                      } else if (row.lat && row.lon) {
                        lat = Number(row.lat)
                        lng = Number(row.lon)
                      } else if (row.y && row.x) {
                        lat = Number(row.y)
                        lng = Number(row.x)
                      } else if (row.coordenadas && typeof row.coordenadas === 'string') {
                        const s = row.coordenadas.replace(/\[|\]/g, '')
                        const p = s.split(',').map((p: string) => p.trim())
                        if (p.length >= 2) {
                          lng = Number(p[0])
                          lat = Number(p[1])
                        }
                      }
                    }
                    // if no coordinates in row, skip rendering marker
                    if (lat == null || lng == null) return null
                    const displayLat = lat
                    const displayLng = lng
                    return (
                      <div
                        key={index}
                        className={cn("absolute group cursor-pointer animate-fade-in", `stagger-${index + 1}`)}
                        style={{
                          left: `${((displayLng + 81) / 13) * 100}%`,
                          top: `${((displayLat + 18) / 15) * 100}%`,
                        }}
                      >
                        <div className="relative">
                          <MapPin className="h-6 w-6 text-primary drop-shadow-lg group-hover:scale-150 group-hover:drop-shadow-2xl transition-all duration-300 filter group-hover:brightness-150" />
                          <div className="absolute inset-0 h-6 w-6 bg-primary/30 rounded-full blur-md group-hover:blur-lg group-hover:scale-150 transition-all duration-300" />
                          <div className="absolute left-8 top-0 opacity-0 group-hover:opacity-100 transition-all duration-300 bg-black/95 border border-primary/30 rounded-lg p-3 whitespace-nowrap z-10 shadow-xl shadow-primary/20 scale-95 group-hover:scale-100">
                            <p className="font-medium text-sm">{row && row.name ? row.name : 'result'}</p>
                            <p className="text-xs text-muted-foreground">{row && row.population ? Number(row.population).toLocaleString('en-US') : ''}</p>
                            <p className="text-xs text-muted-foreground font-mono">
                              {displayLat.toFixed(4)}, {displayLng.toFixed(4)}
                            </p>
                          </div>
                        </div>
                      </div>
                    )
                    })
                  )}
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
            {results.map((city: any, index: number) => (
              <div
                key={city && (city.id ?? `${index}`)}
                className={cn(
                  "flex items-center justify-between rounded-lg border border-white/10 bg-white/5 p-4 hover:bg-white/10 hover:border-primary/30 hover:scale-[1.02] hover:shadow-lg hover:shadow-primary/10 transition-all duration-300 animate-fade-in",
                  `stagger-${index + 1}`,
                )}
              >
                <div className="flex items-center gap-4">
                  <MapPin className="h-5 w-5 text-primary" />
                  <div>
                    <p className="font-medium">{city.name ?? 'result'}</p>
                    <p className="text-sm text-muted-foreground font-mono">
                      {city.lat != null && city.lng != null ? `${Number(city.lat).toFixed(4)}, ${Number(city.lng).toFixed(4)}` : ''}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium">{city.population ? Number(city.population).toLocaleString('en-US') : ''}</p>
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
