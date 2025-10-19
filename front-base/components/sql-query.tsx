"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Play, Download, Clock } from "lucide-react"
import { toast } from "sonner"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Bar } from 'react-chartjs-2';
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
  const [executedWith, setExecutedWith] = useState<boolean | null>(null)
  const [executedWithout, setExecutedWithout] = useState<boolean | null>(null)
  const [usedIndexTypeWith, setUsedIndexTypeWith] = useState<string | null>(null)
  const [usedIndexTypeWithout, setUsedIndexTypeWithout] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [compareTable, setCompareTable] = useState("")
  const [compareColumn, setCompareColumn] = useState("")
  const [compareResults, setCompareResults] = useState<any[] | null>(null)
  const [indexHint, setIndexHint] = useState<string>("auto")
  const [availableIndexOptions, setAvailableIndexOptions] = useState<string[]>([])
  const [availableIndexMeta, setAvailableIndexMeta] = useState<Record<string, any>>({})

  ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

// Frontend: Cambio de las rutas a una sola consulta
const handleExecuteQueryWithIndex = async () => {
  const startTime = performance.now();
  setLoading(true);

    try {
    const res = await fetch("http://localhost:8000/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, use_index: true, index_hint: indexHint === 'auto' ? null : (indexHint === 'none' ? null : indexHint) }),
    });

    const data = await res.json();
    const endTime = performance.now();
    setExecutionTimeWithIndex(endTime - startTime);

    if (data.ok) {
      console.debug("[SQLQuery] Response with index:", data)
      setResultsWithIndex(data.result);
      setUsedIndexTypeWith(data.used_index_type ? String(data.used_index_type) : null)
      // server may communicate executed/dry_run; if absent, assume executed on success
      setExecutedWith(typeof data.executed === 'boolean' ? data.executed : true)
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
      body: JSON.stringify({ query, use_index: false, index_hint: indexHint === 'auto' ? null : (indexHint === 'none' ? null : indexHint) }),
    });

    const data = await res.json();
    const endTime = performance.now();
    setExecutionTimeWithoutIndex(endTime - startTime);

    if (data.ok) {
      console.debug("[SQLQuery] Response without index:", data)
      setResultsWithoutIndex(data.result);
      setUsedIndexTypeWithout(data.used_index_type ? String(data.used_index_type) : null)
      setExecutedWithout(typeof data.executed === 'boolean' ? data.executed : true)
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
      // Decide operation type: only run both variants for read queries
      const op = (query || "").trim().split(/\s+/)[0].toLowerCase()
      const lower = (query || "").toLowerCase()
      const isRead = op === "select" || op === "search" || lower.includes(" between ") || lower.includes(" range ")

      if (isRead) {
        // Ejecutar SIN índice primero
        const resNoIdx = await fetch("http://localhost:8000/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, use_index: false, index_hint: indexHint === 'auto' ? null : (indexHint === 'none' ? null : indexHint) }),
        })
        const dataNoIdx = await resNoIdx.json()
        if (!dataNoIdx.ok) throw new Error(dataNoIdx.error || "Query without index failed")

        // Ejecutar CON índice
        const resIdx = await fetch("http://localhost:8000/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, use_index: true, index_hint: indexHint === 'auto' ? null : (indexHint === 'none' ? null : indexHint) }),
        })
        const dataIdx = await resIdx.json()
        if (!dataIdx.ok) throw new Error(dataIdx.error || "Query with index failed")

  // Use server-side executed/dry_run flags to decide which timings to display.
  const timeWithout = Number(dataNoIdx.execution_time) * 1000
  const timeWith = Number(dataIdx.execution_time) * 1000

  const execNo = typeof dataNoIdx.executed === 'boolean' ? dataNoIdx.executed : true
  const execYes = typeof dataIdx.executed === 'boolean' ? dataIdx.executed : true

  setExecutedWithout(execNo)
  setExecutedWith(execYes)

  // Only set times for requests that were actually executed (exec flag true). This
  // avoids showing a "fake" time from a dry-run or a non-applicable run.
  setExecutionTimeWithoutIndex(execNo ? timeWithout : null)
  setExecutionTimeWithIndex(execYes ? timeWith : null)
        setResultsWithoutIndex(Array.isArray(dataNoIdx.result) ? dataNoIdx.result : [])
        setResultsWithIndex(Array.isArray(dataIdx.result) ? dataIdx.result : [])

        // Debug
        console.log("Results without index:", dataNoIdx.result)
        console.log("Results with index:", dataIdx.result)

        if (dataIdx.index_warning) {
          toast.warning("Index Warning", { description: dataIdx.index_warning })
        }

        // Persistir métricas
        const last = {
          query,
          timeWithIndexMs: Number(timeWith.toFixed(2)),
          timeWithoutIndexMs: Number(timeWithout.toFixed(2)),
          usedIndexOnSecond: Boolean(dataIdx.used_index),
          usedIndexType: dataIdx.used_index_type || null,
          timestamp: Date.now(),
        }
        localStorage.setItem("db_performance_last", JSON.stringify(last))
        const key = "db_performance_history"
        const prevRaw = localStorage.getItem(key)
        const prev = prevRaw ? JSON.parse(prevRaw) : []
        prev.push(last)
        localStorage.setItem(key, JSON.stringify(prev.slice(-20)))

        const labelUsed = last.usedIndexOnSecond ? "index" : "no-index"
        const resultCount = Array.isArray(dataIdx.result) ? dataIdx.result.length : 0
        toast.success("Executed both variants", { description: `with(${labelUsed}): ${last.timeWithIndexMs}ms, without: ${last.timeWithoutIndexMs}ms, results: ${resultCount}` })
      } else {
        // Not a read operation: execute only once (no comparison)
        const res = await fetch("http://localhost:8000/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, use_index: false, index_hint: indexHint === 'auto' ? null : (indexHint === 'none' ? null : indexHint) }),
        })
        const data = await res.json()
        if (!data.ok) throw new Error(data.error || "Query failed")

  const timeMs = Number(data.execution_time || 0) * 1000
  setExecutionTimeWithoutIndex(timeMs)
  setExecutedWithout(true)
        setResultsWithoutIndex(Array.isArray(data.result) ? data.result : [])
        // show feedback
        toast.success("Operation executed", { description: data.message || `Affected: ${Array.isArray(data.result) ? data.result.length : 0}` })
      }
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

  // Load available indexes from backend to populate dropdown
  useEffect(() => {
    const loadIndexes = async () => {
      try {
        const res = await fetch("http://localhost:8000/tables_with_indexes")
        const data = await res.json()
        if (data.ok) {
          const opts: string[] = ["auto", "none"]
          const meta: Record<string, any> = {}
          data.tables.forEach((t: any) => {
            t.indexes.forEach((ix: any) => {
              const key = `${t.table}.${ix.column}`
              opts.push(key)
              meta[key] = ix
            })
          })
          setAvailableIndexOptions(opts)
          setAvailableIndexMeta(meta)
        }
      } catch (e) {
        console.warn("loadIndexes failed", e)
      }
    }
    loadIndexes()
  }, [])

  // Render
  return (
    <div className="space-y-4">

      {/* SQL Input Card */}
      <Card className="glass-card border-white/10 animate-fade-in hover:shadow-xl hover:shadow-primary/5 transition-all duration-300">
        <CardHeader>
          <CardTitle>SQL</CardTitle>
          <CardDescription>Write a SQL query to run against the local DB</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <Textarea value={query} onChange={(e: any) => setQuery(e.target.value)} className="min-h-[120px] text-sm" />

            <div className="flex items-center gap-3">
              <select value={indexHint} onChange={(e) => setIndexHint(e.target.value)} className="bg-black/30 text-sm rounded p-2 border border-white/10">
                {availableIndexOptions.map((o) => (
                  <option key={o} value={o}>{o === 'auto' ? 'Auto (choose best)' : (o === 'none' ? 'None (force no index)' : o)}</option>
                ))}
              </select>

              <div className="flex gap-2 ml-auto">
                <Button onClick={async () => {
                  // If user selected 'auto', run both; otherwise run single request following hint
                  if (indexHint === 'auto') return handleExecuteBoth()
                  if (indexHint === 'none') return handleExecuteQueryWithoutIndex()
                  return handleExecuteQueryWithIndex()
                }} disabled={loading} className="gap-2">
                  <Play className="h-4 w-4" />
                  {loading ? "Running..." : "Execute"}
                </Button>

                <Button onClick={handleExecuteBoth} disabled={loading} className="gap-2">
                  <Play className="h-4 w-4" />
                  Execute (With & Without Index)
                </Button>
              </div>
            </div>

            {/* Timing display: show real executed times with a green clock */}
            {(executionTimeWithIndex || executionTimeWithoutIndex) && (
              <div className="flex items-center gap-2 text-sm text-emerald-400 mt-3 animate-fade-in">
                <Clock className="h-4 w-4 text-emerald-400" />
                <span className="font-mono font-semibold">
                  {executionTimeWithIndex && executedWith ? `With Index: ${executionTimeWithIndex.toFixed(2)}ms` : null}
                  {executionTimeWithIndex && executedWith && executionTimeWithoutIndex && executedWithout ? ` | ` : null}
                  {executionTimeWithoutIndex && executedWithout ? `Without Index: ${executionTimeWithoutIndex.toFixed(2)}ms` : null}
                  {!executedWith && !executedWithout && (executionTimeWithIndex || executionTimeWithoutIndex) ?
                    (executionTimeWithIndex ? `With Index: ${executionTimeWithIndex.toFixed(2)}ms` : `Without Index: ${executionTimeWithoutIndex?.toFixed(2)}ms`) : null}
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
        <>
    <Card className="glass-card border-white/10 animate-scale-in hover:shadow-xl hover:shadow-primary/5 transition-all duration-300">
          <CardHeader>
            <CardTitle>Query Results</CardTitle>
            <CardDescription>
              {resultsWithIndex?.length || resultsWithoutIndex?.length || 0} rows returned
              {resultsWithIndex?.length === resultsWithoutIndex?.length && (resultsWithIndex?.length || 0) > 0 && 
                " (same results for both executions)"}
              {usedIndexTypeWith && (
                <div className="text-sm text-muted-foreground mt-1">Índice usado: {usedIndexTypeWith}</div>
              )}
              {usedIndexTypeWithout && (
                <div className="text-sm text-muted-foreground mt-1">Índice (sin): {usedIndexTypeWithout}</div>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  {(() => {
                    const sample = (resultsWithIndex && resultsWithIndex[0]) || (resultsWithoutIndex && resultsWithoutIndex[0]) || null
                    if (!sample) return []
                    if (typeof sample === 'object' && !Array.isArray(sample)) return Object.keys(sample)
                    // fallback: if sample is primitive or array, create a single 'value' column
                    if (Array.isArray(sample)) return sample.map((_, i) => `col_${i}`)
                    return ['value']
                  })().map((col, i) => (
                    <TableHead key={i}>{col}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {((resultsWithIndex && resultsWithIndex.length > 0) ? resultsWithIndex : resultsWithoutIndex || []).map((row, idx) => (
                  <TableRow key={idx}>
                    {(() => {
                      if (row == null) return [<TableCell key={0}>{String(row)}</TableCell>]
                      if (typeof row === 'object' && !Array.isArray(row)) return Object.values(row).map((val, i) => <TableCell key={i}>{String(val)}</TableCell>)
                      if (Array.isArray(row)) return row.map((val, i) => <TableCell key={i}>{String(val)}</TableCell>)
                      return [<TableCell key={0}>{String(row)}</TableCell>]
                    })()}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

      {/* Comparison UI removed */}
  </>
  ) : null}
    </div>
  )
}
