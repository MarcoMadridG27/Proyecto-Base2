# Proyecto Integrador -- Introducción y Proyecto 1

## 1. Introducción General

*(Contenido proveniente del archivo Proyecto Intro)*

El proyecto integrador consiste en diseñar e implementar un sistema de
base de datos multimodal capaz de manejar datos estructurados y no
estructurados. La arquitectura general combina:

-   Un **backend** orientado a microservicios.
-   Un **parser SQL personalizado**.
-   Un **query engine** que decide qué índice utilizar.
-   Un **módulo de almacenamiento tabular** basado en índices clásicos.
-   Un **módulo vectorial/multimedia** para imágenes, audio y texto.
-   Un **frontend** para consultas, carga de archivos y visualización de
    resultados.

La meta es integrar: 1. Datos tabulares con índices como B+Tree, Hash,
Sequential File. 2. Datos multimodales (texto, imágenes, audio) con
índices de similitud.

Aplicaciones posibles: - Sistemas geoespaciales. - Recomendadores
multimodales. - Gestión de inventario con índices 3D. - Detección de
similitud de canciones, imágenes, etc.

## 2. Proyecto 1 -- Organización e Indexación de Archivos Tabulares y Espaciales

*(Contenido proveniente del archivo Proyecto 1)*

### Objetivo

Construir un mini gestor de bases de datos que implemente técnicas de
organización de archivos y sus respectivos índices, usando archivos
planos reales y simulando un RDBMS.

### Técnicas a Implementar

-   **Sequential File** o **AVL File**
-   **ISAM (Sparse Index de 3 niveles)**
-   **Extendible Hashing**
-   **B+ Tree**
-   **R-Tree** (para datos espaciales)

### Operaciones principales

-   `search(key)`
-   `rangeSearch(begin-key, end-key)`
-   `add(registro)`
-   `remove(key)`
-   En RTree:
    -   `rangeSearch(point, radio)`
    -   `rangeSearch(point, k)` (k vecinos más cercanos)

### Parser SQL

Debe transformar consultas estilo SQL en comandos ejecutables.\
Ejemplos:

    CREATE TABLE Restaurantes (
      id INT KEY INDEX SEQ,
      nombre VARCHAR[20] INDEX BTree,
      fechaRegistro DATE,
      ubicacion ARRAY[FLOAT] INDEX RTree
    );

    select * from Restaurantes where id = x
    select * from Restaurantes where nombre between x and y
    insert into Restaurantes values (...)
    delete from Restaurantes where id = x

### Consideraciones de Implementación

-   El Sequential File debe usar un área auxiliar y reconstrucción
    cuando llegue a K registros.
-   ISAM requiere overflow pages para nuevas inserciones.
-   Hashing no soporta `rangeSearch`.
-   RTree puede usarse desde una librería existente.
-   Código orientado a objetos y genérico.
-   Backend 100% en Python + frontend simple.

### Informe

-   Explicar algoritmos de inserción, eliminación y búsqueda.
-   Análisis comparativo teórico.
-   Resultados experimentales (tiempo + accesos a disco).
-   Pruebas en GUI.
-   Video de presentación.

## 3. Conclusión

El Proyecto 1 constituye la base estructurada del sistema multimodal. El
archivo de introducción describe cómo este proyecto se integra con el
Proyecto 2 para formar un backend completo capaz de manejar tanto
índices clásicos como índices vectoriales y búsquedas por similitud.
