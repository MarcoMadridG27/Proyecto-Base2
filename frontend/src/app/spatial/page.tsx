"use client";
import React, { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/app/components/ui/card";
import { Button } from "@/app/components/ui/button";
import { Input } from "@/app/components/ui/input";
import { Label } from "@/app/components/ui/label";
import { Badge } from "@/app/components/ui/badge";
import { Slider } from "@/app/components/ui/slider";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/app/components/ui/table";

import { Map, MapPin, Search, Target, Circle, Square, Navigation } from "lucide-react";
import { toast } from "sonner";


interface SpatialPoint {
  id: string;
  name: string;
  lat: number;
  lng: number;
  category: string;
  data: Record<string, any>;
}

interface SearchArea {
  centerLat: number;
  centerLng: number;
  radius: number;
  type: 'circle' | 'rectangle';
}

export default function Page() {
  const mapRef = useRef<HTMLDivElement>(null);
  const [searchArea, setSearchArea] = useState<SearchArea>({
    centerLat: -12.0464,
    centerLng: -77.0428,
    radius: 10,
    type: 'circle'
  });
  const [searchResults, setSearchResults] = useState<SpatialPoint[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedPoint, setSelectedPoint] = useState<SpatialPoint | null>(null);

  // Sample spatial data
  const spatialData: SpatialPoint[] = [
    {
      id: '1',
      name: 'Universidad Tecnológica del Perú',
      lat: -12.0464,
      lng: -77.0428,
      category: 'Universidad',
      data: { estudiantes: 15000, fundacion: 1997 }
    },
    {
      id: '2',
      name: 'Plaza de Armas',
      lat: -12.0431,
      lng: -77.0282,
      category: 'Sitio Histórico',
      data: { año: 1535, area: '133.8 m²' }
    },
    {
      id: '3',
      name: 'Miraflores',
      lat: -12.1196,
      lng: -77.0278,
      category: 'Distrito',
      data: { poblacion: 81932, area: '9.62 km²' }
    },
    {
      id: '4',
      name: 'Callao',
      lat: -12.0566,
      lng: -77.1181,
      category: 'Puerto',
      data: { puerto: 'Principal', año: 1537 }
    },
    {
      id: '5',
      name: 'San Isidro',
      lat: -12.1028,
      lng: -77.0347,
      category: 'Distrito',
      data: { poblacion: 54206, area: '11.1 km²' }
    },
    {
      id: '6',
      name: 'Barranco',
      lat: -12.1461,
      lng: -77.0208,
      category: 'Distrito',
      data: { poblacion: 29984, area: '3.33 km²' }
    }
  ];
const executeSearch = async () => {
  setIsSearching(true);
  setSearchResults([]);
  try {
    const res = await fetch("http://localhost:8000/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: `SELECT * FROM ubicaciones WHERE ST_Within(geom, ${searchArea.type.toUpperCase()}(${searchArea.centerLat}, ${searchArea.centerLng}, ${searchArea.radius}))`,
      }),
    });

    const data = await res.json();

    if (res.ok && data.ok) {
      // Se asume que tu backend devuelve rows con [id, name, lat, lng, category, ...]
      const parsedResults: SpatialPoint[] = data.result.rows.map(
        (row: any[], idx: number) => ({
          id: row[0] || idx.toString(),
          name: row[1] || "Sin nombre",
          lat: parseFloat(row[2]),
          lng: parseFloat(row[3]),
          category: row[4] || "Otro",
          data: row.slice(5).reduce(
            (acc: any, val: any, i: number) => ({
              ...acc,
              [`extra_${i}`]: val,
            }),
            {}
          ),
        })
      );

      setSearchResults(parsedResults);
      toast.success(`Encontrados ${parsedResults.length} puntos en el área`);
    } else {
      throw new Error(data.error || "Error en la búsqueda espacial");
    }
  } catch (err) {
    console.error(err);
    toast.error("Error de conexión con backend");
  } finally {
    setIsSearching(false);
  }
};


  const calculateDistance = (lat1: number, lng1: number, lat2: number, lng2: number): number => {
    const R = 6371; // Earth's radius in km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLng/2) * Math.sin(dLng/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
  };

  const renderMap = () => {
    return (
      <div className="relative w-full h-96 bg-gradient-to-br from-blue-100 to-emerald-100 dark:from-gray-700 dark:to-gray-600 rounded-lg overflow-hidden">
        {/* Map Grid */}
        <div className="absolute inset-0 opacity-20">
          <svg width="100%" height="100%">
            <defs>
              <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                <path d="M 20 0 L 0 0 0 20" fill="none" stroke="currentColor" strokeWidth="1"/>
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid)" />
          </svg>
        </div>

        {/* Search Area Overlay */}
        {searchArea.type === 'circle' ? (
          <div 
            className="absolute border-2 border-blue-500 border-dashed bg-blue-200/30 rounded-full"
            style={{
              width: `${searchArea.radius * 8}px`,
              height: `${searchArea.radius * 8}px`,
              left: '50%',
              top: '50%',
              transform: 'translate(-50%, -50%)'
            }}
          />
        ) : (
          <div 
            className="absolute border-2 border-blue-500 border-dashed bg-blue-200/30"
            style={{
              width: `${searchArea.radius * 8}px`,
              height: `${searchArea.radius * 8}px`,
              left: '50%',
              top: '50%',
              transform: 'translate(-50%, -50%)'
            }}
          />
        )}

        {/* Center Point */}
        <div className="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2">
          <Target className="w-6 h-6 text-red-500" />
        </div>

        {/* Data Points */}
        {spatialData.map((point, index) => {
          const isInResults = searchResults.some(r => r.id === point.id);
          const x = 50 + (point.lng + 77.0428) * 800; // Simplified positioning
          const y = 50 + (point.lat + 12.0464) * 800;
          
          return (
            <div
              key={point.id}
              className={`absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer transition-all duration-300 ${
                isInResults ? 'scale-125 z-10' : 'hover:scale-110'
              }`}
              style={{ 
                left: `${Math.max(5, Math.min(95, x))}%`, 
                top: `${Math.max(5, Math.min(95, y))}%` 
              }}
              onClick={() => setSelectedPoint(point)}
            >
              <div className={`w-4 h-4 rounded-full border-2 border-white shadow-lg ${
                isInResults 
                  ? 'bg-emerald-500' 
                  : point.category === 'Universidad' 
                    ? 'bg-blue-500'
                    : point.category === 'Distrito'
                      ? 'bg-purple-500'
                      : 'bg-orange-500'
              }`} />
              {isInResults && (
                <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 bg-white dark:bg-gray-800 px-2 py-1 rounded text-xs shadow-lg whitespace-nowrap">
                  {point.name}
                </div>
              )}
            </div>
          );
        })}

        {/* Map Legend */}
        <div className="absolute bottom-4 left-4 bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm rounded-lg p-3 space-y-2">
          <h4 className="font-medium text-sm">Leyenda</h4>
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs">
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
              <span>Universidad</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
              <span>Distrito</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <div className="w-3 h-3 bg-orange-500 rounded-full"></div>
              <span>Sitio</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <div className="w-3 h-3 bg-emerald-500 rounded-full"></div>
              <span>En resultados</span>
            </div>
          </div>
        </div>

        {/* Coordinates Display */}
        <div className="absolute top-4 right-4 bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm rounded-lg p-3">
          <div className="text-xs space-y-1">
            <div>Centro: {searchArea.centerLat.toFixed(4)}, {searchArea.centerLng.toFixed(4)}</div>
            <div>Radio: {searchArea.radius} km</div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Resultados Espaciales</h2>
          <p className="text-gray-600 dark:text-gray-400">
            Explora datos geoespaciales con R-Tree y consultas espaciales
          </p>
        </div>
        <Badge variant="outline" className="flex items-center gap-2">
          <MapPin className="w-4 h-4" />
          {spatialData.length} puntos cargados
        </Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Search Controls */}
        <div className="space-y-4">
          <Card className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border-0 shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="w-5 h-5" />
                Consulta Espacial
              </CardTitle>
              <CardDescription>
                Configura el área de búsqueda
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Latitud Centro</Label>
                  <Input
                    type="number"
                    step="0.0001"
                    value={searchArea.centerLat}
                    onChange={(e) => setSearchArea(prev => ({
                      ...prev,
                      centerLat: parseFloat(e.target.value) || 0
                    }))}
                  />
                </div>
                <div>
                  <Label>Longitud Centro</Label>
                  <Input
                    type="number"
                    step="0.0001"
                    value={searchArea.centerLng}
                    onChange={(e) => setSearchArea(prev => ({
                      ...prev,
                      centerLng: parseFloat(e.target.value) || 0
                    }))}
                  />
                </div>
              </div>

              <div>
                <Label>Radio de Búsqueda: {searchArea.radius} km</Label>
                <Slider
                  value={[searchArea.radius]}
                  onValueChange={(value) => setSearchArea(prev => ({
                    ...prev,
                    radius: value[0]
                  }))}
                  max={50}
                  min={1}
                  step={1}
                  className="mt-2"
                />
              </div>

              <div className="flex gap-2">
                <Button
                  variant={searchArea.type === 'circle' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSearchArea(prev => ({ ...prev, type: 'circle' }))}
                  className="flex-1"
                >
                  <Circle className="w-4 h-4 mr-2" />
                  Circular
                </Button>
                <Button
                  variant={searchArea.type === 'rectangle' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSearchArea(prev => ({ ...prev, type: 'rectangle' }))}
                  className="flex-1"
                >
                  <Square className="w-4 h-4 mr-2" />
                  Rectangular
                </Button>
              </div>

              <Button 
                onClick={executeSearch} 
                disabled={isSearching}
                className="w-full bg-gradient-to-r from-blue-500 to-emerald-500 hover:from-blue-600 hover:to-emerald-600"
              >
                <Search className="w-4 h-4 mr-2" />
                {isSearching ? 'Buscando...' : 'Ejecutar Búsqueda'}
              </Button>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border-0 shadow-lg">
            <CardHeader>
              <CardTitle className="text-lg">Ubicaciones Rápidas</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button
                variant="ghost"
                className="w-full justify-start"
                onClick={() => setSearchArea(prev => ({
                  ...prev,
                  centerLat: -12.0464,
                  centerLng: -77.0428
                }))}
              >
                <Navigation className="w-4 h-4 mr-2" />
                Centro de Lima
              </Button>
              <Button
                variant="ghost"
                className="w-full justify-start"
                onClick={() => setSearchArea(prev => ({
                  ...prev,
                  centerLat: -12.1196,
                  centerLng: -77.0278
                }))}
              >
                <Navigation className="w-4 h-4 mr-2" />
                Miraflores
              </Button>
              <Button
                variant="ghost"
                className="w-full justify-start"
                onClick={() => setSearchArea(prev => ({
                  ...prev,
                  centerLat: -12.0566,
                  centerLng: -77.1181
                }))}
              >
                <Navigation className="w-4 h-4 mr-2" />
                Callao
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Map Visualization */}
        <div className="lg:col-span-2">
          <Card className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border-0 shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Map className="w-5 h-5" />
                Mapa Espacial Interactivo
              </CardTitle>
              <CardDescription>
                Visualización de datos geoespaciales con R-Tree
              </CardDescription>
            </CardHeader>
            <CardContent>
              {renderMap()}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Search Results */}
      {searchResults.length > 0 && (
        <Card className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border-0 shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="w-5 h-5" />
              Resultados de Búsqueda Espacial
            </CardTitle>
            <CardDescription>
              {searchResults.length} puntos encontrados en el área de búsqueda
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Categoría</TableHead>
                  <TableHead>Coordenadas</TableHead>
                  <TableHead>Distancia</TableHead>
                  <TableHead>Datos</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {searchResults.map((point) => {
                  const distance = calculateDistance(
                    searchArea.centerLat,
                    searchArea.centerLng,
                    point.lat,
                    point.lng
                  );
                  
                  return (
                    <TableRow 
                      key={point.id}
                      className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700"
                      onClick={() => setSelectedPoint(point)}
                    >
                      <TableCell className="font-medium">{point.name}</TableCell>
                      <TableCell>
                        <Badge variant="secondary">{point.category}</Badge>
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {point.lat.toFixed(4)}, {point.lng.toFixed(4)}
                      </TableCell>
                      <TableCell>{distance.toFixed(2)} km</TableCell>
                      <TableCell>
                        <div className="text-sm text-gray-600 dark:text-gray-400">
                          {Object.entries(point.data).map(([key, value]) => (
                            <div key={key}>{key}: {value}</div>
                          ))}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Selected Point Details */}
      {selectedPoint && (
        <Card className="bg-gradient-to-r from-emerald-50 to-blue-50 dark:from-gray-800 dark:to-gray-700 border-0 shadow-lg">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <MapPin className="w-5 h-5 text-emerald-600" />
                {selectedPoint.name}
              </CardTitle>
              <Button variant="ghost" size="sm" onClick={() => setSelectedPoint(null)}>
                ✕
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h5 className="font-medium mb-2">Información Básica</h5>
                <div className="space-y-1 text-sm">
                  <div>Categoría: <Badge variant="secondary">{selectedPoint.category}</Badge></div>
                  <div>Latitud: {selectedPoint.lat}</div>
                  <div>Longitud: {selectedPoint.lng}</div>
                </div>
              </div>
              <div>
                <h5 className="font-medium mb-2">Datos Adicionales</h5>
                <div className="space-y-1 text-sm">
                  {Object.entries(selectedPoint.data).map(([key, value]) => (
                    <div key={key}>{key}: {value}</div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}