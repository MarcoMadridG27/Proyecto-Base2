"use client";
import React, { useState, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/app/components/ui/card";
import { Button } from "@/app/components/ui/button";
import { Input } from "@/app/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/app/components/ui/table";
import { Alert, AlertDescription } from "@/app/components/ui/alert";
import { Badge } from "@/app/components/ui/badge";
import { Progress } from "@/app/components/ui/progress";

import { Upload, File, CheckCircle, AlertCircle, X, Download } from "lucide-react";
import { toast } from "sonner";


interface CsvData {
  headers: string[];
  rows: string[][];
  fileName: string;
  fileSize: string;
  recordCount: number;
}

export default function Page() {
  const [csvData, setCsvData] = useState<CsvData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);

  const parseCSV = (text: string): { headers: string[], rows: string[][] } => {
    const lines = text.trim().split('\n');
    const headers = lines[0].split(',').map(h => h.trim().replace(/"/g, ''));
    const rows = lines.slice(1).map(line => 
      line.split(',').map(cell => cell.trim().replace(/"/g, ''))
    );
    return { headers, rows };
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleFile = useCallback((file: File) => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      toast.error('Por favor selecciona un archivo CSV válido');
      return;
    }

    setIsLoading(true);
    setUploadProgress(0);

    // Simulate upload progress
    const progressInterval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 90) {
          clearInterval(progressInterval);
          return 90;
        }
        return prev + 10;
      });
    }, 100);

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target?.result as string;
        const { headers, rows } = parseCSV(text);
        
        setTimeout(() => {
          setUploadProgress(100);
          setCsvData({
            headers,
            rows,
            fileName: file.name,
            fileSize: formatFileSize(file.size),
            recordCount: rows.length
          });
          setIsLoading(false);
          toast.success(`Archivo ${file.name} cargado exitosamente`);
        }, 500);
      } catch (error) {
        setIsLoading(false);
        setUploadProgress(0);
        toast.error('Error al procesar el archivo CSV');
        clearInterval(progressInterval);
      }
    };
    reader.readAsText(file);
  }, []);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const clearData = () => {
    setCsvData(null);
    setUploadProgress(0);
    toast.success('Datos limpiados');
  };

  const downloadSample = () => {
    const sampleCsv = `id,nombre,edad,ciudad,latitud,longitud
1,Juan Pérez,25,Lima,-12.0464,-77.0428
2,María García,30,Arequipa,-16.4090,-71.5375
3,Carlos López,28,Cusco,-13.5319,-71.9675
4,Ana Rodríguez,32,Trujillo,-8.1116,-79.0290
5,Luis Fernández,27,Chiclayo,-6.7714,-79.8391`;
    
    const blob = new Blob([sampleCsv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sample_data.csv';
    a.click();
    window.URL.revokeObjectURL(url);
    toast.success('Archivo de muestra descargado');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Carga de Archivos</h2>
          <p className="text-gray-600 dark:text-gray-400">
            Sube archivos CSV para análisis y procesamiento
          </p>
        </div>
        <Button variant="outline" onClick={downloadSample}>
          <Download className="w-4 h-4 mr-2" />
          Descargar Muestra
        </Button>
      </div>

      {/* Upload Area */}
      <Card className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border-0 shadow-lg">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="w-5 h-5" />
            Subir Archivo CSV
          </CardTitle>
          <CardDescription>
            Arrastra y suelta tu archivo CSV o haz clic para seleccionar
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-all duration-300 ${
              dragActive
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <div className="space-y-4">
              <div className="w-16 h-16 mx-auto bg-gradient-to-br from-blue-500 to-emerald-500 rounded-2xl flex items-center justify-center">
                <Upload className="w-8 h-8 text-white" />
              </div>
              
              {isLoading ? (
                <div className="space-y-4">
                  <p className="text-lg">Procesando archivo...</p>
                  <Progress value={uploadProgress} className="w-full max-w-md mx-auto" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">{uploadProgress}%</p>
                </div>
              ) : (
                <>
                  <div>
                    <p className="text-lg font-medium text-gray-900 dark:text-white">
                      Arrastra tu archivo CSV aquí
                    </p>
                    <p className="text-gray-600 dark:text-gray-400">
                      o haz clic para seleccionar desde tu dispositivo
                    </p>
                  </div>
                  
                  <Input
                    type="file"
                    accept=".csv"
                    onChange={handleFileInput}
                    className="hidden"
                    id="file-upload"
                  />
                  <label htmlFor="file-upload">
                    <Button asChild className="cursor-pointer">
                      <span>Seleccionar Archivo</span>
                    </Button>
                  </label>
                </>
              )}
            </div>
          </div>

          {csvData && (
            <Alert className="mt-4 bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800">
              <CheckCircle className="h-4 w-4 text-emerald-600" />
              <AlertDescription className="text-emerald-800 dark:text-emerald-200">
                Archivo cargado exitosamente: <strong>{csvData.fileName}</strong>
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* File Info */}
      {csvData && (
        <Card className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border-0 shadow-lg">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <File className="w-5 h-5" />
                Información del Archivo
              </CardTitle>
              <Button variant="outline" size="sm" onClick={clearData}>
                <X className="w-4 h-4 mr-2" />
                Limpiar
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="flex items-center gap-3">
                <Badge variant="secondary">Nombre</Badge>
                <span className="text-sm text-gray-600 dark:text-gray-400">{csvData.fileName}</span>
              </div>
              <div className="flex items-center gap-3">
                <Badge variant="secondary">Tamaño</Badge>
                <span className="text-sm text-gray-600 dark:text-gray-400">{csvData.fileSize}</span>
              </div>
              <div className="flex items-center gap-3">
                <Badge variant="secondary">Registros</Badge>
                <span className="text-sm text-gray-600 dark:text-gray-400">{csvData.recordCount}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Data Preview */}
      {csvData && (
        <Card className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm border-0 shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5" />
              Vista Previa de Datos
            </CardTitle>
            <CardDescription>
              Mostrando los primeros {Math.min(10, csvData.rows.length)} registros
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    {csvData.headers.map((header, index) => (
                      <TableHead key={index} className="min-w-[120px]">
                        {header}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {csvData.rows.slice(0, 10).map((row, rowIndex) => (
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
            
            {csvData.rows.length > 10 && (
              <div className="mt-4 text-center text-sm text-gray-600 dark:text-gray-400">
                ... y {csvData.rows.length - 10} registros más
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}