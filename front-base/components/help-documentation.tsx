"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  HelpCircle,
  BookOpen,
  Code2,
  Github,
  ExternalLink,
  Database,
  Search,
  Image,
  FileText,
  Zap,
  Music
} from "lucide-react"
import { cn } from "@/lib/utils"

export function HelpDocumentation() {
  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="animate-fade-in">
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-foreground/70 bg-clip-text text-transparent">
          Ayuda y Documentación
        </h1>
        <p className="text-muted-foreground mt-2">
          Guía completa del Sistema de Base de Datos Multimodal - Proyecto 2
        </p>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="guide" className="space-y-6">
        <TabsList className="grid w-full max-w-2xl grid-cols-4 bg-white/5 border border-white/10">
          <TabsTrigger value="guide">Guía Rápida</TabsTrigger>
          <TabsTrigger value="features">Funcionalidades</TabsTrigger>
          <TabsTrigger value="examples">Ejemplos</TabsTrigger>
          <TabsTrigger value="resources">Recursos</TabsTrigger>
        </TabsList>

        {/* Quick Guide Tab */}
        <TabsContent value="guide" className="space-y-6 animate-fade-in">
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-primary" />
                Guía de Inicio Rápido
              </CardTitle>
              <CardDescription>Aprende a usar el sistema paso a paso</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Búsqueda de Texto */}
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold">
                    1
                  </div>
                  <h3 className="text-lg font-semibold">Búsqueda de Texto</h3>
                </div>
                <p className="text-sm text-muted-foreground ml-11">
                  Ve a <span className="font-mono text-primary">Text Search</span> y sube un archivo CSV con columnas{" "}
                  <code className="bg-black/30 px-1 rounded">id</code> y{" "}
                  <code className="bg-black/30 px-1 rounded">text</code>. El sistema construirá un índice invertido
                  usando SPIMI y podrás buscar documentos por similitud de texto usando TF-IDF y Cosine Similarity.
                </p>
              </div>

              {/* Búsqueda Multimedia */}
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold">
                    2
                  </div>
                  <h3 className="text-lg font-semibold">Búsqueda Multimedia (Imágenes y Audio)</h3>
                </div>
                <p className="text-sm text-muted-foreground ml-11">
                  En <span className="font-mono text-primary">Multimedia Search</span>, sube un archivo ZIP con
                  imágenes (.jpg, .png) o audios (.wav, .mp3). El sistema extraerá características visuales (SIFT)
                  o acústicas (MFCC) y creará un índice. Luego podrás buscar imágenes/audios similares.
                </p>
              </div>

              {/* Comparación de Métodos */}
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold">
                    3
                  </div>
                  <h3 className="text-lg font-semibold">Comparar Métodos de Búsqueda</h3>
                </div>
                <p className="text-sm text-muted-foreground ml-11">
                  Usa la pestaña <span className="font-mono text-primary">Compare Methods</span> para ver la
                  diferencia de rendimiento entre búsqueda secuencial (KNN) y búsqueda indexada (Inverted Index).
                  Verás métricas de tiempo de ejecución y speedup.
                </p>
              </div>

              {/* Visualización de Resultados */}
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold">
                    4
                  </div>
                  <h3 className="text-lg font-semibold">Visualizar Resultados</h3>
                </div>
                <p className="text-sm text-muted-foreground ml-11">
                  Los resultados se muestran ordenados por similitud. Para texto, verás el contenido del documento
                  y el score de similitud. Para multimedia, verás las imágenes/audios similares con porcentajes
                  de similitud.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Important Notes */}
          <Card className="glass-card border-white/10 bg-gradient-to-br from-yellow-500/10 to-transparent">
            <CardHeader>
              <CardTitle className="text-yellow-500">⚠️ Notas Importantes</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <p>• <strong>Formato CSV para texto:</strong> Debe tener columnas <code className="bg-black/30 px-1 rounded">id</code> o <code className="bg-black/30 px-1 rounded">doc_id</code> y <code className="bg-black/30 px-1 rounded">text</code> o <code className="bg-black/30 px-1 rounded">content</code>.</p>
              <p>• <strong>Formato ZIP para multimedia:</strong> Puede contener imágenes y/o audios en cualquier estructura de carpetas.</p>
              <p>• <strong>Tamaño de vocabulario (K):</strong> Para multimedia, K=100 es rápido pero básico. K=500 da mejores resultados.</p>
              <p>• <strong>Reconstruir índice:</strong> Si cambias los datos, debes reconstruir el índice para ver los cambios.</p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Features Tab */}
        <TabsContent value="features" className="space-y-6 animate-fade-in">
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle>Funcionalidades Principales</CardTitle>
              <CardDescription>Todas las capacidades del sistema</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                {[
                  {
                    icon: FileText,
                    title: "Búsqueda de Texto (SPIMI)",
                    desc: "Índice invertido con TF-IDF y Cosine Similarity. Soporta búsquedas en lenguaje natural con ranking de relevancia.",
                  },
                  {
                    icon: Image,
                    title: "Búsqueda de Imágenes (SIFT)",
                    desc: "Extracción de características visuales usando SIFT. Búsqueda por similitud visual con Bag of Visual Words y distancia Chi-Cuadrado.",
                  },
                  {
                    icon: Music,
                    title: "Búsqueda de Audio (MFCC)",
                    desc: "Análisis de características acústicas usando MFCC. Encuentra audios similares por contenido sonoro.",
                  },
                  {
                    icon: Zap,
                    title: "Índice Invertido",
                    desc: "Estructura de datos optimizada para búsquedas rápidas. Usa posting lists con TF-IDF weights para ranking eficiente.",
                  },
                  {
                    icon: Search,
                    title: "KNN Secuencial vs Indexado",
                    desc: "Compara búsqueda secuencial (fuerza bruta) contra búsqueda indexada. Visualiza métricas de rendimiento.",
                  },
                  {
                    icon: Database,
                    title: "Bag of Words / Visual Words",
                    desc: "Clustering de características usando K-Means. Convierte descriptores en histogramas para comparación eficiente.",
                  },
                ].map((feature, idx) => {
                  const Icon = feature.icon
                  return (
                    <div
                      key={idx}
                      className="p-4 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 transition-colors"
                    >
                      <div className="flex items-start gap-3 mb-2">
                        <Icon className="h-5 w-5 text-primary mt-0.5" />
                        <h4 className="font-semibold text-foreground">{feature.title}</h4>
                      </div>
                      <p className="text-xs text-muted-foreground">{feature.desc}</p>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>

          {/* Technical Details */}
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle>Detalles Técnicos</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <h4 className="font-semibold text-foreground">Algoritmos Implementados</h4>
                <ul className="text-sm text-muted-foreground space-y-1 ml-4">
                  <li>• <strong>SPIMI:</strong> Single-Pass In-Memory Indexing para construcción eficiente de índices</li>
                  <li>• <strong>TF-IDF:</strong> Term Frequency - Inverse Document Frequency para ponderación de términos</li>
                  <li>• <strong>Cosine Similarity:</strong> Medida de similitud entre vectores de documentos</li>
                  <li>• <strong>SIFT:</strong> Scale-Invariant Feature Transform para detección de puntos clave en imágenes</li>
                  <li>• <strong>MFCC:</strong> Mel-Frequency Cepstral Coefficients para análisis de audio</li>
                  <li>• <strong>K-Means:</strong> Clustering para creación de vocabularios visuales/acústicos</li>
                  <li>• <strong>Chi-Square Distance:</strong> Métrica optimizada para comparación de histogramas</li>
                </ul>
              </div>

              <div className="space-y-2">
                <h4 className="font-semibold text-foreground">Estructuras de Datos</h4>
                <ul className="text-sm text-muted-foreground space-y-1 ml-4">
                  <li>• <strong>Inverted Index:</strong> term → [(doc_id, tf-idf_weight), ...]</li>
                  <li>• <strong>Document Metadata:</strong> doc_id → {'{'}length, norm, text{'}'}</li>
                  <li>• <strong>Codebook:</strong> K-Means clusters para vocabulario visual/acústico</li>
                  <li>• <strong>Feature Vectors:</strong> Histogramas normalizados L1 para comparación</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Examples Tab */}
        <TabsContent value="examples" className="space-y-6 animate-fade-in">
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Code2 className="h-5 w-5 text-primary" />
                Ejemplos de Uso
              </CardTitle>
              <CardDescription>Casos de uso comunes paso a paso</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Ejemplo 1 */}
              <div className="space-y-3">
                <h4 className="font-semibold text-foreground">Ejemplo 1: Búsqueda de Documentos de Texto</h4>
                <div className="rounded-lg bg-black/30 border border-white/10 p-4 font-mono text-sm space-y-1">
                  <p className="text-blue-400">1. Ve a "Text Search" → pestaña "Upload & Index"</p>
                  <p className="text-blue-400">2. Sube un CSV con columnas: id, text</p>
                  <p className="text-blue-400">3. Haz clic en "Upload & Build Index"</p>
                  <p className="text-blue-400">4. Ve a la pestaña "Search"</p>
                  <p className="text-blue-400">5. Escribe: "machine learning algorithms"</p>
                  <p className="text-blue-400">6. Selecciona Top-K: 10</p>
                  <p className="text-green-400">✓ Resultado: Lista de documentos ordenados por relevancia</p>
                </div>
              </div>

              {/* Ejemplo 2 */}
              <div className="space-y-3">
                <h4 className="font-semibold text-foreground">Ejemplo 2: Búsqueda de Imágenes Similares</h4>
                <div className="rounded-lg bg-black/30 border border-white/10 p-4 font-mono text-sm space-y-1">
                  <p className="text-blue-400">1. Ve a "Multimedia Search" → pestaña "Build Index"</p>
                  <p className="text-blue-400">2. Sube un ZIP con imágenes (ej: paisajes.zip)</p>
                  <p className="text-blue-400">3. Vocabulary Size (K): 200</p>
                  <p className="text-blue-400">4. Haz clic en "Build Index"</p>
                  <p className="text-blue-400">5. Ve a "Search" y sube una imagen de consulta</p>
                  <p className="text-blue-400">6. Top-K: 5</p>
                  <p className="text-green-400">✓ Resultado: Galería de imágenes similares con % de similitud</p>
                </div>
              </div>

              {/* Ejemplo 3 */}
              <div className="space-y-3">
                <h4 className="font-semibold text-foreground">Ejemplo 3: Comparar Métodos de Búsqueda</h4>
                <div className="rounded-lg bg-black/30 border border-white/10 p-4 font-mono text-sm space-y-1">
                  <p className="text-blue-400">1. Construye un índice multimedia (ver Ejemplo 2)</p>
                  <p className="text-blue-400">2. Ve a la pestaña "Compare Methods"</p>
                  <p className="text-blue-400">3. Sube una imagen/audio de consulta</p>
                  <p className="text-blue-400">4. Top-K: 10</p>
                  <p className="text-blue-400">5. Haz clic en "Compare Methods"</p>
                  <p className="text-green-400">✓ Resultado: Tabla comparativa con tiempos de ejecución</p>
                  <p className="text-green-400">  - Sequential: tiempo de búsqueda secuencial</p>
                  <p className="text-green-400">  - Indexed: tiempo con índice invertido</p>
                  <p className="text-green-400">  - Speedup: cuánto más rápido es el índice</p>
                </div>
              </div>

              {/* Ejemplo 4 */}
              <div className="space-y-3">
                <h4 className="font-semibold text-foreground">Ejemplo 4: Búsqueda de Audio Similar</h4>
                <div className="rounded-lg bg-black/30 border border-white/10 p-4 font-mono text-sm space-y-1">
                  <p className="text-blue-400">1. Prepara un ZIP con archivos .wav o .mp3</p>
                  <p className="text-blue-400">2. Ve a "Multimedia Search" → "Build Index"</p>
                  <p className="text-blue-400">3. Sube el ZIP de audios</p>
                  <p className="text-blue-400">4. K: 150 (vocabulario acústico)</p>
                  <p className="text-blue-400">5. Build Index</p>
                  <p className="text-blue-400">6. En "Search", sube un audio de consulta</p>
                  <p className="text-green-400">✓ Resultado: Lista de audios similares con reproductores</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Tips */}
          <Card className="glass-card border-white/10 bg-gradient-to-br from-blue-500/10 to-transparent">
            <CardHeader>
              <CardTitle className="text-blue-400">💡 Consejos y Trucos</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <p>• <strong>Vocabulario pequeño (K=50-100):</strong> Rápido pero menos preciso. Bueno para pruebas.</p>
              <p>• <strong>Vocabulario grande (K=300-500):</strong> Más lento pero resultados más precisos.</p>
              <p>• <strong>CSV con muchas columnas:</strong> El sistema concatenará todas las columnas (excepto ID) si no encuentra "text".</p>
              <p>• <strong>Imágenes idénticas:</strong> Deberían tener ~100% de similitud. Si no, reconstruye el índice.</p>
              <p>• <strong>Speedup bajo:</strong> Normal con pocos documentos. El índice brilla con datasets grandes (&gt;1000 items).</p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Resources Tab */}
        <TabsContent value="resources" className="space-y-6 animate-fade-in">
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ExternalLink className="h-5 w-5 text-primary" />
                Recursos y Enlaces
              </CardTitle>
              <CardDescription>Documentación externa y referencias del proyecto</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                {
                  icon: Github,
                  title: "Repositorio GitHub",
                  desc: "Código fuente completo del proyecto y documentación técnica",
                  link: "https://github.com/MarcoMadridG27/Proyecto-Base2",
                },
                {
                  icon: Code2,
                  title: "Documentación de la API",
                  desc: "Endpoints del backend, formatos de request/response y ejemplos interactivos",
                  link: "http://localhost:8000/docs",
                },
                {
                  icon: BookOpen,
                  title: "Informe del Proyecto",
                  desc: "Especificación completa, arquitectura del sistema y análisis de rendimiento",
                  link: "#",
                },
              ].map((resource, idx) => {
                const Icon = resource.icon
                return (
                  <a
                    key={idx}
                    href={resource.link}
                    target={resource.link.startsWith("http") ? "_blank" : "_self"}
                    rel={resource.link.startsWith("http") ? "noopener noreferrer" : undefined}
                    className={cn(
                      "block p-4 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 hover:border-primary/50 transition-all duration-300 group cursor-pointer"
                    )}
                  >
                    <div className="flex items-start gap-4">
                      <Icon className="h-5 w-5 text-primary mt-1 group-hover:scale-110 transition-transform" />
                      <div className="flex-1 min-w-0">
                        <h4 className="font-semibold text-foreground group-hover:text-primary transition-colors">
                          {resource.title}
                        </h4>
                        <p className="text-sm text-muted-foreground mt-1">{resource.desc}</p>
                      </div>
                      <ExternalLink className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors flex-shrink-0 mt-1" />
                    </div>
                  </a>
                )
              })}
            </CardContent>
          </Card>

          {/* FAQ */}
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle>Preguntas Frecuentes (FAQ)</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                {
                  q: "¿Por qué mis imágenes no se muestran en los resultados?",
                  a: "Asegúrate de haber reconstruido el índice después de subir el ZIP. Si el problema persiste, verifica que las imágenes estén en formatos soportados (.jpg, .png, .bmp).",
                },
                {
                  q: "¿Qué significa el 'speedup' en la comparación de métodos?",
                  a: "Es cuántas veces más rápido es el método indexado comparado con el secuencial. Por ejemplo, speedup=10x significa que el índice es 10 veces más rápido.",
                },
                {
                  q: "¿Puedo buscar con una imagen que no está en el índice?",
                  a: "Sí, puedes subir cualquier imagen como consulta. El sistema extraerá sus características y buscará las más similares en el índice.",
                },
                {
                  q: "¿Por qué la similitud de imágenes idénticas no es 100%?",
                  a: "Puede deberse a la normalización o al tamaño del vocabulario (K). Intenta reconstruir el índice con K más grande (ej: K=500).",
                },
                {
                  q: "¿Cómo funciona la búsqueda de texto si mi consulta tiene palabras que no están en los documentos?",
                  a: "El sistema usa stemming (raíces de palabras) y TF-IDF. Si ninguna palabra coincide, no habrá resultados. Intenta con sinónimos o términos más generales.",
                },
              ].map((faq, idx) => (
                <div key={idx} className="p-4 rounded-lg border border-white/10 bg-white/5">
                  <h4 className="font-semibold text-foreground mb-2">❓ {faq.q}</h4>
                  <p className="text-sm text-muted-foreground">{faq.a}</p>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Contact & Support */}
          <Card className="glass-card border-white/10 bg-gradient-to-br from-primary/10 to-secondary/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <HelpCircle className="h-5 w-5 text-primary" />
                ¿Necesitas Ayuda?
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-foreground mb-4">
                Si tienes problemas, sugerencias o preguntas sobre el sistema:
              </p>
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>• Revisa esta sección de Ayuda para preguntas comunes</p>
                <p>• Consulta la documentación de la API en /docs</p>
                <p>• Visita el repositorio de GitHub y crea un issue</p>
                <p>• Contacta al equipo de desarrollo para soporte urgente</p>
              </div>
              <Button
                className="mt-6 w-full bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary/80 text-primary-foreground shadow-lg shadow-primary/30"
                onClick={() => window.open("https://github.com/MarcoMadridG27/Proyecto-Base2", "_blank")}
              >
                <Github className="h-4 w-4 mr-2" />
                Visitar Repositorio en GitHub
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
