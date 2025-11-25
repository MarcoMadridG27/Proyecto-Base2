# Proyecto 2 -- Guía Completa

## 1. Backend -- Índice Invertido para Texto

### Preprocesamiento

-   Tokenización\
-   Stopwords\
-   Signos\
-   Stemming

### SPIMI

-   Construcción de bloques\
-   MergeBlocks\
-   Cálculo TF-IDF\
-   Norma del documento

### Consulta

-   Preprocesar query\
-   TF-IDF\
-   Cosine similarity\
-   Top-K sin cargar índice completo

### Comparación con PostgreSQL

-   tsvector / tsquery\
-   ts_rank, ts_rank_cd\
-   Comparación de tiempo y calidad

## 2. Backend -- Descriptores Multimedia

### Extracción de Características

-   Imágenes: SIFT, Inception v3, ResNet50\
-   Audio: MFCC, espectrogramas

### Codebook

-   Recolección de descriptores\
-   K-Means\
-   Visual/Acoustic Words

### Bag of Visual Words

-   Asignación a clusters\
-   Histograma\
-   TF-IDF

### KNN Secuencial

-   Cosine similarity\
-   Heap Top-K

### KNN Indexado

-   Índice invertido visual\
-   TF-IDF\
-   Recuperación eficiente

### Comparación con PostgreSQL (pgVector)

-   Inserción de vectores\
-   Evaluación de tiempos

## 3. Frontend

### Búsqueda textual

-   Sintaxis SQL\
-   Top-K\
-   Resultados + tiempos

### Búsqueda multimedia

-   Subida de archivo\
-   Resultados similares\
-   Tiempos

## 4. Experimentos

### Texto

Comparación de tiempos entre MyIndex y PostgreSQL para N crecientes.

### Multimedia

Comparación: KNN secuencial, KNN indexado, PostgreSQL pgVector.

## 5. Informe Final

-   Introducción\
-   Desarrollo\
-   Frontend\
-   Experimentos\
-   Conclusiones
