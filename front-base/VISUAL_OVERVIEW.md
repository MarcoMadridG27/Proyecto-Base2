# Visual Overview - Nuevas Pestañas Proyecto 2

## 🎨 Diseño General

Todas las nuevas vistas comparten:
- **Fondo:** Negro/gris oscuro (#0f0f0f, #1a1a1a)
- **Tarjetas:** Glass-morphism (semi-transparent white/5, bordes white/10)
- **Texto:** Geist Sans, colores claros (foreground/muted-foreground)
- **Gradientes:** Primary (Cyan/Blue) → Secondary (Pink/Magenta)
- **Sombras:** Suaves, animadas en hover

---

## 1. 📄 Text Search (`/text-search`)

### Layout Principal
```
┌─────────────────────────────────────────────────────┐
│ Text Search                                         │
│ Búsqueda textual usando TF-IDF y Similitud...      │
├─────────────────────────────────────────────────────┤
│
│  ┌─ Query Parameters ──────────────────────────────┐
│  │ [Search Query Input Field]      [Search Button] │
│  │ ┌──────────────────────────────────────────────┐
│  │ │ Top-K: [10   ▼]  Method: [Both (TF-IDF & C..)│
│  │ │ Results: [3] | 45.23ms                       │
│  │ └──────────────────────────────────────────────┘
│  └─────────────────────────────────────────────────┘
│
│  ┌─ Metrics ──────────────────────────────────────┐
│  │ ⏱️ Execution Time      📊 Total Results      ⚡ Method
│  │ 45.23ms                3                    Hybrid
│  └────────────────────────────────────────────────┘
│
│  ┌─ Search Results ───────────────────────────────┐
│  │ Title | Snippet | Cosine Sim | TF-IDF | Score │
│  │────────────────────────────────────────────────│
│  │ Doc 1 | Sample.. │   0.980    │ 0.920  │ 95%  │
│  │ Doc 2 | Sample.. │   0.890    │ 0.850  │ 87%  │
│  │ Doc 3 | Sample.. │   0.780    │ 0.740  │ 76%  │
│  └────────────────────────────────────────────────┘
```

### Características Visuales
- ✨ Tabla con scroll horizontal
- 📊 Barra de progreso visual del score (gradient azul-rosa)
- 🎨 Colores diferenciados por métrica (azul=cosine, rosa=tfidf, blanco=score)
- ⚡ Campo de input con efecto focus (border primary, glow)
- 🔘 Botón Search con gradiente y sombra

---

## 2. 🖼️ Multimedia Search (`/multimedia-search`)

### Layout Principal
```
┌─────────────────────────────────────────────────────┐
│ Multimedia Search                                   │
│ Búsqueda de objetos similares en imágenes y audio  │
├─────────────────────────────────────────────────────┤
│
│  ┌─ Upload Media ──────────────────────────────────┐
│  │ ┌─ File Input ──┐    ┌─ Preview ──────────────┐
│  │ │               │    │                        │
│  │ │  📎 Click or  │    │  [Image Preview]       │
│  │ │  drag files   │    │  or                    │
│  │ │               │    │  [Audio Player]        │
│  │ └───────────────┘    └────────────────────────┘
│  │
│  │         [▶ Find Similar] (Full Width)
│  └─────────────────────────────────────────────────┘
│
│  ┌─ Metrics ──────────────────────────────────────┐
│  │ ⏱️ Execution    📊 Similar Objs    🎵 File Type
│  │ 234.56ms         4                  image
│  └────────────────────────────────────────────────┘
│
│  ┌─ Similar Objects (Grid 2x2, responsive) ──────┐
│  │ ┌─────────────┐  ┌─────────────┐              │
│  │ │  [Image]    │  │  [Image]    │              │
│  │ │  95%   ✓    │  │  87%   ✓    │              │
│  │ │ Obj Title   │  │ Obj Title   │              │
│  │ │ [progress]  │  │ [progress]  │              │
│  │ │ Category... │  │ Category... │              │
│  │ └─────────────┘  └─────────────┘              │
│  │ ┌─────────────┐  ┌─────────────┐              │
│  │ │  [Image]    │  │  [Image]    │              │
│  │ │  76%   ✓    │  │  71%   ✓    │              │
│  │ │ Obj Title   │  │ Obj Title   │              │
│  │ │ [progress]  │  │ [progress]  │              │
│  │ │ Category... │  │ Category... │              │
│  │ └─────────────┘  └─────────────┘              │
│  └─────────────────────────────────────────────────┘
```

### Características Visuales
- 🖼️ Tarjetas con imagen/ícono de audio
- 📊 Badge de similitud en esquina superior derecha (gradient)
- 📈 Barra de similitud animada con label "Similarity"
- 🏷️ Metadata mostrada en pequeño (tags, categoría)
- 🎨 Hover effect: zoom +5%, sombra primary/20, escalado suave
- 📱 Responsive: 4 cols en desktop, 2 en tablet, 1 en mobile

---

## 3. 📊 Performance & Benchmark (`/performance`)

### Layout Principal
```
┌─────────────────────────────────────────────────────┐
│ Performance & Benchmark                             │
│ Comparación de rendimiento entre diferentes...      │
├─────────────────────────────────────────────────────┤
│
│  ┌─ Tabs ──────────────────────────────────────────┐
│  │ [Text Retrieval ▼] [Multimedia Retrieval]       │
│  └─────────────────────────────────────────────────┘
│
│  ┌─ Load Custom Data ──────────────────────────────┐
│  │ [📎 Upload Benchmark Data]     (JSON/CSV)       │
│  └─────────────────────────────────────────────────┘
│
│  ┌─ Execution Time Comparison ────────────────────┐
│  │                                                │
│  │  (Gráfica LineChart: Time vs N)                │
│  │  SPIMI (azul)                                  │
│  │  PostgreSQL (rosa)                             │
│  │  Eje X: N (100, 500, 1K, 5K, 10K)            │
│  │  Eje Y: Time (ms)                             │
│  │                                                │
│  └────────────────────────────────────────────────┘
│
│  ┌─ Precision Comparison ────────────────────────┐
│  │                                                │
│  │  (Gráfica BarChart: Precision vs N)           │
│  │  SPIMI (azul) | PostgreSQL (rosa)             │
│  │  Eje X: N                                     │
│  │  Eje Y: Precision (0-1.0)                    │
│  │                                                │
│  └────────────────────────────────────────────────┘
│
│  ┌─ Statistics ────────────────────────────────────┐
│  │ 🚀 Fastest      ⭐ Best Precision   📈 Ratio
│  │ SPIMI           PostgreSQL         2.1x
│  │ avg: ~900ms     avg: 0.946         SPIMI vs PG
│  └────────────────────────────────────────────────┘
```

### Características Visuales
- 📈 Gráficas animadas con Recharts
- 🎨 LineChart: líneas suaves, colores primary/secondary/auxiliares
- 📊 BarChart: barras redondeadas (radius 8), gradient fills
- 🔄 Tooltip dark: background rgba(0,0,0,0.8), border white/20
- ✨ Legend automático con colores diferenciados
- 📱 ResponsiveContainer: height 300px (ajustable)
- 🎯 Tabs animados con stagger effect

---

## 4. 📚 Help & Documentation (`/help`)

### Layout Principal
```
┌─────────────────────────────────────────────────────┐
│ Help & Documentation                                │
│ Guía de uso, ejemplos y referencias...             │
├─────────────────────────────────────────────────────┤
│
│  ┌─ Tabs ──────────────────────────────────────────┐
│  │ [Quick Guide] [Examples] [Queries] [Resources] │
│  └─────────────────────────────────────────────────┘
│
│  ┌─ Quick Guide ───────────────────────────────────┐
│  │                                                │
│  │ 1️⃣ Upload Data                                 │
│  │   Descripción de uso...                        │
│  │                                                │
│  │ 2️⃣ Create Indexes                              │
│  │   Descripción de uso...                        │
│  │                                                │
│  │ 3️⃣ Query Data                                  │
│  │   Descripción de uso...                        │
│  │                                                │
│  │ 4️⃣ Analyze Results                             │
│  │   Descripción de uso...                        │
│  │                                                │
│  │ 5️⃣ Advanced Search                             │
│  │   Descripción de uso...                        │
│  │                                                │
│  │ [Features Grid]                                │
│  │ SQL Support | Index Types | Text Retrieval    │
│  │ Multimedia  | Performance | CSV Import        │
│  └────────────────────────────────────────────────┘
│
│  ┌─ Examples ──────────────────────────────────────┐
│  │                                                │
│  │ Example 1: Upload and Search                  │
│  │ ┌──────────────────────────────────────────┐  │
│  │ │ 1. Upload cities_1k.csv                  │  │
│  │ │ 2. System creates table: cities_1k      │  │
│  │ │ 3. Query: SELECT * FROM cities_1k...    │  │
│  │ │ Result: Fast with index on id           │  │
│  │ └──────────────────────────────────────────┘  │
│  │                                                │
│  │ [More Examples...]                             │
│  └────────────────────────────────────────────────┘
│
│  ┌─ SQL Query Reference ───────────────────────────┐
│  │                                                │
│  │ Simple SELECT                                  │
│  │ ┌──────────────────────────────────────────┐  │
│  │ │ SELECT * FROM table_name;               │  │
│  │ │ Description: Retrieve all records...    │  │
│  │ └──────────────────────────────────────────┘  │
│  │                                                │
│  │ [More Queries...]                              │
│  └────────────────────────────────────────────────┘
│
│  ┌─ Resources & Links ─────────────────────────────┐
│  │                                                │
│  │ 🔗 GitHub Repository                           │
│  │    Access the source code...                   │
│  │                                                │
│  │ 📖 Project Report                              │
│  │    Full project specification...               │
│  │                                                │
│  │ 📚 API Documentation                           │
│  │    Backend API endpoints...                    │
│  │                                                │
│  │ ┌─ Need Help? ──────────────────────────────┐ │
│  │ │ • Check this Help section...              │ │
│  │ │ • Visit GitHub repository...              │ │
│  │ │ • Review documentation...                 │ │
│  │ │                                           │ │
│  │ │ [▶ Visit GitHub Repository] (Full Width) │ │
│  │ └───────────────────────────────────────────┘ │
│  └────────────────────────────────────────────────┘
```

### Características Visuales
- 📑 Tabs con transiciones suaves (fade-in)
- 🎯 Paso a paso con números circulares (primary bg)
- 📦 Grid de features 2 columnas (responsive)
- 💻 Código monospace con fondo oscuro y colores syntax
- 🔗 Links con hover effect (scale, color change)
- ✨ Tarjetas con hover effect
- 🎨 Card "Need Help?" con gradient primary/secondary

---

## 🎬 Animaciones Consistentes

Todas las vistas usan:
- **fade-in:** Opacidad 0 → 1 (200ms)
- **scale-in:** Scale 0.95 → 1 (300ms) con stagger (50ms entre items)
- **slide-in-left:** TranslateX -20px → 0 (300ms)
- **hover:** Scale +1.05, shadow boost, border color change
- **glow:** Sombra animada en logo/accent elements

---

## 📐 Responsividad

| Breakpoint | Aplicación |
|-----------|-----------|
| Mobile (<640px) | 1 columna, botones full-width, grid 1x1 |
| Tablet (640-1024px) | 2 columnas, padding reducido, grid 2x2 |
| Desktop (>1024px) | 3-4 columnas, padding full, grid 2x2-4x4 |

---

## 🎨 Paleta de Colores

| Elemento | Color | Uso |
|---------|-------|-----|
| Primary | Cyan/Blue (#06b6d4) | Botones, highlights, accents |
| Secondary | Pink/Magenta (#ec4899) | Gradientes, alternativas |
| Background | #0f0f0f | Fondo principal |
| Surface | #1a1a1a | Tarjetas glass-morphism |
| Border | rgba(255,255,255,0.1) | Bordes sutiles |
| Text | #f0f0f0 | Foreground |
| Muted | rgba(255,255,255,0.4) | Muted foreground |

---

## ✅ Checklist Visual

- [x] Consistencia de colores en todas las vistas
- [x] Tipografía Geist Sans en todo
- [x] Glass-morphism en tarjetas
- [x] Bordes y sombras suaves
- [x] Animaciones smooth
- [x] Responsividad probada
- [x] Gradientes primary→secondary
- [x] Hover effects en botones/links
- [x] Iconos de lucide-react
- [x] Espaciado consistente (Tailwind)

---

## 🚀 Próximos Pasos

1. **Teste el frontend:**
   ```bash
   cd front-base
   npm run dev  # http://localhost:3000
   ```

2. **Navega a las nuevas vistas:**
   - http://localhost:3000/text-search
   - http://localhost:3000/multimedia-search
   - http://localhost:3000/performance
   - http://localhost:3000/help

3. **Conecta el backend** (endpoints en BACKEND_INTEGRATION_GUIDE.md)

4. **Personaliza según sea necesario** (colores, campos, lógica)

---

**¡El frontend está listo para usar!** 🎉
