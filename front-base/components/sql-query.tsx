"use client"

import { useState } from "react"
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
  const [results, setResults] = useState<any[] | null>(null)
  const [executionTime, setExecutionTime] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)

  const handleExecuteQuery = async () => {
    const startTime = performance.now()
    setLoading(true)

    try {
      const res = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      })

      const data = await res.json()
      const endTime = performance.now()
      setExecutionTime(endTime - startTime)

      if (data.ok) {
        setResults(data.result)
        toast.success("Query executed successfully!", {
          description: `Returned ${Array.isArray(data.result) ? data.result.length : 0} rows in ${(endTime - startTime).toFixed(2)}ms`,
        })
      } else {
        toast.error("Error executing query", { description: data.error })
      }
    } catch (err: any) {
      toast.error("Connection error", { description: err.message })
    } finally {
      setLoading(false)
    }
  }

  const handleLoadExample = (example: string) => {
    setQuery(example)
    toast.info("Example query loaded")
  }

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
                onClick={handleExecuteQuery}
                disabled={loading}
                className="gap-2 hover:scale-105 hover:shadow-lg hover:shadow-primary/30 transition-all duration-300 bg-gradient-to-r from-primary to-primary/90"
              >
                <Play className="h-4 w-4" />
                {loading ? "Running..." : "Execute Query"}
              </Button>
              <Button
                variant="outline"
                onClick={() => setResults(null)}
                className="hover:scale-105 transition-transform duration-300 bg-transparent"
              >
                Clear
              </Button>
            </div>
            {executionTime && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground animate-fade-in">
                <Clock className="h-4 w-4" />
                <span className="font-mono text-secondary font-semibold">{executionTime.toFixed(2)}ms</span>
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
      {results && Array.isArray(results) && results.length > 0 && (
        <Card className="glass-card border-white/10 animate-scale-in hover:shadow-xl hover:shadow-primary/5 transition-all duration-300">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Query Results</CardTitle>
                <CardDescription>{results.length} rows returned</CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="gap-2 bg-transparent hover:scale-105 transition-transform duration-300"
              >
                <Download className="h-4 w-4" />
                Export CSV
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border border-white/10 overflow-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-white/10 hover:bg-white/5">
                    {Object.keys(results[0]).map((col, i) => (
                      <TableHead key={i}>{col}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map((row, idx) => (
                    <TableRow key={idx} className="border-white/10 hover:bg-white/10 transition-all">
                      {Object.values(row).map((val, i) => (
                        <TableCell key={i} className="font-mono text-sm">
                          {String(val)}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
