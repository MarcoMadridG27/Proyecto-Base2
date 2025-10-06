"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Play, Download, Clock } from "lucide-react"
import { toast } from "sonner"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { cn } from "@/lib/utils"

const queryExamples = [
  'SELECT * FROM users WHERE city = "Lima"',
  "SELECT name, age FROM users WHERE age > 30",
  "SELECT city, COUNT(*) as total FROM users GROUP BY city",
]

export function SQLQuery() {
  const [query, setQuery] = useState("SELECT * FROM users LIMIT 10")
  const [resultsWithIndex, setResultsWithIndex] = useState<any[] | null>(null)
  const [resultsWithoutIndex, setResultsWithoutIndex] = useState<any[] | null>(null)
  const [executionTimeWithIndex, setExecutionTimeWithIndex] = useState<number | null>(null)
  const [executionTimeWithoutIndex, setExecutionTimeWithoutIndex] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)

// Frontend: Cambio de las rutas a una sola consulta
const handleExecuteQueryWithIndex = async () => {
  const startTime = performance.now();
  setLoading(true);

  try {
    const res = await fetch("http://localhost:8000/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, use_index: true }),  // Asegúrate de pasar el parámetro use_index
    });

    const data = await res.json();
    const endTime = performance.now();
    setExecutionTimeWithIndex(endTime - startTime);

    if (data.ok) {
      setResultsWithIndex(data.result);
      toast.success("Query executed with index successfully!", {
        description: `Returned ${Array.isArray(data.result) ? data.result.length : 0} rows in ${(endTime - startTime).toFixed(2)}ms`,
      });
    } else {
      toast.error("Error executing query with index", { description: data.error });
    }
  } catch (err: any) {
    toast.error("Connection error", { description: err.message });
  } finally {
    setLoading(false);
  }
};

