"use client";
import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Database, Upload, Search, TreePine, Map, BarChart3, FileText, Zap } from 'lucide-react';

export default function Page() {
  const features = [
    {
      icon: Upload,
      title: 'Carga de Archivos',
      description: 'Sube archivos CSV y visualiza datos tabulares en tiempo real',
      color: 'from-blue-500 to-blue-600'
    },
    {
      icon: Search,
      title: 'Consultas SQL-like',
      description: 'Ejecuta consultas personalizadas sobre tus datos',
      color: 'from-emerald-500 to-emerald-600'
    },
    {
      icon: TreePine,
      title: 'Explorador de Índices',
      description: 'Visualiza estructuras Sequential, ISAM, Hash, B+Tree, RTree',
      color: 'from-purple-500 to-purple-600'
    },
    {
      icon: Map,
      title: 'Resultados Espaciales',
      description: 'Explora datos geoespaciales con mapas interactivos',
      color: 'from-orange-500 to-orange-600'
    }
  ];

  const stats = [
    { label: 'Archivos Procesados', value: '0', icon: FileText },
    { label: 'Consultas Ejecutadas', value: '0', icon: BarChart3 },
    { label: 'Índices Creados', value: '0', icon: TreePine },
    { label: 'Búsquedas Espaciales', value: '0', icon: Map }
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
          Organización e indexación eficiente de archivos con datos tabulares y espaciales. 
          Una solución completa para el manejo de información estructurada y geográfica.
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <Card key={index} className="bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm border-0 shadow-lg">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">{stat.label}</p>
                    <p className="text-3xl font-bold text-gray-900 dark:text-white">{stat.value}</p>
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
            <Card key={index} className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border-0 shadow-lg hover:shadow-xl transition-all duration-300 group">
              <CardHeader className="pb-4">
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 bg-gradient-to-br ${feature.color} rounded-xl flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300`}>
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

      {/* Quick Actions */}
      <Card className="bg-gradient-to-r from-blue-50 to-emerald-50 dark:from-gray-800 dark:to-gray-700 border-0 shadow-lg">
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            <Zap className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            Acciones Rápidas
          </CardTitle>
          <CardDescription>
            Comienza a trabajar con tus datos de inmediato
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Button className="h-12 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white shadow-lg">
              <Upload className="w-4 h-4 mr-2" />
              Subir CSV
            </Button>
            <Button variant="outline" className="h-12 border-emerald-300 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-600 dark:text-emerald-400">
              <Search className="w-4 h-4 mr-2" />
              Nueva Consulta
            </Button>
            <Button variant="outline" className="h-12 border-purple-300 text-purple-700 hover:bg-purple-50 dark:border-purple-600 dark:text-purple-400">
              <TreePine className="w-4 h-4 mr-2" />
              Ver Índices
            </Button>
            <Button variant="outline" className="h-12 border-orange-300 text-orange-700 hover:bg-orange-50 dark:border-orange-600 dark:text-orange-400">
              <Map className="w-4 h-4 mr-2" />
              Mapa Espacial
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Project Info */}
      <Card className="bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm border-0 shadow-lg">
        <CardHeader>
          <CardTitle>Sobre el Proyecto</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Objetivos Principales</h4>
              <ul className="space-y-2 text-gray-600 dark:text-gray-400">
                <li className="flex items-start gap-2">
                  <div className="w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                  Implementar estructuras de indexación eficientes
                </li>
                <li className="flex items-start gap-2">
                  <div className="w-2 h-2 bg-emerald-500 rounded-full mt-2"></div>
                  Optimizar consultas sobre datos tabulares
                </li>
                <li className="flex items-start gap-2">
                  <div className="w-2 h-2 bg-purple-500 rounded-full mt-2"></div>
                  Manejar datos espaciales con R-Tree
                </li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Tecnologías</h4>
              <ul className="space-y-2 text-gray-600 dark:text-gray-400">
                <li className="flex items-start gap-2">
                  <div className="w-2 h-2 bg-orange-500 rounded-full mt-2"></div>
                  Índices Sequential, ISAM, Hash, B+Tree
                </li>
                <li className="flex items-start gap-2">
                  <div className="w-2 h-2 bg-red-500 rounded-full mt-2"></div>
                  R-Tree para datos espaciales
                </li>
                <li className="flex items-start gap-2">
                  <div className="w-2 h-2 bg-indigo-500 rounded-full mt-2"></div>
                  Interfaz web responsiva
                </li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}