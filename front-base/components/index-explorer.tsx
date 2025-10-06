"use client"

import React, { useState, useEffect } from "react"
import { cn } from "@/lib/utils"
import { Line } from "react-chartjs-2"; // Para el gráfico de performance
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js'; // Importa LineElement
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Network, GitBranch, Hash, Database, MapPin } from "lucide-react"
import { toast } from "sonner"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"

const indexTypes = [
  { id: "sequential", name: "Sequential Index", icon: Database, description: "Linear search through ordered data", complexity: "O(n)", color: "text-blue-400" },
  { id: "isam", name: "ISAM", icon: GitBranch, description: "Indexed Sequential Access Method", complexity: "O(log n)", color: "text-purple-400" },
  { id: "hash", name: "Hash Index", icon: Hash, description: "Direct access using hash function", complexity: "O(1)", color: "text-emerald-400" },
  { id: "btree", name: "B+ Tree", icon: Network, description: "Balanced tree structure for range queries", complexity: "O(log n)", color: "text-orange-400" },
  { id: "rtree", name: "R-Tree", icon: MapPin, description: "Spatial indexing for geographic data", complexity: "O(log n)", color: "text-pink-400" },
]

export function IndexExplorer({ defaultTable }: { defaultTable: string }) {
  const [selectedIndex, setSelectedIndex] = useState("sequential")
  const [loadingIndex, setLoadingIndex] = useState<string | null>(null)
  const [tableName, setTableName] = useState(defaultTable)
  const [columnName, setColumnName] = useState("")
  const [columns, setColumns] = useState<string[]>([]) // Añadido para las columnas
  const [tableExists, setTableExists] = useState(false) // Verifica si la tabla existe

  const [performanceData, setPerformanceData] = useState({
    labels: ["Query 1"],
    datasets: [
      {
        label: "Without Index",
        data: [0],
        borderColor: "rgba(75, 192, 192, 1)",
        backgroundColor: "rgba(75, 192, 192, 0.2)",
      },
      {
        label: "With Index",
        data: [0],
        borderColor: "rgba(153, 102, 255, 1)",
        backgroundColor: "rgba(153, 102, 255, 0.2)",
      },
    ],
  });

  // Registra los elementos necesarios de Chart.js
  ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    PointElement,  // Registra el PointElement
    LineElement,   // Registra el LineElement
    Title,
    Tooltip,
    Legend
  );

  // Llamar al backend para obtener las columnas cuando la tabla se ha seleccionado
  useEffect(() => {
    if (tableName) {
      fetch(`http://localhost:8000/get_table_columns?table_name=${tableName}`)
        .then((res) => res.json())
        .then((data) => {
          if (data.ok) {
            setColumns(data.columns) // Asignar las columnas recibidas
            setTableExists(true)
          } else {
            setColumns([])
            setTableExists(false)
          }
        })
        .catch(() => {
          setColumns([])
          setTableExists(false)
        })
    }
  }, [tableName])

  const handleCreateIndex = async (indexType: string) => {
    if (!tableName) {
      toast.error("Missing table name", { description: "Please enter a table name first." })
      return
    }
    if (!columnName) {
      toast.error("Missing column name", { description: "Please enter a column name first." })
      return
    }

    setLoadingIndex(indexType)
    try {
      const query = `CREATE INDEX ${indexType} ON ${tableName} (${columnName})`
      const res = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const data = await res.json()
      if (data.ok) {
        toast.success("Index created successfully!", {
          description: `${indexType} index on ${tableName}(${columnName})`,
        })
      } else {
        toast.error("Error creating index", { description: data.error })
      }
    } catch (err: any) {
      toast.error("Connection error", { description: err.message })
    } finally {
      setLoadingIndex(null)
    }
  }

  // Función para ejecutar la consulta y actualizar los datos del gráfico de rendimiento
  const executeQueryAndUpdatePerformance = async () => {
    if (!tableName || !columnName) {
      toast.error("Please provide both table and column names")
      return
    }

    try {
      const query = `SELECT * FROM ${tableName} WHERE ${columnName} IS NOT NULL LIMIT 10`  // Consulta ejemplo

      // Ejecutar la consulta sin índices
      const startTimeNoIndex = performance.now()
      const resNoIndex = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      })
      const dataNoIndex = await resNoIndex.json()
      const endTimeNoIndex = performance.now()
      const timeNoIndex = (endTimeNoIndex - startTimeNoIndex).toFixed(2)

      // Ejecutar la consulta con índices
      const startTimeWithIndex = performance.now()
      const resWithIndex = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      })
      const dataWithIndex = await resWithIndex.json()
      const endTimeWithIndex = performance.now()
      const timeWithIndex = (endTimeWithIndex - startTimeWithIndex).toFixed(2)

      // Actualizar los datos de rendimiento
      setPerformanceData({
        labels: ["Query 1"],  // Solo un query por ahora
        datasets: [
          {
            label: "Without Index",
            data: [parseFloat(timeNoIndex)],
            borderColor: "rgba(75, 192, 192, 1)",
            backgroundColor: "rgba(75, 192, 192, 0.2)",
          },
          {
            label: "With Index",
            data: [parseFloat(timeWithIndex)],
            borderColor: "rgba(153, 102, 255, 1)",
            backgroundColor: "rgba(153, 102, 255, 0.2)",
          },
        ],
      })
      toast.success("Query executed and performance data updated")

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "An unexpected error occurred";
      toast.error("Error executing query or fetching performance data", { description: errorMessage });
    }
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="animate-fade-in">
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-foreground/70 bg-clip-text text-transparent">
          Index Explorer
        </h1>
        <p className="text-muted-foreground mt-2">
          Visualize and compare different indexing structures
        </p>
      </div>

      {/* Table & Column selector */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center">
        <Input
          placeholder="Enter table name..."
          value={tableName}
          onChange={(e) => setTableName(e.target.value)}
          className="max-w-sm"
        />
        <Input
          placeholder="Enter column name..."
          value={columnName}
          onChange={(e) => setColumnName(e.target.value)}
          className="max-w-sm"
          list="columns-list" // Habilitar lista de autocompletado
        />
        <datalist id="columns-list">
          {columns.map((col, idx) => (
            <option key={idx} value={col} />
          ))}
        </datalist>
        <span className="text-sm text-muted-foreground">
          Target: <strong>{tableName || "none"}</strong> ({columnName || "no column"})
        </span>
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
              disabled={loadingIndex !== null} // Cambiar a una comprobación booleana
              className="w-full bg-transparent hover:bg-gradient-to-r hover:from-primary/10 hover:to-transparent hover:scale-105 transition-all duration-300"
              onClick={(e) => {
                e.stopPropagation()
                handleCreateIndex(index.id)
              }}
            >
              {loadingIndex === index.id ? "Creating..." : "Create Index"}
            </Button>

            </CardContent>
          </Card>
        ))}
      </div>

      {/* Performance Visualization */}
      <Card className="glass-card border-white/10 animate-fade-in hover:shadow-xl hover:shadow-primary/5 transition-all duration-300">
        <CardHeader>
          <CardTitle>Index Performance</CardTitle>
          <CardDescription>Compare query performance with and without indices</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={executeQueryAndUpdatePerformance} className="w-full bg-gradient-to-r from-primary to-primary/90">
            Execute Query and Show Performance
          </Button>
          <Line data={performanceData} />
        </CardContent>
      </Card>
    </div>
  )
}
