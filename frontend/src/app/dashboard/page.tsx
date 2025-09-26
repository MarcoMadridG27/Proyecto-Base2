"use client";
import React, { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import {
  Database,
  Upload,
  Search,
  TreePine,
  Map,
  BarChart3,
  FileText,
  Zap,
} from "lucide-react";

export default function Page() {
  const [sql, setSql] = useState("");
  const [result, setResult] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  async function runQuery() {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: sql }),
      });
      const data = await res.json();
      if (data.ok && Array.isArray(data.result)) {
        setResult(data.result);
      } else {
        setResult([{ error: data.error || "Formato inesperado" }]);
      }
    } catch (err) {
      console.error(err);
      setResult([{ error: "Error al conectar con backend" }]);
    } finally {
      setLoading(false);
    }
  }

  const features = [
    {
      icon: Upload,
      title: "Carga de Archivos",
      description: "Sube archivos CSV y visualiza datos tabulares en tiempo real",
      color: "from-blue-500 to-blue-600",
    },
    {
      icon: Search,
      title: "Consultas SQL-like",
      description: "Ejecuta consultas personalizadas sobre tus datos",
      color: "from-emerald-500 to-emerald-600",
    },
    {
      icon: TreePine,
      title: "Explorador de Índices",
      description: "Visualiza estructuras Sequential, ISAM, Hash, B+Tree, RTree",
      color: "from-purple-500 to-purple-600",
    },
    {
      icon: Map,
      title: "Resultados Espaciales",
      description: "Explora datos geoespaciales con mapas interactivos",
      color: "from-orange-500 to-orange-600",
    },
  ];

  const stats = [
    { label: "Archivos Procesados", value: "0", icon: FileText },
    { label: "Consultas Ejecutadas", value: "0", icon: BarChart3 },
    { label: "Índices Creados", value: "0", icon: TreePine },
    { label: "Búsquedas Espaciales", value: "0", icon: Map },
  ];

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="text-center py-12">
        <div className="inline-flex items-center gap-3 mb-6">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-emerald-500 rounded-2xl flex items-center justify-center shadow-lg">
            <Database className="w-8 h-8 text-white" />
          </div>
          <div className="text-left">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Sistema de Base de Datos Multimodal
            </h1>
            <p className="text-lg text-gray-600 dark:text-gray-400">
              Proyecto 1 - UTEC
            </p>
          </div>
        </div>

        <p className="text-xl text-gray-600 dark:text-gray-400 max-w-3xl mx-auto leading-relaxed">
          Organización e indexación eficiente de archivos con datos tabulares y
          espaciales. Una solución completa para el manejo de información
          estructurada y geográfica.
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <Card
              key={index}
              className="bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm border-0 shadow-lg"
            >
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {stat.label}
                    </p>
                    <p className="text-3xl font-bold text-gray-900 dark:text-white">
                      {stat.value}
                    </p>
                  </div>
                  <div className="w-12 h-12 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-600 rounded-xl flex items-center justify-center">
                    <Icon className="w-6 h-6 text-gray-600 dark:text-gray-400" />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Features Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {features.map((feature, index) => {
          const Icon = feature.icon;
          return (
            <Card
              key={index}
              className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border-0 shadow-lg hover:shadow-xl transition-all duration-300 group"
            >
              <CardHeader className="pb-4">
                <div className="flex items-center gap-4">
                  <div
                    className={`w-12 h-12 bg-gradient-to-br ${feature.color} rounded-xl flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300`}
                  >
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <CardTitle className="text-xl">{feature.title}</CardTitle>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-base leading-relaxed">
                  {feature.description}
                </CardDescription>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Ejecutor de Queries */}
      <Card className="bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm border-0 shadow-lg">
        <CardHeader>
          <CardTitle>Ejecutor de Consultas SQL</CardTitle>
          <CardDescription>
            Escribe tu query SQL y ejecútala contra el backend
          </CardDescription>
        </CardHeader>
        <CardContent>
          <textarea
            value={sql}
            onChange={(e) => setSql(e.target.value)}
            placeholder="Ejemplo: SELECT * FROM Restaurantes WHERE id = 1 USING btree"
            className="w-full h-32 border rounded-md p-2 mb-4 dark:bg-gray-900 dark:text-white"
          />
          <Button
            onClick={runQuery}
            className="bg-blue-600 hover:bg-blue-700 text-white"
            disabled={loading}
          >
            {loading ? "Ejecutando..." : "Ejecutar"}
          </Button>

          {result.length > 0 && (
            <div className="mt-6 overflow-x-auto">
              <table className="w-full border-collapse border border-gray-300 dark:border-gray-600">
                <thead className="bg-gray-100 dark:bg-gray-700">
                  <tr>
                    {Object.keys(result[0]).map((key) => (
                      <th
                        key={key}
                        className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-left text-sm font-semibold"
                      >
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.map((row, i) => (
                    <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                      {Object.values(row).map((val, j) => (
                        <td
                          key={j}
                          className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm"
                        >
                          {String(val)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
