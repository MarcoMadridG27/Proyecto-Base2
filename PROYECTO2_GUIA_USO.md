# Proyecto 2 - Sistema de Búsqueda Completo

## 📋 Resumen de Implementación

### ✅ **COMPLETADO (100%)**

#### 1. Backend - Búsqueda Textual
- ✅ **Preprocesamiento**: Tokenización, stopwords, stemming (NLTK)
- ✅ **SPIMI**: Construcción bloques, merge, TF-IDF, norma
- ✅ **Consulta**: Preprocesar query, TF-IDF, cosine similarity, Top-K
- ✅ **PostgreSQL**: Integración con tsvector/tsquery, ts_rank
- ✅ **Endpoints API**:
  - `POST /text/build_index` - Construir índice desde CSV
  - `POST /text/search` - Búsqueda con índice custom
  - `POST /text/postgres/setup` - Configurar PostgreSQL
  - `POST /text/postgres/load_data` - Cargar datos en PostgreSQL
  - `POST /text/postgres/search` - Búsqueda con PostgreSQL
  - `POST /text/compare` - Comparar ambos métodos

#### 2. Backend - Búsqueda Multimedia
- ✅ **Extracción Características**: SIFT para imágenes, MFCC para audio
- ✅ **Codebook**: K-Means, Visual Words, TF-IDF
- ✅ **KNN Secuencial**: Distancia euclidiana, Top-K con heap
- ✅ **KNN Indexado**: Índice invertido visual, búsqueda eficiente
- ✅ **Endpoints API**:
  - `POST /multimedia/build_index` - Construir índice desde ZIP
  - `POST /multimedia/search` - Búsqueda con KNN secuencial
  - `POST /multimedia/compare_methods` - Comparar secuencial vs indexado

#### 3. Frontend
- ✅ **Búsqueda Textual**: Interfaz completa con tabs (Search, Upload)
- ✅ **Búsqueda Multimedia**: Interfaz completa con tabs (Search, Build Index)
- ✅ **Visualización**: Resultados, métricas, tiempos de ejecución

---

## 🚀 Guía de Uso

### Requisitos Previos

1. **Python 3.8+** instalado
2. **Node.js 18+** instalado
3. **PostgreSQL 14+** instalado (opcional, para comparación)

### Instalación

#### 1. Backend

```bash
cd core
pip install -r requirements.txt

# Descargar datos de NLTK (solo primera vez)
python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt')"
```

#### 2. Frontend

```bash
cd front-base
npm install
```

#### 3. PostgreSQL (Opcional)

```bash
# Crear base de datos
createdb proyecto_bd2

# O usando psql
psql -U postgres
CREATE DATABASE proyecto_bd2;
\q
```

### Ejecución

#### 1. Iniciar Backend

```bash
cd core
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

El backend estará disponible en: `http://localhost:8000`
Documentación API: `http://localhost:8000/docs`

#### 2. Iniciar Frontend

```bash
cd front-base
npm run dev
```

El frontend estará disponible en: `http://localhost:3000`

---

## 📖 Uso del Sistema

### Búsqueda Textual

#### Opción A: Usando Índice Custom (SPIMI)

1. **Preparar datos**: CSV con columnas `doc_id` y `text`
   ```csv
   doc_id,text
   1,"Machine learning is a subset of artificial intelligence"
   2,"Deep learning uses neural networks with multiple layers"
   ```

2. **Construir índice**:
   - Ir a `http://localhost:3000/text-search`
   - Pestaña "Upload & Index"
   - Seleccionar archivo CSV
   - Click "Build Index"

3. **Buscar**:
   - Pestaña "Search"
   - Ingresar query: "machine learning"
   - Click "Search"

#### Opción B: Comparar con PostgreSQL

1. **Configurar PostgreSQL**:
   ```bash
   # Usando curl o Postman
   curl -X POST http://localhost:8000/text/postgres/setup \
     -F "host=localhost" \
     -F "database=proyecto_bd2" \
     -F "user=postgres" \
     -F "password=tu_password" \
     -F "port=5432"
   ```

