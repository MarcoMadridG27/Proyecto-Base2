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
import { Badge } from "@/app/components/ui/badge";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/app/components/ui/tabs";
import { Progress } from "@/app/components/ui/progress";
import {
  TreePine,
  Hash,
  Database,
  BarChart3,
  Search,
  ChevronDown,
  ChevronRight,
  Circle,
} from "lucide-react";
import { toast } from "sonner";

type IndexType = "sequential" | "isam" | "hash" | "btree" | "rtree";

interface IndexInfo {
  type: IndexType;
  name: string;
  description: string;
  icon: React.ElementType;
  complexity: string;
  bestFor: string[];
  color: string;
}

interface TreeNode {
  id: string;
  value: string;
  children?: TreeNode[];
  isExpanded?: boolean;
}

export default function Page() {
  const [selectedIndex, setSelectedIndex] = useState<IndexType>("btree");
  const [isLoading, setIsLoading] = useState(false);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(
    new Set(["root"])
  );
  const [queryResult, setQueryResult] = useState<any>(null);

  const indexes: Record<IndexType, IndexInfo> = {
    sequential: {
      type: "sequential",
      name: "Sequential File",
      description: "Acceso secuencial ordenado por clave primaria",
      icon: BarChart3,
      complexity: "O(n)",
      bestFor: ["Consultas de rango", "Acceso secuencial", "Archivos pequeños"],
      color: "from-blue-500 to-blue-600",
    },
    isam: {
      type: "isam",
      name: "ISAM (Indexed Sequential)",
      description: "Combina índice con acceso secuencial",
      icon: Database,
      complexity: "O(log n)",
      bestFor: ["Lecturas frecuentes", "Archivos estáticos", "Consultas de rango"],
      color: "from-emerald-500 to-emerald-600",
    },
    hash: {
      type: "hash",
      name: "Hash Index",
      description: "Acceso directo mediante función hash",
      icon: Hash,
      complexity: "O(1)",
      bestFor: ["Búsquedas exactas", "Acceso rápido", "Claves únicas"],
      color: "from-purple-500 to-purple-600",
    },
    btree: {
      type: "btree",
      name: "B+ Tree",
      description: "Árbol balanceado para acceso eficiente",
      icon: TreePine,
      complexity: "O(log n)",
      bestFor: ["Consultas de rango", "Ordenamiento", "Bases de datos"],
      color: "from-orange-500 to-orange-600",
    },
    rtree: {
      type: "rtree",
      name: "R-Tree",
      description: "Índice espacial para datos geográficos",
      icon: Search,
      complexity: "O(log n)",
      bestFor: ["Consultas espaciales", "Datos geográficos", "Geometrías"],
      color: "from-red-500 to-red-600",
    },
  };

  const generateIndex = async () => {
    setIsLoading(true);
    try {
      const res = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: `SELECT * FROM Restaurantes USING ${selectedIndex}`,
        }),
      });

      const data = await res.json();
      if (data.ok) {
        toast.success(
          `Índice ${indexes[selectedIndex].name} generado exitosamente`
        );
        setQueryResult(data.result); // guardamos el resultado real del backend
      } else {
        toast.error(`Error: ${data.error}`);
      }
    } catch (err) {
      console.error(err);
      toast.error("Error de conexión con backend");
    } finally {
      setIsLoading(false);
    }
  };

  const toggleNode = (nodeId: string) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(nodeId)) {
      newExpanded.delete(nodeId);
    } else {
      newExpanded.add(nodeId);
    }
    setExpandedNodes(newExpanded);
  };

  const renderTreeNode = (node: TreeNode, level: number = 0) => {
    const hasChildren = node.children && node.children.length > 0;
    const isExpanded = expandedNodes.has(node.id);

    return (
      <div key={node.id} className={`ml-${level * 4}`}>
        <div
          className="flex items-center gap-2 py-2 px-3 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer"
          onClick={() => hasChildren && toggleNode(node.id)}
        >
          {hasChildren ? (
            isExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-500" />
            )
          ) : (
            <Circle className="w-2 h-2 text-gray-400 ml-1" />
          )}
          <span className="font-mono text-sm">{node.value}</span>
        </div>

        {hasChildren && isExpanded && (
          <div className="ml-4">
            {node.children!.map((child) => renderTreeNode(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  const currentIndex = indexes[selectedIndex];
  const Icon = currentIndex.icon;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Explorador de Índices
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Visualiza y compara diferentes estructuras de indexación
          </p>
        </div>
        <Button onClick={generateIndex} disabled={isLoading}>
          {isLoading ? "Generando..." : "Generar Índice"}
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Index Selection */}
        <div className="space-y-4">
          <Card className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border-0 shadow-lg">
            <CardHeader>
              <CardTitle className="text-lg">Tipos de Índice</CardTitle>
              <CardDescription>
                Selecciona una estructura para explorar
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {Object.values(indexes).map((index) => {
                const IndexIcon = index.icon;
                const isSelected = selectedIndex === index.type;

                return (
                  <Button
                    key={index.type}
                    variant={isSelected ? "default" : "ghost"}
                    className={`w-full justify-start h-auto p-4 ${
                      isSelected
                        ? `bg-gradient-to-r ${index.color} text-white`
                        : "text-left"
                    }`}
                    onClick={() => setSelectedIndex(index.type)}
                  >
                    <div className="flex items-start gap-3">
                      <IndexIcon className="w-5 h-5 mt-0.5 flex-shrink-0" />
                      <div>
                        <div className="font-medium">{index.name}</div>
                        <div
                          className={`text-sm ${
                            isSelected ? "text-white/80" : "text-gray-500"
                          }`}
                        >
                          {index.complexity}
                        </div>
                      </div>
                    </div>
                  </Button>
                );
              })}
            </CardContent>
          </Card>

          {/* Index Info */}
          <Card className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border-0 shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Icon className="w-5 h-5" />
                {currentIndex.name}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {currentIndex.description}
              </p>

              <div>
                <Badge variant="secondary" className="mb-2">
                  Complejidad: {currentIndex.complexity}
                </Badge>
              </div>

              <div>
                <h4 className="font-medium mb-2">Ideal para:</h4>
                <ul className="space-y-1">
                  {currentIndex.bestFor.map((use, index) => (
                    <li
                      key={index}
                      className="text-sm text-gray-600 dark:text-gray-400 flex items-center gap-2"
                    >
                      <Circle className="w-2 h-2 text-emerald-500" />
                      {use}
                    </li>
                  ))}
                </ul>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Visualization */}
        <div className="lg:col-span-3">
          <Card className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border-0 shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Icon className="w-5 h-5" />
                Visualización: {currentIndex.name}
              </CardTitle>
              <CardDescription>
                Estructura de datos y organización (resultado real del backend)
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="text-center py-12 space-y-4">
                  <div className="w-16 h-16 mx-auto bg-gradient-to-br from-blue-500 to-emerald-500 rounded-2xl flex items-center justify-center animate-pulse">
                    <Icon className="w-8 h-8 text-white" />
                  </div>
                  <p>Generando índice...</p>
                  <Progress value={65} className="w-full max-w-md mx-auto" />
                </div>
              ) : queryResult ? (
                <pre className="bg-gray-100 dark:bg-gray-900 p-4 rounded-md text-sm overflow-x-auto">
                  {JSON.stringify(queryResult, null, 2)}
                </pre>
              ) : (
                <p className="text-gray-500">Ejecuta una consulta para ver resultados</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
