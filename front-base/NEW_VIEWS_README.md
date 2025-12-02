# Nuevas Vistas - Proyecto 2: Mapeando el Caos

Este documento describe las 4 nuevas pestañas agregadas al sistema UTEC Multimodal Database Management System.

## 1. 📄 Text Search (`/text-search`)

**Componente:** `components/text-search.tsx`

Búsqueda textual avanzada con métricas de similitud.

### Características:
- Campo de entrada para consultas textuales (SQL o lenguaje natural)
- Selector **Top-K** para limitar resultados (1-1000)
- Selector de método: TF-IDF, Cosine Similarity, o Hybrid
- **Tabla de resultados** con columnas:
  - Title: Título del documento
  - Snippet: Fragmento de texto relevante
  - TF-IDF Score: Puntuación TF-IDF
  - Cosine Similarity: Similitud de coseno
  - Score final: Barra visual con porcentaje
- **Métricas:**
  - Execution Time (ms)
  - Total Results
  - Method used

### Endpoint Backend Esperado:
```bash
POST /text_search
{
  "query": "string",
  "top_k": int,
  "method": "tfidf" | "cosine" | "both"
}
```

### Demo:
Si el backend no está disponible, muestra datos de demostración automáticamente.

---

## 2. 🖼️ Multimedia Search (`/multimedia-search`)

**Componente:** `components/multimedia-search.tsx`

Búsqueda de similitud para imágenes y audio.

### Características:
- **Upload Area:** Arrastra y suelta o haz clic para seleccionar
- **Preview:** Muestra vista previa de imagen o reproductor de audio
- Botón **"Find Similar"** para buscar objetos similares
- **Grid de resultados** con tarjetas mostrando:
  - Miniatura (imagen) o ícono (audio)
  - Título del objeto
  - ID único
  - **Barra de similitud** con % (color gradiente)
  - Categoría y tags del objeto
- **Métricas:**
  - Execution Time (ms)
  - Total Similar Objects
  - File Type (image/audio)

### Endpoint Backend Esperado:
```bash
POST /multimedia_search (multipart/form-data)
file: File
type: "image" | "audio"
```

### Demo:
Si el backend no está disponible, retorna 4 objetos similares de demostración.

---

## 3. 📊 Performance & Benchmark (`/performance`)

**Componente:** `components/performance-benchmark.tsx`

Comparación de rendimiento entre técnicas de búsqueda.

### Características:

#### Tab 1: Text Retrieval
- Compara: **SPIMI vs PostgreSQL**
- Gráficos:
  - **Línea:** Tiempo de ejecución (ms) vs Tamaño del dataset (N)
  - **Barras:** Precisión (0-1) vs Tamaño del dataset
- Estadísticas resumidas:
  - Método más rápido
  - Mejor precisión
  - Ratio de rendimiento

#### Tab 2: Multimedia Retrieval
- Compara: **KNN Sequential vs KNN Indexed vs pgVector**
- Gráficos idénticos al tab de Text Retrieval
- Mismas estadísticas resumidas

### Características Especiales:
- Carga de datos personalizados (JSON/CSV)
- Demo data precargada
- Colores diferenciados por técnica
- Animaciones smooth en gráficos

### Endpoint Backend Esperado:
```bash
POST /upload_benchmark (multipart/form-data)
file: File
type: "text" | "multimedia"
```

---

## 4. 📚 Help & Documentation (`/help`)

**Componente:** `components/help-documentation.tsx`

Documentación completa y guía de usuario.

### Tabs:

#### Quick Guide
- Guía paso a paso (5 pasos)
- Overview de características disponibles
- Workflow típico del sistema

#### Examples
- 4 ejemplos prácticos:
  1. Upload and Search
  2. Text Search
  3. Multimedia Search
  4. Performance Comparison