2. **Cargar datos**:
   ```bash
   curl -X POST http://localhost:8000/text/postgres/load_data \
     -F "file=@documents.csv"
   ```

3. **Comparar métodos**:
   ```bash
   curl -X POST http://localhost:8000/text/compare \
     -H "Content-Type: application/json" \
     -d '{"query": "machine learning", "top_k": 10}'
   ```

### Búsqueda Multimedia

#### 1. Construir Índice

1. **Preparar imágenes**: Crear un ZIP con imágenes
   ```
   images.zip
   ├── img1.jpg
   ├── img2.png
   └── img3.jpeg
   ```

2. **Construir índice**:
   - Ir a `http://localhost:3000/multimedia-search`
   - Pestaña "Build Index"
   - Seleccionar ZIP
   - Configurar:
     - Index Name: "my_index"
     - Vocabulary Size (K): 100
   - Click "Build Index"

#### 2. Buscar Imágenes Similares

1. **Buscar**:
   - Pestaña "Search"
   - Subir imagen de consulta
   - Configurar Top-K
   - Click "Find Similar"

2. **Ver resultados**: Se mostrarán las imágenes más similares con scores

#### 3. Buscar Audios Similares

**Preparación de Audios**:

1. **Formatos soportados**:
   - `.wav` (recomendado)
   - `.mp3`
   - `.flac`
   - `.ogg`
   - `.m4a`

2. **Crear ZIP con audios**:
   ```
   audios.zip
   ├── song1.wav
   ├── song2.mp3
   ├── ambient/
   │   ├── rain.wav
   │   └── ocean.wav
   └── speech/
       ├── voice1.wav
       └── voice2.wav
   ```

**Construir Índice de Audio**:

1. **Ir a Multimedia Search**:
   - Navegar a `http://localhost:3000/multimedia-search`
   - Pestaña "Build Index"

2. **Configurar parámetros**:
   - **Index Name**: `audio_index`
   - **Vocabulary Size (K)**: 150-200 (recomendado para audio)
   - **Seleccionar ZIP**: Subir archivo con audios

3. **Build Index**: Click en "Build Index"
   - El sistema detectará automáticamente que son archivos de audio
   - Extraerá características MFCC (Mel-Frequency Cepstral Coefficients)
   - Creará un vocabulario acústico usando K-Means
   - Construirá el índice invertido

**Buscar Audio Similar**:

1. **Pestaña "Search"**:
   - Subir un archivo de audio como consulta (puede ser del índice o uno nuevo)
   - Configurar Top-K (ej: 5)
   - Click "Find Similar"

2. **Resultados**:
   - Se mostrarán los audios más similares
   - Cada resultado tendrá un reproductor de audio
   - Porcentaje de similitud
   - Nombre del archivo

**Ejemplo con cURL**:

```bash
# Construir índice de audio
curl -X POST http://localhost:8000/multimedia/build_index \
  -F "file=@audios.zip" \
  -F "index_name=audio_index" \
  -F "k=150"

# Buscar audio similar
curl -X POST http://localhost:8000/multimedia/search \
  -F "file=@query_audio.wav" \
  -F "index_name=audio_index" \
  -F "top_k=5"
```

**Características de Audio Extraídas (MFCC)**:
- **13 coeficientes MFCC** por frame
- Captura características del espectro de frecuencia
- Invariante a volumen y tono (parcialmente)
- Ideal para:
  - Búsqueda de canciones similares
  - Reconocimiento de voz
  - Clasificación de sonidos ambientales
  - Detección de música similar

**Tips para Mejores Resultados**:
- ✅ Usa archivos `.wav` sin comprimir para mejor calidad
- ✅ Audios de duración similar (ej: todos 30 segundos)
- ✅ K=150-200 para vocabulario acústico (más que para imágenes)
- ✅ Normaliza el volumen de los audios antes de indexar
- ⚠️ Audios muy cortos (<1 segundo) pueden dar resultados inconsistentes
- ⚠️ Audios muy largos (>5 minutos) tardarán más en procesarse

#### 4. Comparar Métodos (Imágenes o Audio)

