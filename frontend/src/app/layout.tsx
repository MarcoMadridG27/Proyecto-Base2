"use client";
import "../styles/globals.css";
import React, { useState } from "react";
import { Home, Upload, Database, TreePine, Map, Menu, Sun, Moon } from "lucide-react";
import { Button } from "./components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "./components/ui/sheet";
import Link from "next/link";

// Aquí defines los menús de la sidebar
type Screen = "dashboard" | "upload" | "query" | "index" | "spatial";

const menuItems = [
  { id: "dashboard" as Screen, label: "Home", icon: Home },
  { id: "upload" as Screen, label: "Cargar Datos", icon: Upload },
  { id: "query" as Screen, label: "Consultas", icon: Database },
  { id: "index" as Screen, label: "Índices", icon: TreePine },
  { id: "spatial" as Screen, label: "Resultados Espaciales", icon: Map },
];

function Sidebar() {
  const [currentScreen, setCurrentScreen] = useState<Screen>("dashboard");

  return (
    <div className="h-full w-64 bg-gradient-to-b from-blue-50 to-emerald-50 dark:from-gray-900 dark:to-gray-800 border-r border-gray-200 dark:border-gray-700">
      <div className="p-6">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-emerald-500 rounded-lg flex items-center justify-center">
            <Database className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">UTEC DB</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">Sistema Multimodal</p>
          </div>
        </div>


        <nav className="space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentScreen === item.id;

            return (
              <Link key={item.id} href={`/${item.id === "dashboard" ? "" : item.id}`}>
                <Button
                  variant={isActive ? "default" : "ghost"}
                  className={`w-full justify-start gap-3 h-12 ${
                    isActive
                      ? "bg-gradient-to-r from-blue-500 to-emerald-500 text-white shadow-lg"
                      : "text-gray-700 dark:text-gray-300 hover:bg-white/50 dark:hover:bg-gray-700/50"
                  }`}
                  onClick={() => setCurrentScreen(item.id)}
                >
                  <Icon className="w-5 h-5" />
                  {item.label}
                </Button>
              </Link>
            );
          })}
        </nav>

      </div>
    </div>
  );
}

export default function RootLayout({
                                     children,
                                   }: {
  children: React.ReactNode;
}) {
  const [isDarkMode, setIsDarkMode] = useState(false);

  const toggleDarkMode = () => {
    setIsDarkMode(!isDarkMode);
    document.documentElement.classList.toggle("dark");
  };

  return (
    <html lang="es">
    <body
      className={`min-h-screen bg-gray-50 dark:bg-gray-900 ${
        isDarkMode ? "dark" : ""
      }`}
    >
    {/* Header */}
    <header className="h-16 bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-6 sticky top-0 z-40">
      <div className="flex items-center gap-4">
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="lg:hidden">
              <Menu className="w-6 h-6" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="p-0 w-64">
            <Sidebar />
          </SheetContent>
        </Sheet>

        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-emerald-500 rounded-lg flex items-center justify-center">
            <Database className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
              Sistema de Base de Datos Multimodal
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400 hidden sm:block">
              Organización e Indexación Eficiente de Archivos
            </p>
          </div>
        </div>
      </div>

      <Button
        variant="ghost"
        size="icon"
        onClick={toggleDarkMode}
        className="rounded-full"
      >
        {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
      </Button>
    </header>

    {/* Layout principal */}
    <div className="flex">
      {/* Sidebar (desktop) */}
      <aside className="hidden lg:block">
        <Sidebar />
      </aside>

      {/* Main content */}
      <main className="flex-1 p-6">
        <div className="max-w-7xl mx-auto">{children}</div>
      </main>
    </div>
    </body>
    </html>
  );
}