#### Queries
- Referencia SQL completa
- 7 patrones comunes:
  - Simple SELECT
  - WHERE
  - BETWEEN (para índices)
  - ORDER BY / LIMIT
  - INSERT
  - DELETE
  - CREATE INDEX

#### Resources
- Enlaces a GitHub
- Links a API docs
- Página de documentación del proyecto
- Sección de soporte y contacto

---

## 🎨 Diseño Visual

Todas las nuevas vistas mantienen la consistencia con el dashboard existente:

✅ **Modo Oscuro:** Background oscuro con tarjetas glass-morphism  
✅ **Tipografía:** Geist Sans (moderna, limpia)  
✅ **Tarjetas:** Esquinas redondeadas (lg), bordes subtle, sombras suaves  
✅ **Colores:**
- Primary: Azul/Cyan
- Secondary: Rosa/Magenta
- Gradientes: Primary → Secondary
✅ **Animaciones:** Fade-in, scale-in, stagger effects  
✅ **Responsive:** Mobile-first, grid layouts adaptables  

---

## 📁 Estructura de Archivos Creados

```
front-base/
├── app/
│   ├── text-search/
│   │   └── page.tsx              # Layout para /text-search
│   ├── multimedia-search/
│   │   └── page.tsx              # Layout para /multimedia-search
│   ├── performance/
│   │   └── page.tsx              # Layout para /performance
│   └── help/
│       └── page.tsx              # Layout para /help
│
└── components/
    ├── text-search.tsx           # Componente Text Search
    ├── multimedia-search.tsx     # Componente Multimedia Search
    ├── performance-benchmark.tsx # Componente Performance Benchmark
    ├── help-documentation.tsx    # Componente Help/Documentation
    └── sidebar.tsx               # ACTUALIZADO: 4 nuevas rutas agregadas
```

---

## 🔌 Integración con Backend

Para activar las funcionalidades completas (sin demo data):

### 1. Text Search
```python
# backend/src/api/main.py
@app.post("/text_search")
async def text_search(query: str, top_k: int = 10, method: str = "both"):
    # Implementar búsqueda TF-IDF y/o Cosine Similarity
    pass
```

### 2. Multimedia Search
```python
@app.post("/multimedia_search")
async def multimedia_search(file: UploadFile, type: str = "image"):
    # Implementar búsqueda de similitud (embeddings)
    pass
```

### 3. Performance Benchmark
```python
@app.post("/upload_benchmark")
async def upload_benchmark(file: UploadFile, type: str = "text"):
    # Parsear JSON/CSV con datos de benchmark
    pass
```

---

## 🚀 Primeros Pasos

1. **Navega a cualquiera de las nuevas pestañas** desde el sidebar
2. **Demo Mode:** Todas las vistas funcionan sin backend (muestran datos de ejemplo)
3. **Conexión al Backend:** Los endpoints esperados están documentados arriba
4. **Personalización:** Edita los componentes para adaptar colores, campos o lógica

---

## ✅ Checklist de Cumplimiento

- [x] 4 nuevas vistas creadas (Text Search, Multimedia Search, Performance, Help)
- [x] Componentes con UI consistente con dashboard
- [x] Uso de TailwindCSS y modo oscuro
- [x] Tarjetas glass-morphism con sombras suaves
- [x] Gráficas con Recharts (Performance)
- [x] Tabla de resultados con estilos (Text Search)
- [x] Grid de tarjetas (Multimedia Search)
- [x] Upload de archivos (Multimedia, Benchmark)
- [x] Tabs reutilizables (Performance, Help)
- [x] Integración en Sidebar con iconos
- [x] Rutas en Next.js (`app/` layout)
- [x] Componentes reutilizables (Card, Button, Table, etc.)
- [x] Placeholders y demo data
- [x] Responsivo (mobile-first)
- [x] Animaciones suaves

---

## 📞 Soporte

Para preguntas o cambios:
- Revisa el componente Help (/help)
- Consulta el README principal del proyecto
- Abre un issue en GitHub