```bash
# Comparar KNN Secuencial vs Indexado
curl -X POST http://localhost:8000/multimedia/compare_methods \
  -F "file=@query_image.jpg" \
  -F "top_k=5" \
  -F "index_name=my_index"
```

---

## 🧪 Experimentos

### 1. Comparación Búsqueda Textual

**Script de prueba**:

```python
import requests
import time
import matplotlib.pyplot as plt

# Queries de prueba
queries = [
    "machine learning",
    "neural networks deep learning",
    "artificial intelligence algorithms"
]

# Comparar tiempos
custom_times = []
postgres_times = []

for query in queries:
    # Custom index
    response = requests.post("http://localhost:8000/text/search", 
                            json={"query": query, "top_k": 10})
    custom_times.append(response.json()["search_time_seconds"])
    
    # PostgreSQL
    response = requests.post("http://localhost:8000/text/postgres/search",
                            json={"query": query, "top_k": 10})
    postgres_times.append(response.json()["search_time_seconds"])

# Graficar
plt.figure(figsize=(10, 6))
x = range(len(queries))
plt.bar([i-0.2 for i in x], custom_times, width=0.4, label='Custom Index', color='blue')
plt.bar([i+0.2 for i in x], postgres_times, width=0.4, label='PostgreSQL', color='green')
plt.xlabel('Query')
plt.ylabel('Time (seconds)')
plt.title('Text Search Performance Comparison')
plt.xticks(x, [f'Q{i+1}' for i in x])
plt.legend()
plt.savefig('text_search_comparison.png')
plt.show()
```

### 2. Comparación Búsqueda Multimedia

**Script de prueba**:

```python
import requests
import matplotlib.pyplot as plt

# Imágenes de prueba
test_images = ['query1.jpg', 'query2.jpg', 'query3.jpg']

seq_times = []
indexed_times = []

for img_path in test_images:
    with open(img_path, 'rb') as f:
        files = {'file': f}
        data = {'top_k': 5, 'index_name': 'default'}
        
        response = requests.post("http://localhost:8000/multimedia/compare_methods",
                                files=files, data=data)
        result = response.json()
        
        seq_times.append(result["sequential"]["time_seconds"])
        indexed_times.append(result["indexed"]["time_seconds"])

# Graficar
plt.figure(figsize=(10, 6))
x = range(len(test_images))
plt.bar([i-0.2 for i in x], seq_times, width=0.4, label='Sequential KNN', color='orange')
plt.bar([i+0.2 for i in x], indexed_times, width=0.4, label='Inverted Index', color='purple')
plt.xlabel('Query Image')
plt.ylabel('Time (seconds)')
plt.title('Multimedia Search Performance Comparison')
plt.xticks(x, [f'Img{i+1}' for i in x])
plt.legend()
plt.savefig('multimedia_search_comparison.png')
plt.show()
```

### 3. Experimentos con Audio

**Script de prueba para búsqueda de audio**:

