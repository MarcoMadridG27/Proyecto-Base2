"use client";
import React, { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/app/components/ui/card";
import { Button } from "@/app/components/ui/button";
import { Textarea } from "@/app/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/app/components/ui/table";
import { Badge } from "@/app/components/ui/badge";
import { Alert, AlertDescription } from "@/app/components/ui/alert";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/app/components/ui/select";

import {
  Play,
  History,
  Save,
  Download,
  Database,
  Clock,
  CheckCircle,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";

interface QueryResult {
  headers: string[];
  rows: string[][];
  executionTime: number;
  rowCount: number;
}

interface QueryHistory {
  id: string;
  query: string;
  timestamp: Date;
  executionTime: number;
  status: "success" | "error";
}

export default function Page() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [queryHistory, setQueryHistory] = useState<QueryHistory[]>([]);
  const [selectedTable, setSelectedTable] = useState<string>("");

  const sampleQueries = [
    "SELECT * FROM usuarios WHERE edad > 25",
    "SELECT ciudad, COUNT(*) as total FROM usuarios GROUP BY ciudad",
    "SELECT * FROM usuarios WHERE latitud BETWEEN -15 AND -10",
    "SELECT nombre, edad FROM usuarios ORDER BY edad DESC LIMIT 5",
  ];

  const availableTables = ["usuarios", "productos", "ventas", "ubicaciones"];

  const executeQuery = async () => {
    if (!query.trim()) {
      toast.error("Por favor ingresa una consulta");
      return;
    }

    setIsExecuting(true);
    setError(null);
    const startTime = Date.now();

    try {
      const res = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      const data = await res.json();

      if (res.ok && data.ok) {
        const queryResult: QueryResult = {
          headers: data.result.headers || [],
          rows: data.result.rows || [],
          executionTime: Date.now() - startTime,
          rowCount: data.result.rows ? data.result.rows.length : 0,
        };

        setResult(queryResult);

        // Historial
        const historyEntry: QueryHistory = {
          id: Date.now().toString(),
          query,
          timestamp: new Date(),
          executionTime: queryResult.executionTime,
          status: "success",
        };
        setQueryHistory((prev) => [historyEntry, ...prev.slice(0, 9)]);

        toast.success(`Consulta ejecutada en ${queryResult.executionTime}ms`);
      } else {
        throw new Error(data.error || "Error al ejecutar la consulta");
      }
    } catch (err: any) {
      const errorEntry: QueryHistory = {
        id: Date.now().toString(),
        query,
        timestamp: new Date(),
        executionTime: Date.now() - startTime,
        status: "error",
      };
      setQueryHistory((prev) => [errorEntry, ...prev.slice(0, 9)]);
      setError(err.message || "Error desconocido");
      toast.error("Error al ejecutar la consulta");
    } finally {
      setIsExecuting(false);
    }
  };

  const loadSampleQuery = (sampleQuery: string) => {
    setQuery(sampleQuery);
    toast.success("Consulta de ejemplo cargada");
  };

  const loadFromHistory = (historyQuery: string) => {
    setQuery(historyQuery);
    toast.success("Consulta cargada desde el historial");
  };

  const saveQuery = () => {
    if (!query.trim()) {
      toast.error("No hay consulta para guardar");
      return;
    }

    localStorage.setItem("saved_query", query);
    toast.success("Consulta guardada exitosamente");
  };

  const exportResults = () => {
    if (!result) {
      toast.error("No hay resultados para exportar");
      return;
    }

    const csvContent = [
      result.headers.join(","),
      ...result.rows.map((row) => row.join(",")),
    ].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "query_results.csv";
    a.click();
    window.URL.revokeObjectURL(url);
    toast.success("Resultados exportados");
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Consultas SQL-like
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Ejecuta consultas personalizadas sobre tus datos
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={saveQuery}>
            <Save className="w-4 h-4 mr-2" />
            Guardar
          </Button>
          {result && (
            <Button variant="outline" onClick={exportResults}>
              <Download className="w-4 h-4 mr-2" />
              Exportar
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Query Editor */}
        <div className="lg:col-span-2 space-y-4">
          <Card className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border-0 shadow-lg">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Database className="w-5 h-5" />
                    Editor de Consultas
                  </CardTitle>
                  <CardDescription>
                    Escribe tu consulta SQL en el área de texto
                  </CardDescription>
                </div>
                <Select value={selectedTable} onValueChange={setSelectedTable}>
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Tabla" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableTables.map((table) => (
                      <SelectItem key={table} value={table}>
                        {table}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <Textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="SELECT * FROM usuarios WHERE..."
                className="min-h-[200px] font-mono text-sm"
                disabled={isExecuting}
              />

              <div className="flex items-center gap-2">
                <Button
                  onClick={executeQuery}
                  disabled={isExecuting || !query.trim()}
                  className="bg-gradient-to-r from-blue-500 to-emerald-500 hover:from-blue-600 hover:to-emerald-600"
                >
                  <Play className="w-4 h-4 mr-2" />
                  {isExecuting ? "Ejecutando..." : "Ejecutar Consulta"}
                </Button>

                <Badge variant="secondary" className="ml-auto">
                  {query.length} caracteres
                </Badge>
              </div>

              {error && (
                <Alert className="bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
                  <AlertTriangle className="h-4 w-4 text-red-600" />
                  <AlertDescription className="text-red-800 dark:text-red-200">
                    {error}
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* Query Results */}
          {result && (
            <Card className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border-0 shadow-lg">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle className="w-5 h-5 text-emerald-600" />
                    Resultados
                  </CardTitle>
                  <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                    <span>{result.rowCount} filas</span>
                    <span>{result.executionTime}ms</span>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {result.headers.map((header, index) => (
                          <TableHead key={index} className="min-w-[120px]">
                            {header}
                          </TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {result.rows.map((row, rowIndex) => (
                        <TableRow key={rowIndex}>
                          {row.map((cell, cellIndex) => (
                            <TableCell key={cellIndex} className="text-sm">
                              {cell}
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

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Sample Queries */}
          <Card className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border-0 shadow-lg">
            <CardHeader>
              <CardTitle className="text-lg">Consultas de Ejemplo</CardTitle>
              <CardDescription>Haz clic para cargar ejemplos</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {sampleQueries.map((sampleQuery, index) => (
                <Button
                  key={index}
                  variant="ghost"
                  className="w-full justify-start text-left h-auto p-3 text-sm"
                  onClick={() => loadSampleQuery(sampleQuery)}
                >
                  <Database className="w-4 h-4 mr-2 flex-shrink-0" />
                  <span className="truncate">{sampleQuery}</span>
                </Button>
              ))}
            </CardContent>
          </Card>

          {/* Query History */}
          <Card className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border-0 shadow-lg">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <History className="w-5 h-5" />
                Historial
              </CardTitle>
              <CardDescription>Consultas recientes</CardDescription>
            </CardHeader>
            <CardContent>
              {queryHistory.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-4">
                  No hay consultas en el historial
                </p>
              ) : (
                <div className="space-y-3">
                  {queryHistory.map((item) => (
                    <div
                      key={item.id}
                      className="p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                      onClick={() => loadFromHistory(item.query)}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        {item.status === "success" ? (
                          <CheckCircle className="w-4 h-4 text-emerald-500" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-red-500" />
                        )}
                        <Clock className="w-3 h-3 text-gray-400" />
                        <span className="text-xs text-gray-500">
                          {item.timestamp.toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-sm truncate">{item.query}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {item.executionTime}ms
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
