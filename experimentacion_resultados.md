# 📊 Resultados de la Experimentación — MyIndex vs PostgreSQL

Este documento resume las **observaciones clave**, la **metodología del experimento** y las **conclusiones generales** basadas en la comparación entre:

- **MyIndex** (índice invertido implementado manualmente con SPIMI)
- **PostgreSQL** (búsqueda con `tsvector`, `tsquery` y ranking `ts_rank`)

Dataset utilizado:  
👉 https://www.kaggle.com/datasets/bwandowando/spotify-songs-with-attributes-and-lyrics

---

## 🔍 Metodología del Experimento

Para evaluar el rendimiento de ambos sistemas se realizaron consultas sobre subsets del dataset original, usando tamaños crecientes:

- **1k**, 2k, 4k, 8k, 16k, 32k, 64k y 128k canciones.

Consulta utilizada para ambas plataformas:

```
"My bags were packed from the day I was born Yeah I’m leaving one way or another Curiosity has got the best of me Yeah I’m leaving one way or another"
```

Se midieron:

1. **Tiempo de respuesta**
2. **Similitud obtenida**
3. **ID del primer documento recuperado**

---

## ### Observaciones clave

### 🔹 1. Velocidad
- **MyIndex fue consistentemente más rápido** que PostgreSQL en todos los tamaños.
- PostgreSQL incrementó su tiempo de forma casi lineal, llegando a **2.45 s** en 128k.
- MyIndex, al usar estructuras más simples e índices en memoria, alcanzó solo **266 ms** en 128k.

### 🔹 2. Diferencia en ranking
- MyIndex devolvió mayor similitud en casi todos los casos debido a que trabaja con coincidencias más directas.
- PostgreSQL usa un ranking **tf-idf normalizado**, lo que produce puntajes más bajos pero más "lingüísticamente razonables".

### 🔹 3. Precisión de coincidencia
- MyIndex recuperó exactamente la canción esperada en varios datasets.
- PostgreSQL tendió a encontrar resultados distintos al aumentar el tamaño, debido a:
  - normalización,
  - stemming,
  - separación de tokens,
  - ajustes de ranking.

### 🔹 4. Escalabilidad
- PostgreSQL es más lento en esta prueba porque procesa más información y aplica técnicas IR reales.
- MyIndex escala mejor en **estos volúmenes**, pero no soportaría fácilmente datasets industriales (millones+).

### 🔹 5. Peso del preprocesamiento
- PostgreSQL tuvo un mayor costo en su procesamiento `tsvector`: remueve stopwords, analiza tokens, indexa cada término.
- MyIndex no hace stemming ni stopwords, lo que lo hace más rápido, pero menos robusto.

---

## 🧠 Conclusiones Generales

- **MyIndex**:
  - Excelente rendimiento en datasets pequeños y medianos.
  - Recuperación rápida gracias a su estructura simplificada.
  - Alta coincidencia literal, útil en búsquedas exactas.
  - Limitado en capacidad semántica y robustez.

- **PostgreSQL**:
  - Más lento en esta prueba, pero diseñado para sistemas reales con millones de documentos.
  - Ranking más completo y semánticamente consistente (tf-idf + normalización).
  - Funciones avanzadas: stemming, operadores, frases, pesos, boolean search.
  - Más adecuado para aplicaciones profesionales.

### 📌 En resumen:

| Criterio | MyIndex | PostgreSQL |
|---------|---------|------------|
| Velocidad | ⭐ Más rápido | ❌ Más lento |
| Coincidencia literal | ⭐ Excelente | ❌ Menor |
| Búsqueda semántica | ❌ No soportada | ⭐ Avanzada |
| Escalabilidad real | ❌ Limitado | ⭐ Industrial |
| Complejidad | Baja | Alta |

Ambos enfoques son correctos, pero responden a **objetivos distintos**:  
**MyIndex** es ideal para entender IR y comparar algoritmos, mientras que **PostgreSQL** es la versión realista para sistemas de producción.