```python
import requests
import matplotlib.pyplot as plt
import numpy as np

# Construir índice de audio
print("Construyendo índice de audio...")
with open('audios.zip', 'rb') as f:
    files = {'file': f}
    data = {'index_name': 'audio_test', 'k': 150}
    response = requests.post("http://localhost:8000/multimedia/build_index",
                            files=files, data=data)
    print(response.json())

# Audios de prueba
test_audios = ['query1.wav', 'query2.wav', 'query3.wav']
results = []

for audio_path in test_audios:
    with open(audio_path, 'rb') as f:
        files = {'file': f}
        data = {'top_k': 5, 'index_name': 'audio_test'}
        
        # Comparar métodos
        response = requests.post("http://localhost:8000/multimedia/compare_methods",
                                files=files, data=data)
        result = response.json()
        
        results.append({
            'query': audio_path,
            'seq_time': result["sequential"]["time_seconds"],
            'idx_time': result["indexed"]["time_seconds"],
            'speedup': result["speedup"],
            'top_result_sim': result["indexed"]["results"][0]["similarity"]
        })

# Visualizar resultados
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

# Gráfico 1: Comparación de tiempos
queries = [r['query'] for r in results]
seq_times = [r['seq_time'] for r in results]
idx_times = [r['idx_time'] for r in results]

x = np.arange(len(queries))
width = 0.35

ax1.bar(x - width/2, seq_times, width, label='Sequential', color='coral')
ax1.bar(x + width/2, idx_times, width, label='Indexed', color='teal')
ax1.set_xlabel('Query Audio')
ax1.set_ylabel('Time (seconds)')
ax1.set_title('Audio Search Performance')
ax1.set_xticks(x)
ax1.set_xticklabels([f'Q{i+1}' for i in range(len(queries))])
ax1.legend()
ax1.grid(True, alpha=0.3)

# Gráfico 2: Speedup
speedups = [r['speedup'] for r in results]
ax2.bar(x, speedups, color='purple', alpha=0.7)
ax2.set_xlabel('Query Audio')
ax2.set_ylabel('Speedup (x times faster)')
ax2.set_title('Indexing Speedup')
ax2.set_xticks(x)
ax2.set_xticklabels([f'Q{i+1}' for i in range(len(queries))])
ax2.axhline(y=1, color='red', linestyle='--', label='No improvement')
ax2.legend()
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('audio_search_analysis.png', dpi=300)
plt.show()

# Imprimir estadísticas
print("\n=== Estadísticas de Búsqueda de Audio ===")
print(f"Tiempo promedio secuencial: {np.mean(seq_times):.4f}s")
print(f"Tiempo promedio indexado: {np.mean(idx_times):.4f}s")
print(f"Speedup promedio: {np.mean(speedups):.2f}x")
print(f"Similitud promedio del top result: {np.mean([r['top_result_sim'] for r in results]):.2%}")
```

**Análisis de Calidad de Resultados**:

```python
import requests
import pandas as pd

# Evaluar precisión de búsqueda
def evaluate_audio_search(ground_truth_pairs):
    """
    ground_truth_pairs: lista de tuplas (query_audio, expected_similar_audio)
    """
    results = []
    
    for query, expected in ground_truth_pairs:
        with open(query, 'rb') as f:
            files = {'file': f}
            data = {'top_k': 10, 'index_name': 'audio_test'}
            
            response = requests.post("http://localhost:8000/multimedia/search",
                                    files=files, data=data)
            search_results = response.json()['results']
            
            # Verificar si el audio esperado está en top-K
            found_rank = None
            for i, result in enumerate(search_results):
                if expected in result['filename']:
                    found_rank = i + 1
                    break
            
            results.append({
                'query': query,
                'expected': expected,
                'found_rank': found_rank,
                'found': found_rank is not None,
                'top_similarity': search_results[0]['similarity'] if search_results else 0
            })
    
    # Calcular métricas
    df = pd.DataFrame(results)
    precision_at_1 = df[df['found_rank'] == 1].shape[0] / len(df)
    precision_at_5 = df[df['found_rank'] <= 5].shape[0] / len(df)
    precision_at_10 = df['found'].sum() / len(df)
    
    print("\n=== Métricas de Precisión ===")
    print(f"Precision@1: {precision_at_1:.2%}")
    print(f"Precision@5: {precision_at_5:.2%}")
    print(f"Precision@10: {precision_at_10:.2%}")
    print(f"\nPromedio de similitud del top-1: {df['top_similarity'].mean():.2%}")
    
    return df

# Ejemplo de uso
ground_truth = [
    ('query_song1.wav', 'song1.wav'),
    ('query_voice1.wav', 'voice1.wav'),
    ('query_rain.wav', 'rain.wav'),
]

results_df = evaluate_audio_search(ground_truth)
print("\nResultados detallados:")
print(results_df)
```

---

## 📊 Estructura del Proyecto

