# Backend Integration Guide - Proyecto 2 New Views

Este archivo proporciona ejemplos de endpoints backend necesarios para la integración completa de las nuevas vistas.

## 1. Text Search Endpoint

**Endpoint:** `POST /text_search`

```python
from fastapi import FastAPI, HTTPException
from typing import List, Dict, Any, Literal
import time

app = FastAPI()

@app.post("/text_search")
async def text_search(
    query: str,
    top_k: int = 10,
    method: Literal["tfidf", "cosine", "both"] = "both"
) -> Dict[str, Any]:
    """
    Búsqueda textual usando TF-IDF y/o Similitud de Coseno.
    
    Args:
        query: Texto a buscar (SQL o lenguaje natural)
        top_k: Número máximo de resultados (1-1000)
        method: Método de similitud a usar
        
    Returns:
        {
            "ok": True,
            "results": [
                {
                    "title": str,
                    "snippet": str,
                    "score": float,
                    "tfidf_score": float (opcional),
                    "cosine_similarity": float (opcional)
                },
                ...
            ],
            "metrics": {
                "execution_time": float,
                "total_results": int,
                "method": str
            }
        }
    """
    start_time = time.time()
    
    try:
        # Tu lógica de búsqueda aquí
        results = []
        
        # Ejemplo con datos reales:
        # if method in ["tfidf", "both"]:
        #     tfidf_results = search_tfidf(query, top_k)
        #     results.extend(tfidf_results)
        # if method in ["cosine", "both"]:
        #     cosine_results = search_cosine(query, top_k)
        #     results.extend(cosine_results)
        
        execution_time = time.time() - start_time
        
        return {
            "ok": True,
            "results": results,
            "metrics": {
                "execution_time": execution_time,
                "total_results": len(results),
                "method": method
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 2. Multimedia Search Endpoint

**Endpoint:** `POST /multimedia_search`

```python
from fastapi import FastAPI, UploadFile, File, Form
from typing import List, Dict, Any, Literal
import time

@app.post("/multimedia_search")
async def multimedia_search(
    file: UploadFile = File(...),
    type: Literal["image", "audio"] = "image"
) -> Dict[str, Any]:
    """
    Búsqueda de similitud para imágenes y audio.
    
    Args:
        file: Archivo a buscar (imagen o audio)
        type: Tipo de archivo
        
    Returns:
        {
            "ok": True,
            "results": [
                {
                    "id": str,
                    "title": str,
                    "thumbnail": str (opcional, path o base64),
                    "type": "image" | "audio",
                    "similarity_score": float (0-1),
                    "metadata": dict
                },
                ...
            ],
            "metrics": {
                "execution_time": float,
                "total_similar": int,
                "file_name": str
            }
        }
    """
    start_time = time.time()
    
    try:
        # Guardar archivo temporal
        contents = await file.read()
        
        # Tu lógica de búsqueda de similitud aquí
        # 1. Extraer embeddings del archivo subido
        # 2. Comparar con embeddings en base de datos
        # 3. Retornar Top-K resultados similares
        
        results = []
        
        # Ejemplo:
        # query_embedding = extract_embedding(contents, type)
        # similar_objects = find_similar(query_embedding, top_k=10)
        # results = format_results(similar_objects)
        
        execution_time = time.time() - start_time
        
        return {
            "ok": True,
            "results": results,
            "metrics": {
                "execution_time": execution_time,
                "total_similar": len(results),
                "file_name": file.filename
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 3. Upload Benchmark Data Endpoint

**Endpoint:** `POST /upload_benchmark`

```python
from fastapi import FastAPI, UploadFile, File, Form
import json
import csv
from typing import Dict, Any, List, Literal
from io import StringIO

@app.post("/upload_benchmark")
async def upload_benchmark(
    file: UploadFile = File(...),
    type: Literal["text", "multimedia"] = "text"
) -> Dict[str, Any]:
    """
    Carga datos de benchmark desde JSON o CSV.
    
    Args:
        file: Archivo JSON o CSV con datos de benchmark
        type: Tipo de benchmark ("text" o "multimedia")
        
    Expected JSON format:
        [
            {"n": 100, "time_spimi": 12, "time_postgresql": 25, 
             "precision_spimi": 0.92, "precision_postgresql": 0.95},
            ...
        ]
        
    Expected CSV format:
        n,time_spimi,time_postgresql,precision_spimi,precision_postgresql
        100,12,25,0.92,0.95
        500,45,89,0.93,0.94
        ...
        
    Returns:
        {
            "ok": True,
            "data": [
                {"n": int, "time_*": float, "precision_*": float},
                ...
            ]
        }
    """
    try:
        contents = await file.read()
        text_content = contents.decode("utf-8")
        
        data = []
        
        if file.filename.endswith(".json"):
            # Parse JSON
            data = json.loads(text_content)
            
        elif file.filename.endswith(".csv"):
            # Parse CSV
            reader = csv.DictReader(StringIO(text_content))
            for row in reader:
                # Convertir valores a números
                converted_row = {}
                for key, value in row.items():
                    try:
                        # Intentar float si tiene punto, si no int
                        converted_row[key] = float(value) if "." in value else int(value)
                    except ValueError:
                        converted_row[key] = value
                data.append(converted_row)
        else:
            raise ValueError("File must be JSON or CSV")
        
        # Validar estructura de datos
        if type == "text":
            # Esperamos campos: n, time_spimi, time_postgresql, precision_spimi, precision_postgresql
            expected_fields = ["n", "time_spimi", "time_postgresql", "precision_spimi", "precision_postgresql"]
        else:  # multimedia
            # Esperamos: n, time_knn_sequential, time_knn_indexed, time_pgvector, precision_*
            expected_fields = ["n", "time_knn_sequential", "time_knn_indexed", "time_pgvector"]
        
        # Validar que todos los registros tienen los campos esperados
        for record in data:
            for field in expected_fields:
                if field not in record:
                    raise ValueError(f"Missing field '{field}' in data")
        
        return {
            "ok": True,
            "data": data,
            "message": f"Loaded {len(data)} benchmark records"
        }
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## 4. Database Integration Examples

### Text Search Implementation

```python
# Pseudocódigo para implementación con TF-IDF
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def search_tfidf(query: str, documents: List[str], top_k: int = 10):
    """Buscar usando TF-IDF"""
    vectorizer = TfidfVectorizer()
    
    # Vectorizar documentos y query
    all_texts = documents + [query]
    tfidf_matrix = vectorizer.fit_transform(all_texts)
    
    # Calcular similitud del query vs documentos
    query_vector = tfidf_matrix[-1]
    doc_vectors = tfidf_matrix[:-1]
    
    similarities = cosine_similarity(query_vector, doc_vectors).flatten()
    
    # Obtener Top-K
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    results = []
    for idx in top_indices:
        results.append({
            "title": f"Document {idx}",
            "snippet": documents[idx][:100],
            "tfidf_score": float(similarities[idx]),
            "score": float(similarities[idx])
        })
    
    return results

def search_cosine(query: str, embeddings: List[List[float]], top_k: int = 10):
    """Buscar usando embeddings y similitud de coseno"""
    from sklearn.metrics.pairwise import cosine_similarity
    
    query_embedding = get_embedding(query)  # Tu modelo de embeddings
    
    similarities = cosine_similarity([query_embedding], embeddings).flatten()
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    results = []
    for idx in top_indices:
        results.append({
            "title": f"Document {idx}",
            "snippet": get_document_snippet(idx),
            "cosine_similarity": float(similarities[idx]),
            "score": float(similarities[idx])
        })
    
    return results
```

### Multimedia Search Implementation

```python
import numpy as np
from typing import List, Tuple

def extract_embedding(file_contents: bytes, type: str) -> np.ndarray:
    """Extraer embeddings de imagen o audio"""
    if type == "image":
        # Usar modelo de visión (CLIP, ResNet, etc.)
        from PIL import Image
        from io import BytesIO
        
        image = Image.open(BytesIO(file_contents))
        # embedding = vision_model.encode(image)
        
    else:  # audio
        # Usar modelo de audio (Wav2Vec, etc.)
        import librosa
        
        # embedding = audio_model.encode(audio_data)
    
    return embedding

def find_similar(query_embedding: np.ndarray, 
                 embeddings_db: List[Tuple[str, np.ndarray]], 
                 top_k: int = 10) -> List[Dict]:
    """Encontrar objetos similares usando búsqueda KNN"""
    from sklearn.metrics.pairwise import cosine_similarity
    
    similarities = []
    for obj_id, embedding in embeddings_db:
        sim = cosine_similarity([query_embedding], [embedding])[0][0]
        similarities.append((obj_id, sim))
    
    # Top-K
    similarities.sort(key=lambda x: x[1], reverse=True)
    top_results = similarities[:top_k]
    
    results = []
    for obj_id, similarity in top_results:
        results.append({
            "id": obj_id,
            "title": get_title(obj_id),
            "similarity_score": float(similarity),
            "metadata": get_metadata(obj_id)
        })
    
    return results
```

---

## 5. Frontend API Calls

Las siguientes funciones ya están implementadas en los componentes:

```typescript
// Text Search
fetch("http://localhost:8000/text_search", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    query: query,
    top_k: topK,
    method: activeMethod,
  }),
})