// Lo mismo para el query sin índice:
const handleExecuteQueryWithoutIndex = async () => {
  const startTime = performance.now();
  setLoading(true);

  try {
    const res = await fetch("http://localhost:8000/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, use_index: false }),  // Pasando use_index como false
    });

    const data = await res.json();
    const endTime = performance.now();
    setExecutionTimeWithoutIndex(endTime - startTime);

    if (data.ok) {
      setResultsWithoutIndex(data.result);
      toast.success("Query executed without index successfully!", {
        description: `Returned ${Array.isArray(data.result) ? data.result.length : 0} rows in ${(endTime - startTime).toFixed(2)}ms`,
      });
    } else {
      toast.error("Error executing query without index", { description: data.error });
    }
  } catch (err: any) {
    toast.error("Connection error", { description: err.message });
  } finally {
    setLoading(false);
  }
};


  const handleLoadExample = (example: string) => {
    setQuery(example)
    toast.info("Example query loaded")
  }

  // Ejecutar ambas variantes y persistir en localStorage para otras vistas
  const handleExecuteBoth = async () => {
    setLoading(true)
    try {
      // Ejecutar SIN índice primero (backend mide tiempo)
      const resNoIdx = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, use_index: false }),
      })
      const dataNoIdx = await resNoIdx.json()
      if (!dataNoIdx.ok) throw new Error(dataNoIdx.error || "Query without index failed")

      // Ejecutar CON índice
      const resIdx = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, use_index: true }),
      })
      const dataIdx = await resIdx.json()
      if (!dataIdx.ok) throw new Error(dataIdx.error || "Query with index failed")

      const timeWithout = Number(dataNoIdx.execution_time) * 1000
      const timeWith = Number(dataIdx.execution_time) * 1000

      setExecutionTimeWithoutIndex(timeWithout)
      setExecutionTimeWithIndex(timeWith)
      setResultsWithoutIndex(Array.isArray(dataNoIdx.result) ? dataNoIdx.result : [])
      setResultsWithIndex(Array.isArray(dataIdx.result) ? dataIdx.result : [])
      
      // Debug: mostrar resultados en consola
      console.log("Results without index:", dataNoIdx.result)
      console.log("Results with index:", dataIdx.result)
      console.log("Used index:", dataIdx.used_index)
      console.log("Index warning:", dataIdx.index_warning)
      
      // Mostrar advertencias si existen
      if (dataIdx.index_warning) {
        toast.warning("Index Warning", { description: dataIdx.index_warning })
      }

      // Persistir en localStorage
      const last = {
        query,
        timeWithIndexMs: Number(timeWith.toFixed(2)),
        timeWithoutIndexMs: Number(timeWithout.toFixed(2)),
        usedIndexOnSecond: Boolean(dataIdx.used_index),
        timestamp: Date.now(),
      }
      localStorage.setItem("db_performance_last", JSON.stringify(last))

      // Historial acumulado
      const key = "db_performance_history"
      const prevRaw = localStorage.getItem(key)
      const prev = prevRaw ? JSON.parse(prevRaw) : []
      prev.push(last)
      localStorage.setItem(key, JSON.stringify(prev.slice(-20))) // mantener últimos 20

      const labelUsed = last.usedIndexOnSecond ? "index" : "no-index"
      const resultCount = Array.isArray(dataIdx.result) ? dataIdx.result.length : 0
      toast.success("Executed both variants", { description: `with(${labelUsed}): ${last.timeWithIndexMs}ms, without: ${last.timeWithoutIndexMs}ms, results: ${resultCount}` })
    } catch (err: any) {
      toast.error("Execution failed", { description: err.message })
    } finally {
      setLoading(false)
    }
  }

  // Restaurar último query ejecutado
  useEffect(() => {
    try {
      const raw = localStorage.getItem("db_performance_last_query")
      if (raw) setQuery(raw)
    } catch {}
  }, [])
  
  // Guardar query en localStorage cada vez que cambie
  useEffect(() => {
    if (query.trim()) {
      try { 
        localStorage.setItem("db_performance_last_query", query) 
      } catch {}
    }
  }, [query])

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="animate-fade-in">
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-foreground/70 bg-clip-text text-transparent">
          SQL Query Editor
        </h1>
        <p className="text-muted-foreground mt-2">Execute SQL-like queries on your database</p>
      </div>

      {/* Query Editor */}
      <Card className="glass-card border-white/10 animate-scale-in hover:shadow-xl hover:shadow-primary/10 transition-all duration-300">
        <CardHeader>
          <CardTitle>Query Editor</CardTitle>
          <CardDescription>Write and execute your SQL queries</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter your SQL query..."
            className="font-mono min-h-[200px] bg-black/40 border-white/10 focus:border-primary/50 focus:shadow-lg focus:shadow-primary/20 transition-all duration-300"
          />
          <div className="flex items-center justify-between">
            <div className="flex gap-2">
              <Button
                onClick={handleExecuteBoth}
                disabled={loading}
                className="gap-2 hover:scale-105 hover:shadow-lg hover:shadow-primary/30 transition-all duration-300 bg-gradient-to-r from-primary to-primary/90"
              >
                <Play className="h-4 w-4" />
                {loading ? "Running..." : "Execute (With & Without Index)"}
              </Button>
            </div>
            {(executionTimeWithIndex || executionTimeWithoutIndex) && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground animate-fade-in">
                <Clock className="h-4 w-4" />
                <span className="font-mono text-secondary font-semibold">
                  {executionTimeWithIndex && `With Index: ${executionTimeWithIndex.toFixed(2)}ms`}
                  {executionTimeWithoutIndex && ` | Without Index: ${executionTimeWithoutIndex.toFixed(2)}ms`}
                </span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Query Examples */}
      <Card className="glass-card border-white/10 animate-fade-in hover:shadow-xl hover:shadow-primary/5 transition-all duration-300">
        <CardHeader>
          <CardTitle>Example Queries</CardTitle>
          <CardDescription>Click to load a sample query</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {queryExamples.map((example, index) => (
              <button
                key={index}
                onClick={() => handleLoadExample(example)}
                className={cn(
                  "w-full text-left rounded-lg border border-white/10 bg-white/5 p-3 font-mono text-sm hover:bg-white/10 hover:border-primary/50 hover:scale-[1.02] hover:shadow-lg hover:shadow-primary/20 transition-all duration-300 animate-fade-in",
                  `stagger-${index + 1}`,
                )}
              >
                {example}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {(resultsWithIndex && Array.isArray(resultsWithIndex) && resultsWithIndex.length > 0) || 
       (resultsWithoutIndex && Array.isArray(resultsWithoutIndex) && resultsWithoutIndex.length > 0) ? (
        <Card className="glass-card border-white/10 animate-scale-in hover:shadow-xl hover:shadow-primary/5 transition-all duration-300">
          <CardHeader>
            <CardTitle>Query Results</CardTitle>
            <CardDescription>
              {resultsWithIndex?.length || resultsWithoutIndex?.length || 0} rows returned
              {resultsWithIndex?.length === resultsWithoutIndex?.length && (resultsWithIndex?.length || 0) > 0 && 
                " (same results for both executions)"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  {Object.keys((resultsWithIndex && resultsWithIndex[0]) || (resultsWithoutIndex && resultsWithoutIndex[0]) || {}).map((col, i) => (
                    <TableHead key={i}>{col}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {(resultsWithIndex || resultsWithoutIndex || []).map((row, idx) => (
                  <TableRow key={idx}>
                    {Object.values(row).map((val, i) => (
                      <TableCell key={i}>{String(val)}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : null}
    </div>
  )
}