```
proyecto-base4/
├── core/                           # Backend
│   ├── src/
│   │   ├── api/
│   │   │   ├── main.py            # FastAPI app principal
│   │   │   ├── text_search_routes.py    # Endpoints text search
│   │   │   └── multimedia_routes.py     # Endpoints multimedia
│   │   ├── text_search/
│   │   │   ├── preprocessor.py    # Tokenización, stemming
│   │   │   ├── spimi_indexer.py   # SPIMI indexing
│   │   │   ├── query_processor.py # Query processing
│   │   │   └── postgres_search.py # PostgreSQL integration
│   │   └── multimedia_search/
│   │       ├── feature_extractor.py      # SIFT, MFCC
│   │       ├── codebook.py               # K-Means, BoW
│   │       ├── knn_index.py              # KNN secuencial
│   │       └── visual_inverted_index.py  # KNN indexado
│   ├── data/                      # Índices y datos
│   ├── requirements.txt
│   └── test_*.py                  # Scripts de prueba
│
└── front-base/                    # Frontend (Next.js)
    ├── app/
    │   ├── text-search/
    │   └── multimedia-search/
    └── components/
        ├── text-search.tsx
        └── multimedia-search.tsx
```

---

## 🎯 Características Implementadas

### Búsqueda Textual
- ✅ Preprocesamiento completo (NLTK)
- ✅ Índice invertido con SPIMI
- ✅ TF-IDF y cosine similarity
- ✅ Top-K eficiente
- ✅ Comparación con PostgreSQL (tsvector/tsquery)

### Búsqueda Multimedia
- ✅ Extracción SIFT (imágenes)
- ✅ Extracción MFCC (audio)
- ✅ Detección automática de tipo de archivo (imagen/audio)
- ✅ Bag of Visual/Acoustic Words con K-Means
- ✅ TF-IDF para histogramas
- ✅ Distancia Chi-Cuadrado para comparación de histogramas
- ✅ Normalización L1 para distribuciones de probabilidad
- ✅ KNN secuencial (fuerza bruta)
- ✅ KNN indexado (índice invertido visual/acústico)
- ✅ Comparación de métodos
- ✅ Soporte para subdirectorios en ZIP
- ✅ Reproductores de audio en resultados

### Frontend
- ✅ Interfaz moderna y responsiva
- ✅ Visualización de resultados
- ✅ Métricas de rendimiento
- ✅ Carga de archivos (CSV, ZIP)

---

## 📝 Notas Importantes

1. **PostgreSQL es opcional**: El sistema funciona completamente sin PostgreSQL. Solo se necesita para comparaciones.

2. **Datos de prueba**: Puedes generar datos sintéticos con los scripts en `core/test_*.py`

3. **Rendimiento**: Los tiempos dependen del tamaño del dataset y la configuración de hardware.

4. **Vocabulario (K)**: Para multimedia, K=100 es un buen punto de partida. Aumentar K mejora precisión pero aumenta tiempo de construcción.

---

## 🐛 Troubleshooting

### Error: "PostgreSQL connection failed"
- Verificar que PostgreSQL esté corriendo
- Verificar credenciales en `/text/postgres/setup`

### Error: "No module named 'cv2'"
```bash
pip install opencv-python-headless
```

### Error: "NLTK data not found"
```python
import nltk
nltk.download('stopwords')
nltk.download('punkt')
```

### Frontend no conecta con backend
- Verificar que backend esté en puerto 8000
- Verificar CORS en `main.py`

---

## 📚 Referencias

- **SPIMI**: Single-Pass In-Memory Indexing
- **TF-IDF**: Term Frequency-Inverse Document Frequency
- **BoW**: Bag of Visual Words
- **SIFT**: Scale-Invariant Feature Transform
- **PostgreSQL Full-Text Search**: https://www.postgresql.org/docs/current/textsearch.html

---

## ✅ Checklist de Implementación

- [x] Preprocesamiento de texto
- [x] SPIMI indexing
- [x] Query processing con TF-IDF
- [x] PostgreSQL integration
- [x] Extracción de características multimedia
- [x] Codebook con K-Means
- [x] KNN secuencial
- [x] KNN indexado (inverted index)
- [x] API REST completa
- [x] Frontend completo
- [x] Comparación de métodos
- [ ] Experimentos (pendiente - usuario)
- [ ] Informe final (pendiente - usuario)

---

**Proyecto completado al 100% de funcionalidad requerida.**
**Listo para experimentos y redacción de informe.**
