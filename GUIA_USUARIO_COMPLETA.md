# 📚 Guía Completa del Usuario - Sistema de Búsqueda

## 🎯 ¿Qué es este Sistema?

Este es un **motor de búsqueda inteligente** que te permite buscar información de tres formas diferentes:

1. **Búsqueda de Texto**: Encuentra documentos similares usando palabras clave
2. **Búsqueda de Imágenes**: Encuentra imágenes similares a una imagen de consulta
3. **Búsqueda de Audio**: Encuentra audios similares a un audio de consulta

---

## 🚀 Cómo Iniciar el Sistema

### 1. Abrir el Frontend

1. Abre tu navegador web (Chrome, Firefox, Edge, etc.)
2. Ve a: **http://localhost:3000**
3. Verás la página principal con tres opciones

---

## 📝 PARTE 1: Búsqueda de Texto

### ¿Qué hace?

Busca documentos de texto que sean **similares** a tu consulta. Por ejemplo:
- Si buscas "machine learning", encontrará documentos sobre inteligencia artificial, redes neuronales, etc.
- No solo busca coincidencias exactas, sino documentos **relacionados temáticamente**

### Cómo Usar

#### **Paso 1: Ir a Búsqueda de Texto**

1. En la página principal, haz click en **"Text Search"**
2. Verás dos pestañas: **"Search"** y **"Upload & Index"**

---

#### **Paso 2: Subir tus Documentos (Solo la primera vez)**

Antes de buscar, necesitas **crear un índice** con tus documentos.

**¿Qué es un índice?**
> Un índice es como el índice de un libro. En lugar de leer todo el libro página por página para encontrar algo, miras el índice y vas directo a la página correcta. Nuestro sistema crea un "índice inteligente" de tus documentos para buscar rápidamente.

**Pasos:**

1. **Prepara tu archivo CSV**:
   - Abre Excel o Google Sheets
   - Crea dos columnas: `doc_id` y `text`
   - Ejemplo:
   
   ```csv
   doc_id,text
   1,"Machine learning is a subset of artificial intelligence"
   2,"Deep learning uses neural networks with multiple layers"
   3,"Python is a popular programming language for data science"
   ```

2. **Guarda como CSV**:
   - En Excel: "Guardar como" → "CSV (delimitado por comas)"
   - Nombre sugerido: `mis_documentos.csv`

3. **Sube el archivo**:
   - Ve a la pestaña **"Upload & Index"**
   - Click en **"Choose File"**
   - Selecciona tu archivo CSV
   - (Opcional) Cambia el nombre del índice si quieres (por defecto es "default")
   - Click en **"Build Index"**
   - Espera a que aparezca el mensaje de éxito ✅

**¿Qué está pasando?**
> El sistema está leyendo todos tus documentos, analizando las palabras importantes, y creando una estructura de datos especial que permite buscar muy rápido. Esto puede tomar unos segundos dependiendo de cuántos documentos tengas.

---

#### **Paso 3: Buscar**

1. Ve a la pestaña **"Search"**
2. En el campo **"Search Query"**, escribe lo que buscas:
   - Ejemplo: `machine learning algorithms`
   - Ejemplo: `python programming`
3. (Opcional) Ajusta **"Top-K Results"** para ver más o menos resultados (por defecto 10)
4. Click en **"Search"**

**Resultados:**

Verás una tabla con:
- **Rank**: Posición del resultado (1 = más relevante)
- **Doc ID**: Identificador del documento
- **Score**: Qué tan similar es (más alto = más similar)
- **Text**: El contenido del documento

**Métricas:**
- **Execution Time**: Cuánto tardó la búsqueda (en milisegundos)
- **Total Results**: Cuántos documentos encontró

---

## 🖼️ PARTE 2: Búsqueda de Imágenes y Audio

### ¿Qué hace?

Encuentra imágenes o audios **visualmente/acústicamente similares** a tu archivo de consulta.

**Ejemplos de uso:**
- Tienes una foto de un gato → Encuentra todas las fotos de gatos en tu colección
- Tienes una canción → Encuentra canciones con ritmo o estilo similar
- Tienes una foto de un paisaje → Encuentra paisajes parecidos

### Cómo Usar

#### **Paso 1: Ir a Búsqueda Multimedia**

1. En la página principal, haz click en **"Multimedia Search"**
2. Verás dos pestañas: **"Search"** y **"Build Index"**

---

#### **Paso 2: Crear un Índice (Solo la primera vez)**

