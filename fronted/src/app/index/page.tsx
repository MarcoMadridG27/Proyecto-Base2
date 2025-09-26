"use client";
import React, { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/app/components/ui/card";
import { Button } from "@/app/components/ui/button";
import { Badge } from "@/app/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/app/components/ui/tabs";
import { Progress } from "@/app/components/ui/progress";

import { TreePine, Hash, Database, BarChart3, Search, ChevronDown, ChevronRight, Circle } from "lucide-react";
import { toast } from "sonner";


type IndexType = 'sequential' | 'isam' | 'hash' | 'btree' | 'rtree';

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
  const [selectedIndex, setSelectedIndex] = useState<IndexType>('btree');
  const [isLoading, setIsLoading] = useState(false);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set(['root']));

  const indexes: Record<IndexType, IndexInfo> = {
    sequential: {
      type: 'sequential',
      name: 'Sequential File',
      description: 'Acceso secuencial ordenado por clave primaria',
      icon: BarChart3,
      complexity: 'O(n)',
      bestFor: ['Consultas de rango', 'Acceso secuencial', 'Archivos pequeños'],
      color: 'from-blue-500 to-blue-600'
    },
    isam: {
      type: 'isam',
      name: 'ISAM (Indexed Sequential)',
      description: 'Combina índice con acceso secuencial',
      icon: Database,
      complexity: 'O(log n)',
      bestFor: ['Lecturas frecuentes', 'Archivos estáticos', 'Consultas de rango'],
      color: 'from-emerald-500 to-emerald-600'
    },
    hash: {
      type: 'hash',
      name: 'Hash Index',
      description: 'Acceso directo mediante función hash',
      icon: Hash,
      complexity: 'O(1)',
      bestFor: ['Búsquedas exactas', 'Acceso rápido', 'Claves únicas'],
      color: 'from-purple-500 to-purple-600'
    },
    btree: {
      type: 'btree',
      name: 'B+ Tree',
      description: 'Árbol balanceado para acceso eficiente',
      icon: TreePine,
      complexity: 'O(log n)',
      bestFor: ['Consultas de rango', 'Ordenamiento', 'Bases de datos'],
      color: 'from-orange-500 to-orange-600'
    },
    rtree: {
      type: 'rtree',
      name: 'R-Tree',
      description: 'Índice espacial para datos geográficos',
      icon: Search,
      complexity: 'O(log n)',
      bestFor: ['Consultas espaciales', 'Datos geográficos', 'Geometrías'],
      color: 'from-red-500 to-red-600'
    }
  };

  const sampleData = {
    sequential: [
      { key: '001', value: 'Ana García' },
      { key: '002', value: 'Carlos López' },
      { key: '003', value: 'Elena Ruiz' },
      { key: '004', value: 'Juan Pérez' },
      { key: '005', value: 'María Silva' }
    ],
    hash: [
      { bucket: '0', values: ['López (hash: 240)'] },
      { bucket: '1', values: ['Silva (hash: 241)', 'García (hash: 241)'] },
      { bucket: '2', values: ['Pérez (hash: 242)'] },
      { bucket: '3', values: ['Ruiz (hash: 243)'] },
      { bucket: '4', values: [] }
    ],
    btree: {
      id: 'root',
      value: '[15, 30]',
      children: [
        {
          id: 'left',
          value: '[5, 10]',
          children: [
            { id: 'left-left', value: '[1, 3]' },
            { id: 'left-right', value: '[12, 14]' }
          ]
        },
        {
          id: 'middle',
          value: '[20, 25]',
          children: [
            { id: 'middle-left', value: '[17, 18]' },
            { id: 'middle-right', value: '[27, 28]' }
          ]
        },
        {
          id: 'right',
          value: '[35, 40]',
          children: [
            { id: 'right-left', value: '[32, 33]' },
            { id: 'right-right', value: '[42, 45]' }
          ]
        }
      ]
    }
  };

  const generateIndex = async () => {
    setIsLoading(true);
    
    // Simulate index generation
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    setIsLoading(false);
    toast.success(`Índice ${indexes[selectedIndex].name} generado exitosamente`);
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
            {node.children!.map(child => renderTreeNode(child, level + 1))}
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
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Explorador de Índices</h2>
          <p className="text-gray-600 dark:text-gray-400">
            Visualiza y compara diferentes estructuras de indexación
          </p>
        </div>
        <Button onClick={generateIndex} disabled={isLoading}>
          {isLoading ? 'Generando...' : 'Generar Índice'}
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Index Selection */}
        <div className="space-y-4">
          <Card className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border-0 shadow-lg">
            <CardHeader>
              <CardTitle className="text-lg">Tipos de Índice</CardTitle>
              <CardDescription>Selecciona una estructura para explorar</CardDescription>
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
                        : 'text-left'
                    }`}
                    onClick={() => setSelectedIndex(index.type)}
                  >
                    <div className="flex items-start gap-3">
                      <IndexIcon className="w-5 h-5 mt-0.5 flex-shrink-0" />
                      <div>
                        <div className="font-medium">{index.name}</div>
                        <div className={`text-sm ${isSelected ? 'text-white/80' : 'text-gray-500'}`}>
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
                    <li key={index} className="text-sm text-gray-600 dark:text-gray-400 flex items-center gap-2">
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
                Estructura de datos y organización
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
              ) : (
                <Tabs defaultValue="structure" className="w-full">
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="structure">Estructura</TabsTrigger>
                    <TabsTrigger value="performance">Performance</TabsTrigger>
                    <TabsTrigger value="operations">Operaciones</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="structure" className="mt-6">
                    {selectedIndex === 'sequential' && (
                      <div className="space-y-4">
                        <h4 className="font-medium">Archivo Secuencial Ordenado</h4>
                        <div className="grid grid-cols-1 gap-2">
                          {sampleData.sequential.map((item, index) => (
                            <div key={index} className="flex items-center gap-4 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                              <Badge variant="outline">{item.key}</Badge>
                              <span className="text-sm">{item.value}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {selectedIndex === 'hash' && (
                      <div className="space-y-4">
                        <h4 className="font-medium">Tabla Hash</h4>
                        <div className="grid grid-cols-1 gap-2">
                          {sampleData.hash.map((bucket, index) => (
                            <div key={index} className="flex items-center gap-4 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                              <Badge variant="outline" className="min-w-[60px]">
                                Bucket {bucket.bucket}
                              </Badge>
                              <div className="flex-1">
                                {bucket.values.length > 0 ? (
                                  bucket.values.map((value, i) => (
                                    <span key={i} className="text-sm mr-2">
                                      {value}
                                    </span>
                                  ))
                                ) : (
                                  <span className="text-sm text-gray-400">Vacío</span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {selectedIndex === 'btree' && (
                      <div className="space-y-4">
                        <h4 className="font-medium">Estructura B+ Tree</h4>
                        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                          {renderTreeNode(sampleData.btree)}
                        </div>
                      </div>
                    )}
                    
                    {(selectedIndex === 'isam' || selectedIndex === 'rtree') && (
                      <div className="text-center py-12">
                        <Icon className="w-16 h-16 mx-auto text-gray-400 mb-4" />
                        <p className="text-gray-500">
                          Visualización de {currentIndex.name} en desarrollo
                        </p>
                      </div>
                    )}
                  </TabsContent>
                  
                  <TabsContent value="performance" className="mt-6">
                    <div className="space-y-6">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <Card className="p-4">
                          <h5 className="font-medium mb-2">Búsqueda</h5>
                          <div className="text-2xl font-bold text-emerald-600">
                            {currentIndex.complexity}
                          </div>
                        </Card>
                        <Card className="p-4">
                          <h5 className="font-medium mb-2">Inserción</h5>
                          <div className="text-2xl font-bold text-blue-600">
                            {selectedIndex === 'hash' ? 'O(1)' : 'O(log n)'}
                          </div>
                        </Card>
                        <Card className="p-4">
                          <h5 className="font-medium mb-2">Eliminación</h5>
                          <div className="text-2xl font-bold text-red-600">
                            {selectedIndex === 'hash' ? 'O(1)' : 'O(log n)'}
                          </div>
                        </Card>
                      </div>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="operations" className="mt-6">
                    <div className="space-y-4">
                      <h4 className="font-medium">Operaciones Soportadas</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Badge className="bg-emerald-100 text-emerald-800">✓ Búsqueda por clave</Badge>
                          <Badge className="bg-emerald-100 text-emerald-800">✓ Inserción</Badge>
                          <Badge className="bg-emerald-100 text-emerald-800">✓ Eliminación</Badge>
                        </div>
                        <div className="space-y-2">
                          {selectedIndex !== 'hash' && (
                            <Badge className="bg-emerald-100 text-emerald-800">✓ Consultas de rango</Badge>
                          )}
                          {selectedIndex === 'rtree' && (
                            <Badge className="bg-emerald-100 text-emerald-800">✓ Consultas espaciales</Badge>
                          )}
                          <Badge className="bg-blue-100 text-blue-800">ℹ Recorrido ordenado</Badge>
                        </div>
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}