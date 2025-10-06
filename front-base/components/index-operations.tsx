"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Line, Bar } from "react-chartjs-2"
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js'
import { toast } from "sonner"
import { Search, Ruler, Plus, Trash2 } from "lucide-react"

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Title, Tooltip, Legend)

type OperationResult = {
  operation: string
  table: string
  column: string
  timeMs: number
  timestamp: number
  resultCount?: number
}

export function IndexOperations() {
  const [tableName, setTableName] = useState("prueba")
  const [columnName, setColumnName] = useState("observation_id")
  const [searchKey, setSearchKey] = useState("900")
  const [rangeStart, setRangeStart] = useState("100")
  const [rangeEnd, setRangeEnd] = useState("200")
  const [addKey, setAddKey] = useState("1001")
  const [removeKey, setRemoveKey] = useState("900")
  
  const [operations, setOperations] = useState<OperationResult[]>([])

  // Load operations from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem("index_operations_history")
      if (saved) {
        setOperations(JSON.parse(saved))
      }
    } catch {}
  }, [])

  // Save operations to localStorage
  useEffect(() => {
    try {
      localStorage.setItem("index_operations_history", JSON.stringify(operations))
    } catch {}
  }, [operations])

  const addOperation = (operation: string, timeMs: number, resultCount?: number) => {
    const newOp: OperationResult = {
      operation,
      table: tableName,
      column: columnName,
      timeMs,
      timestamp: Date.now(),
      resultCount
    }
    setOperations(prev => [...prev.slice(-19), newOp]) // Keep last 20
  }

  const executeSearch = async () => {
    try {
      const query = `SELECT * FROM ${tableName} WHERE ${columnName} = ${searchKey}`
      const startTime = performance.now()
      
      const res = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, use_index: true }),
      })
      
      const data = await res.json()
      const endTime = performance.now()
      
      if (data.ok) {
        const timeMs = endTime - startTime
        const resultCount = Array.isArray(data.result) ? data.result.length : 0
        addOperation("search", timeMs, resultCount)
        toast.success(`Search completed in ${timeMs.toFixed(2)}ms`, { 
          description: `Found ${resultCount} results` 
        })
      } else {
        toast.error("Search failed", { description: data.error })
      }
    } catch (err: any) {
      toast.error("Search error", { description: err.message })
    }
  }

  const executeRangeSearch = async () => {
    try {
      const query = `SELECT * FROM ${tableName} WHERE ${columnName} BETWEEN ${rangeStart} AND ${rangeEnd}`
      const startTime = performance.now()
      
      const res = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, use_index: true }),
      })
      
      const data = await res.json()
      const endTime = performance.now()
      
      if (data.ok) {
        const timeMs = endTime - startTime
        const resultCount = Array.isArray(data.result) ? data.result.length : 0
        addOperation("rangeSearch", timeMs, resultCount)
        toast.success(`Range search completed in ${timeMs.toFixed(2)}ms`, { 
          description: `Found ${resultCount} results` 
        })
      } else {
        toast.error("Range search failed", { description: data.error })
      }
    } catch (err: any) {
      toast.error("Range search error", { description: err.message })
    }
  }

  const executeAdd = async () => {
    try {
      const query = `INSERT INTO ${tableName} VALUES (${addKey}, 'Test Record', 'Test Species', 'Test Family', 'Test Genus', 1.5, 50.0, 'Adult', 'Unknown', '2024-01-01', 'Test Country', 'Test Habitat', 'Test Status', 'Test Observer', 'Test Notes')`
      const startTime = performance.now()
      
      const res = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, use_index: false }),
      })
      
      const data = await res.json()
      const endTime = performance.now()
      
      if (data.ok) {
        const timeMs = endTime - startTime
        addOperation("add", timeMs)
        toast.success(`Add completed in ${timeMs.toFixed(2)}ms`)
      } else {
        toast.error("Add failed", { description: data.error })
      }
    } catch (err: any) {
      toast.error("Add error", { description: err.message })
    }
  }

  const executeRemove = async () => {
    try {
      const query = `DELETE FROM ${tableName} WHERE ${columnName} = ${removeKey}`
      const startTime = performance.now()
      
      const res = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, use_index: false }),
      })
      
      const data = await res.json()
      const endTime = performance.now()
      
      if (data.ok) {
        const timeMs = endTime - startTime
        addOperation("remove", timeMs)
        toast.success(`Remove completed in ${timeMs.toFixed(2)}ms`)
      } else {
        toast.error("Remove failed", { description: data.error })
      }
    } catch (err: any) {
      toast.error("Remove error", { description: err.message })
    }
  }

  const getChartData = (operation: string) => {
    const opData = operations.filter(op => op.operation === operation)
    return {
      labels: opData.map((_, i) => `Run ${i + 1}`),
      datasets: [{
        label: `${operation} Time (ms)`,
        data: opData.map(op => op.timeMs),
        borderColor: getOperationColor(operation),
        backgroundColor: getOperationColor(operation, 0.2),
        tension: 0.1
      }]
    }
  }

  const getOperationColor = (operation: string, alpha: number = 1) => {
    const colors = {
      search: `rgba(59, 130, 246, ${alpha})`, // blue
      rangeSearch: `rgba(16, 185, 129, ${alpha})`, // green
      add: `rgba(245, 158, 11, ${alpha})`, // yellow
      remove: `rgba(239, 68, 68, ${alpha})` // red
    }
    return colors[operation as keyof typeof colors] || `rgba(156, 163, 175, ${alpha})`
  }

  return (
    <div className="p-8 space-y-8">
      <div className="animate-fade-in">
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-foreground/70 bg-clip-text text-transparent">
          Index Operations Performance
        </h1>
        <p className="text-muted-foreground mt-2">Test and visualize the 4 core index operations</p>
      </div>

      {/* Configuration */}
      <Card className="glass-card border-white/10">
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
          <CardDescription>Set table and column for operations</CardDescription>
        </CardHeader>
        <CardContent className="flex gap-4">
          <Input 
            placeholder="Table name" 
            value={tableName} 
            onChange={e => setTableName(e.target.value)}
            className="max-w-xs"
          />
          <Input 
            placeholder="Column name" 
            value={columnName} 
            onChange={e => setColumnName(e.target.value)}
            className="max-w-xs"
          />
        </CardContent>
      </Card>

      {/* Operations */}
      <Tabs defaultValue="search" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="search" className="flex items-center gap-2">
            <Search className="h-4 w-4" />
            Search
          </TabsTrigger>
          <TabsTrigger value="range" className="flex items-center gap-2">
            <Ruler className="h-4 w-4" />
            Range Search
          </TabsTrigger>
          <TabsTrigger value="add" className="flex items-center gap-2">
            <Plus className="h-4 w-4" />
            Add
          </TabsTrigger>
          <TabsTrigger value="remove" className="flex items-center gap-2">
            <Trash2 className="h-4 w-4" />
            Remove
          </TabsTrigger>
        </TabsList>

        <TabsContent value="search" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Search Operation</CardTitle>
              <CardDescription>Find records with specific key value</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-4">
                <Input 
                  placeholder="Search key" 
                  value={searchKey} 
                  onChange={e => setSearchKey(e.target.value)}
                  className="max-w-xs"
                />
                <Button onClick={executeSearch}>Execute Search</Button>
              </div>
              {operations.filter(op => op.operation === "search").length > 0 && (
                <div className="h-64">
                  <Line data={getChartData("search")} options={{ responsive: true, maintainAspectRatio: false }} />
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="range" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Range Search Operation</CardTitle>
              <CardDescription>Find records within a key range</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-4">
                <Input 
                  placeholder="Start key" 
                  value={rangeStart} 
                  onChange={e => setRangeStart(e.target.value)}
                  className="max-w-xs"
                />
                <Input 
                  placeholder="End key" 
                  value={rangeEnd} 
                  onChange={e => setRangeEnd(e.target.value)}
                  className="max-w-xs"
                />
                <Button onClick={executeRangeSearch}>Execute Range Search</Button>
              </div>
              {operations.filter(op => op.operation === "rangeSearch").length > 0 && (
                <div className="h-64">
                  <Line data={getChartData("rangeSearch")} options={{ responsive: true, maintainAspectRatio: false }} />
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="add" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Add Operation</CardTitle>
              <CardDescription>Insert a new record</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-4">
                <Input 
                  placeholder="New key" 
                  value={addKey} 
                  onChange={e => setAddKey(e.target.value)}
                  className="max-w-xs"
                />
                <Button onClick={executeAdd}>Execute Add</Button>
              </div>
              {operations.filter(op => op.operation === "add").length > 0 && (
                <div className="h-64">
                  <Line data={getChartData("add")} options={{ responsive: true, maintainAspectRatio: false }} />
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="remove" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Remove Operation</CardTitle>
              <CardDescription>Delete records with specific key</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-4">
                <Input 
                  placeholder="Key to remove" 
                  value={removeKey} 
                  onChange={e => setRemoveKey(e.target.value)}
                  className="max-w-xs"
                />
                <Button onClick={executeRemove}>Execute Remove</Button>
              </div>
              {operations.filter(op => op.operation === "remove").length > 0 && (
                <div className="h-64">
                  <Line data={getChartData("remove")} options={{ responsive: true, maintainAspectRatio: false }} />
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Combined Performance Overview */}
      {operations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Combined Performance Overview</CardTitle>
            <CardDescription>All operations performance comparison</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <Line 
                data={{
                  labels: operations.map((_, i) => `Op ${i + 1}`),
                  datasets: [
                    {
                      label: "Search",
                      data: operations.map(op => op.operation === "search" ? op.timeMs : null),
                      borderColor: getOperationColor("search"),
                      backgroundColor: getOperationColor("search", 0.2),
                    },
                    {
                      label: "Range Search",
                      data: operations.map(op => op.operation === "rangeSearch" ? op.timeMs : null),
                      borderColor: getOperationColor("rangeSearch"),
                      backgroundColor: getOperationColor("rangeSearch", 0.2),
                    },
                    {
                      label: "Add",
                      data: operations.map(op => op.operation === "add" ? op.timeMs : null),
                      borderColor: getOperationColor("add"),
                      backgroundColor: getOperationColor("add", 0.2),
                    },
                    {
                      label: "Remove",
                      data: operations.map(op => op.operation === "remove" ? op.timeMs : null),
                      borderColor: getOperationColor("remove"),
                      backgroundColor: getOperationColor("remove", 0.2),
                    }
                  ]
                }}
                options={{ responsive: true, maintainAspectRatio: false }}
              />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