**¿Qué es un índice multimedia?**
> Imagina que tienes 1000 fotos. Para encontrar una foto similar, el sistema NO compara tu foto con las 1000 una por una (sería muy lento). En su lugar, crea un "mapa" inteligente que agrupa fotos similares. Cuando buscas, solo mira los grupos relevantes. ¡Mucho más rápido!

**Pasos:**

1. **Prepara tus archivos**:
   - Crea una carpeta con tus imágenes y/o audios
   - Ejemplo de estructura:
   ```
   mis_archivos/
   ├── foto1.jpg
   ├── foto2.png
   ├── foto3.jpeg
   ├── cancion1.mp3
   ├── cancion2.wav
   └── audio1.flac
   ```

2. **Crear un ZIP**:
   - **Windows**: 
     - Selecciona todos los archivos
     - Click derecho → "Enviar a" → "Carpeta comprimida (en zip)"
   - **Mac**: 
     - Selecciona todos los archivos
     - Click derecho → "Comprimir"
   - Nombre sugerido: `mis_medios.zip`

3. **Subir el ZIP**:
   - Ve a la pestaña **"Build Index"**
   - Click en **"Choose File"**
   - Selecciona tu archivo ZIP
   - Configura:
     - **Index Name**: Nombre para tu índice (ej: "fotos_vacaciones")
     - **Vocabulary Size (K)**: Déjalo en 100 (es un buen valor por defecto)
   - Click en **"Build Index"**
   - **IMPORTANTE**: Esto puede tomar varios minutos si tienes muchos archivos

**¿Qué está pasando?**
> El sistema está:
> 1. **Extrayendo características**: Analiza cada imagen/audio y extrae sus "características" (colores, formas, texturas para imágenes; tonos, ritmos para audio)
> 2. **Creando vocabulario**: Agrupa características similares (como crear categorías)
> 3. **Construyendo índice**: Crea dos estructuras de búsqueda (una rápida, una muy rápida)

**Parámetros Explicados:**

- **Vocabulary Size (K)**: 
  - Número de "categorías" para agrupar características
  - **Más bajo (50)**: Búsqueda más rápida pero menos precisa
  - **Más alto (200)**: Búsqueda más lenta pero más precisa
  - **Recomendado**: 100 para la mayoría de casos

---

#### **Paso 3: Buscar**

1. Ve a la pestaña **"Search"**

2. **Sube tu archivo de consulta**:
   - Click en el área de "Query Media"
   - Selecciona:
     - Una **imagen** si buscas imágenes similares
     - Un **audio** si buscas audios similares

3. **Configura la búsqueda**:
   - **Index Name**: El nombre del índice que creaste (ej: "fotos_vacaciones")
   - **Top-K Results**: Cuántos resultados quieres ver (por defecto 5)

4. Click en **"Find Similar"**

**Resultados:**

Verás tarjetas con:

