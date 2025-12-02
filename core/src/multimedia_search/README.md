# Módulo de Búsqueda Multimedia

## 📚 Descripción

Este módulo implementa un sistema de búsqueda de similitud para contenido multimedia (imágenes y audio) utilizando el modelo **Bag of Words (BoW)**.

## 🏗️ Arquitectura

```
src/multimedia_search/
├── __init__.py
├── feature_extractor.py   # Extracción de características (SIFT/ORB, MFCC)
├── codebook.py            # Generación de vocabulario (K-Means)
└── knn_index.py           # Búsqueda de similitud (KNN Secuencial)
```

## 🔧 Componentes

### 1. FeatureExtractor (`feature_extractor.py`)

Extrae descriptores locales de archivos multimedia.
- **Imágenes**: Usa SIFT (Scale-Invariant Feature Transform) o ORB si SIFT no está disponible. Retorna descriptores de puntos clave.
- **Audio**: Usa MFCC (Mel-Frequency Cepstral Coefficients). Retorna vectores de características espectrales.

### 2. Codebook (`codebook.py`)

Implementa el modelo "Bag of Words":
- Usa **K-Means** para agrupar descriptores de todos los archivos en `k` clusters (vocabulario visual/acústico).
- Convierte cada archivo en un **histograma** de frecuencias de estas palabras visuales.

### 3. KNNIndex (`knn_index.py`)

Maneja la búsqueda de similitud:
- Almacena los histogramas de los archivos indexados.
- Realiza búsqueda **KNN Secuencial** (fuerza bruta) comparando distancias Euclidianas.
- Soporta persistencia (guardar/cargar índice).

## 📡 API Endpoints

### 1. Construir Índice Multimedia

Sube un archivo ZIP con imágenes para construir el índice.

```http
POST /multimedia/build_index
Content-Type: multipart/form-data

file: images.zip
k: 100 (tamaño del vocabulario)
index_name: my_images
```

### 2. Buscar Similitud

Sube una imagen de consulta para encontrar las más similares.

```http
POST /multimedia/search
Content-Type: multipart/form-data

file: query_image.jpg
top_k: 5
index_name: my_images
```

## 🧪 Flujo de Trabajo

1. **Extracción**: Se extraen miles de descriptores SIFT de todas las imágenes.
2. **Entrenamiento**: Se ejecuta K-Means sobre estos descriptores para encontrar `k` centroides (palabras visuales).
3. **Indexación**: Cada imagen se convierte en un histograma basado en qué tan cerca están sus descriptores de los centroides.
4. **Búsqueda**: La imagen de consulta se convierte en histograma y se busca los vectores más cercanos en el índice.

## 📋 Requisitos

- `opencv-python` (o `opencv-python-headless`)
- `scikit-learn`
- `numpy`
- `librosa` (para audio)