// Multimedia Search
const formData = new FormData()
formData.append("file", uploadedFile)
formData.append("type", fileType)

fetch("http://localhost:8000/multimedia_search", {
  method: "POST",
  body: formData,
})

// Upload Benchmark
const formData = new FormData()
formData.append("file", file)
formData.append("type", benchmarkType)

fetch("http://localhost:8000/upload_benchmark", {
  method: "POST",
  body: formData,
})
```

---

## 6. Checklist de Implementación Backend

- [ ] Endpoint `/text_search` implementado
- [ ] Endpoint `/multimedia_search` implementado
- [ ] Endpoint `/upload_benchmark` implementado
- [ ] TF-IDF y Cosine Similarity funcionando
- [ ] Modelo de embeddings cargado
- [ ] Base de datos de embeddings poblada
- [ ] Parseo de JSON/CSV funcional
- [ ] Métricas de ejecución precisas
- [ ] CORS configurado para frontend
- [ ] Documentación en `/docs` (Swagger)

---

## 7. Notas Importantes

1. **Frontend demo mode:** Las vistas funcionan sin backend (datos fake)
2. **Estructura de respuesta:** Mantener exactamente como se documenta arriba
3. **Error handling:** Retornar HTTP errors con `{"ok": False, "error": "message"}`
4. **CORS:** Configurar CORS para permite requests del frontend (localhost:3000)
5. **Performance:** Considerar caching/índices para búsquedas rápidas
6. **Validación:** Validar inputs (top_k max 1000, file size limits, etc.)

---

## 8. Testing

Puedes probar manualmente con curl:

```bash
# Text Search
curl -X POST "http://localhost:8000/text_search" \
  -H "Content-Type: application/json" \
  -d '{"query":"database","top_k":10,"method":"both"}'

# Multimedia Search
curl -X POST "http://localhost:8000/multimedia_search" \
  -F "file=@image.jpg" \
  -F "type=image"

# Upload Benchmark
curl -X POST "http://localhost:8000/upload_benchmark" \
  -F "file=@benchmark.json" \
  -F "type=text"
```

---

**¡Éxito con la implementación!** 🚀