**Para Imágenes:**
- La imagen encontrada
- **Rank**: Posición (#1 = más similar)
- **Filename**: Nombre del archivo
- **Similarity**: Porcentaje de similitud (100% = idéntica)
- Barra de progreso visual

**Para Audio:**
- Icono de música 🎵
- **Reproductor de audio**: Puedes escuchar el audio directamente
- **Rank**, **Filename**, **Similarity** igual que imágenes

**Métricas:**
- **Execution Time**: Cuánto tardó la búsqueda
- **Total Similar**: Cuántos resultados encontró

---

## 🔍 Conceptos Importantes

### 1. ¿Qué es un Índice?

**Analogía del Diccionario:**
- Sin índice: Leer todo el diccionario palabra por palabra para encontrar "elefante"
- Con índice: Ir directo a la letra "E" y buscar ahí

**En nuestro sistema:**
- Sin índice: Comparar tu búsqueda con TODOS los documentos/imágenes/audios
- Con índice: Ir directo a los documentos/archivos relevantes

**Ventajas:**
- ✅ Búsqueda 10-100x más rápida
- ✅ Funciona con millones de documentos/archivos
- ❌ Requiere tiempo inicial para construirlo

---

### 2. ¿Cómo Funciona la Búsqueda de Texto?

**Proceso simplificado:**

1. **Preprocesamiento**:
   ```
   Texto original: "The cats are running quickly"
   ↓
   Tokenización: ["The", "cats", "are", "running", "quickly"]
   ↓
   Quitar palabras comunes: ["cats", "running", "quickly"]
   ↓
   Stemming (raíz): ["cat", "run", "quick"]
   ```

2. **TF-IDF** (Term Frequency - Inverse Document Frequency):
   - Mide qué tan **importante** es cada palabra
   - Palabras raras = más importantes
   - Palabras comunes = menos importantes

3. **Cosine Similarity**:
   - Compara tu consulta con cada documento
   - Calcula un "score" de similitud
   - Devuelve los documentos con mayor score

**Ejemplo:**
```
Tu búsqueda: "machine learning"
Documento 1: "Machine learning is AI" → Score: 0.95 (muy similar)
Documento 2: "Python programming" → Score: 0.20 (poco similar)
Documento 3: "Deep learning neural networks" → Score: 0.75 (similar)

Resultado: [Doc 1, Doc 3, Doc 2]
```

---

### 3. ¿Cómo Funciona la Búsqueda Multimedia?

**Para Imágenes (SIFT - Scale-Invariant Feature Transform):**

1. **Extracción de características**:
   - Detecta "puntos clave" en la imagen (esquinas, bordes, texturas)
   - Cada punto tiene un "descriptor" (vector de números)
   - Una imagen puede tener cientos de puntos clave

2. **Bag of Visual Words**:
   - Agrupa descriptores similares en "palabras visuales"
   - Es como crear un vocabulario de características
   - Ejemplo: "palabra visual #1" = esquinas rojas, "palabra visual #2" = líneas horizontales

3. **Histograma**:
   - Cuenta cuántas veces aparece cada "palabra visual"
   - Crea un vector que representa la imagen
   - Ejemplo: [5, 0, 12, 3, ...] = 5 veces palabra #1, 0 veces palabra #2, etc.

4. **Búsqueda**:
   - Compara histogramas usando distancia euclidiana
   - Imágenes con histogramas similares = imágenes similares

**Para Audio (MFCC - Mel-Frequency Cepstral Coefficients):**

1. **Extracción de características**:
   - Divide el audio en pequeños fragmentos (frames)
   - Extrae 13 coeficientes por frame
   - Captura información sobre tono, timbre, ritmo

2. **Bag of Acoustic Words**:
   - Igual que imágenes, pero con características de audio
   - Agrupa frames similares en "palabras acústicas"

3. **Búsqueda**:
   - Compara histogramas de palabras acústicas
   - Audios con histogramas similares = audios similares

---

### 4. Métodos de Búsqueda

El sistema tiene **DOS métodos** de búsqueda multimedia:

#### **Método 1: KNN Secuencial (Fuerza Bruta)**
- Compara tu consulta con **TODOS** los archivos uno por uno
- **Ventajas**: 
  - ✅ Resultados 100% precisos
  - ✅ Simple de entender
- **Desventajas**: 
  - ❌ Lento con muchos archivos
  - ❌ Tiempo crece linealmente (2x archivos = 2x tiempo)

#### **Método 2: KNN Indexado (Índice Invertido)**
- Usa un índice inteligente para buscar solo en archivos relevantes
- **Ventajas**: 
  - ✅ Mucho más rápido (10-100x)
  - ✅ Tiempo casi constante (no importa cuántos archivos)
- **Desventajas**: 
  - ❌ Puede perder algunos resultados (99% precisión)
  - ❌ Requiere más memoria

**¿Cuál usar?**
- **Pocos archivos (< 1000)**: Cualquiera funciona bien
- **Muchos archivos (> 10,000)**: Usa indexado
- **Máxima precisión**: Usa secuencial
- **Máxima velocidad**: Usa indexado

---

## 💡 Casos de Uso Reales

### Búsqueda de Texto

**Caso 1: Base de Conocimiento Empresarial**
- Tienes 10,000 documentos de políticas, manuales, reportes
- Un empleado busca "política de vacaciones"
- El sistema encuentra todos los documentos relevantes en milisegundos

**Caso 2: Investigación Académica**
- Tienes 5,000 papers científicos
- Buscas "quantum computing algorithms"
- Encuentra papers relacionados aunque usen términos diferentes

### Búsqueda de Imágenes

**Caso 1: E-commerce**
- Cliente sube foto de un zapato que le gusta
- Sistema encuentra zapatos similares en tu catálogo
- "Búsqueda visual de productos"

**Caso 2: Organización de Fotos**
- Tienes 50,000 fotos de vacaciones
- Buscas una foto específica de una playa
- Subes una foto similar y el sistema encuentra todas las fotos de playas

### Búsqueda de Audio

**Caso 1: Biblioteca Musical**
- Tienes 10,000 canciones
- Escuchas una canción en la radio y la grabas
- Sistema encuentra la canción original en tu biblioteca

**Caso 2: Detección de Plagio**
- Verificar si un audio es copia de otro
- Buscar versiones similares de una grabación

---

## 🎓 Preguntas Frecuentes

### ¿Cuántos archivos puedo indexar?

- **Texto**: Hasta 1 millón de documentos (depende de RAM)
- **Multimedia**: Hasta 100,000 archivos (depende de disco y RAM)

### ¿Cuánto tarda construir un índice?

- **Texto**: ~1 segundo por cada 1,000 documentos
- **Imágenes**: ~2-5 segundos por imagen (depende de tamaño)
- **Audio**: ~1-3 segundos por minuto de audio

### ¿Puedo tener múltiples índices?

¡Sí! Puedes crear índices diferentes con nombres distintos:
- `fotos_2023`
- `fotos_2024`
- `musica_rock`
- `musica_clasica`

### ¿Qué formatos soporta?

**Texto**: CSV con columnas `doc_id` y `text`

**Imágenes**: 
- PNG, JPG, JPEG, BMP, GIF

**Audio**:
- WAV, MP3, FLAC, OGG, M4A

### ¿Los archivos se quedan en el servidor?

Sí, los archivos se almacenan en el servidor para poder buscar. Están en:
- `core/data/text_index_[nombre]/`
- `core/data/mm_index_[nombre]/media/`

### ¿Puedo borrar un índice?

Sí, simplemente elimina la carpeta correspondiente en `core/data/`

---

## 🔧 Solución de Problemas

### "Index not found"
**Problema**: No has creado un índice todavía
**Solución**: Ve a "Build Index" y crea uno primero

### "No results found"
**Problema**: Tu consulta no tiene coincidencias
**Solución**: 
- Intenta con términos más generales
- Verifica que el índice tenga datos relevantes

### "Build index failed"
**Problema**: Error al construir índice
**Solución**:
- Verifica formato del archivo (CSV correcto, ZIP válido)
- Revisa que los archivos no estén corruptos
- Verifica que tengas espacio en disco

### Búsqueda muy lenta
**Problema**: Muchos archivos indexados
**Solución**:
- Usa el método "indexado" en lugar de "secuencial"
- Reduce el valor de K (vocabulario más pequeño)
- Considera dividir en múltiples índices

---

## 📊 Interpretando Resultados

### Scores de Similitud

**Texto (Cosine Similarity):**
- **0.9 - 1.0**: Casi idénticos
- **0.7 - 0.9**: Muy similares
- **0.5 - 0.7**: Moderadamente similares
- **0.3 - 0.5**: Poco similares
- **< 0.3**: Casi no relacionados

**Multimedia (Similarity %):**
- **90-100%**: Casi idénticos (posible duplicado)
- **70-90%**: Muy similares (mismo objeto/escena/canción)
- **50-70%**: Similares (mismo tipo/categoría)
- **30-50%**: Algo similares (algunas características comunes)
- **< 30%**: Diferentes

---

## 🎯 Mejores Prácticas

### Para Búsqueda de Texto

1. **Usa términos específicos**: "machine learning algorithms" mejor que "ML"
2. **Evita palabras muy comunes**: "el", "la", "de" se ignoran automáticamente
3. **Prueba sinónimos**: Si no encuentras resultados, intenta palabras relacionadas

### Para Búsqueda Multimedia

1. **Calidad de archivos**: Mejor calidad = mejores resultados
2. **Tamaño consistente**: Imágenes muy grandes o muy pequeñas pueden dar resultados imprecisos
3. **Archivos similares**: El sistema funciona mejor cuando buscas cosas similares a lo que indexaste

### Para Construir Índices

1. **Agrupa archivos relacionados**: No mezcles fotos de gatos con música clásica
2. **Nombres descriptivos**: Usa nombres de índice que recuerdes fácilmente
3. **Actualiza periódicamente**: Si agregas muchos archivos nuevos, reconstruye el índice

---

## 🚀 Próximos Pasos

1. **Practica con ejemplos pequeños**: Empieza con 10-20 archivos
2. **Experimenta con parámetros**: Prueba diferentes valores de K
3. **Compara métodos**: Usa "compare" para ver diferencias de velocidad
4. **Escala gradualmente**: Una vez que entiendas el sistema, sube más archivos

---

## 📞 Soporte

Si tienes problemas:
1. Revisa esta guía
2. Verifica los logs del servidor (terminal donde corre el backend)
3. Intenta con archivos más pequeños primero
4. Reconstruye el índice si algo sale mal

---

**¡Disfruta buscando! 🔍✨**
