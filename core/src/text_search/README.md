# Módulo de Búsqueda Textual - Índice Invertido con SPIMI

## 📚 Descripción

Este módulo implementa un sistema completo de búsqueda textual utilizando un **índice invertido** construido con el algoritmo **SPIMI** (Single-Pass In-Memory Indexing). El sistema incluye preprocesamiento de texto, cálculo de TF-IDF y ranking por similitud coseno.

## 🏗️ Arquitectura

```
src/text_search/
├── __init__.py
├── preprocessor.py      # Preprocesamiento de texto
├── spimi_indexer.py     # Construcción del índice invertido
└── query_processor.py   # Procesamiento de consultas
```

## 🔧 Componentes

### 1. TextPreprocessor (`preprocessor.py`)

Preprocesa texto aplicando:
- **Tokenización**: División en palabras
- **Normalización**: Minúsculas y eliminación de acentos
- **Stopwords**: Eliminación de palabras comunes
- **Stemming**: Reducción a raíz (usando Porter Stemmer)

**Ejemplo:**
```python
from src.text_search.preprocessor import TextPreprocessor

preprocessor = TextPreprocessor(language='english', use_stemming=True)
tokens = preprocessor.preprocess("The quick brown foxes are running!")
# Output: ['quick', 'brown', 'fox', 'run']
```

### 2. SPIMIIndexer (`spimi_indexer.py`)

Construye el índice invertido usando SPIMI:
- Procesa documentos en bloques
- Escribe bloques parciales a disco
- Merge de bloques
- Cálculo de TF-IDF
- Cálculo de normas de documentos

**Ejemplo:**
```python
from src.text_search.spimi_indexer import SPIMIIndexer

documents = [
    (1, "The quick brown fox jumps over the lazy dog"),
    (2, "A quick brown dog outpaces a quick fox"),
    # ...
]

indexer = SPIMIIndexer(index_dir="data/my_index", block_size=1000)
indexer.build_index(documents)
indexer.save_index()
```

### 3. QueryProcessor (`query_processor.py`)

Procesa consultas y retorna resultados rankeados:
- Preprocesa query
- Calcula TF-IDF de la query
- Calcula similitud coseno
- Retorna Top-K resultados

**Ejemplo:**
```python
from src.text_search.query_processor import QueryProcessor

query_processor = QueryProcessor(indexer)
results = query_processor.search("quick brown fox", top_k=10)

for doc_id, score in results:
    print(f"Doc {doc_id}: {score:.4f}")
```

## 📡 API Endpoints

### 1. Construir Índice desde JSON

```http
POST /text_search/build_index
Content-Type: application/json

{
  "documents": [
    {"doc_id": 1, "text": "The quick brown fox..."},
    {"doc_id": 2, "text": "Another document..."}
  ],
  "index_name": "my_index"
}
```

### 2. Construir Índice desde CSV

```http
POST /text_search/upload_documents
Content-Type: multipart/form-data

file: documents.csv
index_name: my_index
text_column: text
id_column: id
```

### 3. Buscar Documentos

```http
POST /text_search/search
Content-Type: application/json

{
  "query": "quick brown fox",
  "top_k": 10
}
```

**Respuesta:**
```json
{
  "ok": true,
  "query": "quick brown fox",
  "results": [
    {"doc_id": 1, "score": 0.8523, "rank": 1},
    {"doc_id": 5, "score": 0.6234, "rank": 2}
  ],
  "search_time_seconds": 0.0023,
  "num_results": 2
}
```

### 4. Cargar Índice Existente

```http
GET /text_search/load_index?index_name=my_index
```

### 5. Estadísticas del Índice

```http
GET /text_search/stats
```

## 🧪 Pruebas

Ejecutar el script de prueba:

```bash
cd core
python test_text_search.py
```

## 📊 Algoritmo SPIMI

### Construcción del Índice

1. **Dividir documentos en bloques** (block_size)
2. Para cada bloque:
   - Construir índice parcial en memoria
   - Escribir bloque a disco
3. **Merge de bloques** en índice final
4. **Calcular TF-IDF**:
   - TF = 1 + log(term_frequency)
   - IDF = log(N / document_frequency)
   - TF-IDF = TF × IDF
5. **Calcular normas** de documentos para similitud coseno

### Búsqueda

1. **Preprocesar query** (mismos pasos que documentos)
2. **Calcular TF-IDF de query**
3. **Identificar documentos candidatos** (que contienen al menos un término)
4. **Calcular similitud coseno** para cada candidato:
   ```
   sim(q, d) = (q · d) / (||q|| × ||d||)
   ```
5. **Rankear y retornar Top-K**

## 🎯 Complejidad

| Operación | Complejidad |
|-----------|-------------|
| Build Index | O(N × L) |
| Search | O(V + C × log K) |

Donde:
- N = número de documentos
- L = longitud promedio de documento
- V = tamaño del vocabulario en la query
- C = número de documentos candidatos
- K = top-k resultados

## 📝 Ejemplo Completo

```python
# 1. Construir índice
from src.text_search.spimi_indexer import SPIMIIndexer

documents = [
    (1, "Machine learning is a subset of artificial intelligence"),
    (2, "Deep learning uses neural networks with multiple layers"),
    (3, "Natural language processing enables computers to understand text"),
    (4, "Computer vision allows machines to interpret visual information"),
    (5, "Reinforcement learning trains agents through trial and error")
]

indexer = SPIMIIndexer(index_dir="data/ai_index", block_size=2)
indexer.build_index(documents)
indexer.save_index()

# 2. Buscar
from src.text_search.query_processor import QueryProcessor

query_processor = QueryProcessor(indexer)
results = query_processor.search("machine learning neural networks", top_k=3)

for rank, (doc_id, score) in enumerate(results, 1):
    print(f"{rank}. Document {doc_id}: {score:.4f}")
```

## 🔜 Próximos Pasos

- [ ] Comparación con PostgreSQL (tsvector/tsquery)
- [ ] Frontend para búsqueda textual
- [ ] Experimentos de rendimiento
- [ ] Soporte para múltiples idiomas
- [ ] Búsqueda con operadores booleanos

## 📚 Referencias

- Manning, C. D., Raghavan, P., & Schütze, H. (2008). *Introduction to Information Retrieval*
- SPIMI Algorithm: Single-Pass In-Memory Indexing
- TF-IDF: Term Frequency - Inverse Document Frequency
- Cosine Similarity for document ranking
