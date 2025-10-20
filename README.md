# Proyecto 1 - Base de datos II

# Integrantes: 

| Nombre Completo | Código|
| :--- | :--- | 
| Marco Madrid | 202320053  |
| Henry Quispe | 202320078 |
| Maria Surco | 202110358 |
| Juan Inca |  |
| Joaquin Huamán |  |

# Introducción

## Objetivo del Proyecto

El objetivo principal de este proyecto es **comprender y aplicar técnicas de organización e indexación de archivos físicos** para **optimizar la gestión, el almacenamiento y la recuperación eficiente de datos estructurados** dentro de un modelo relacional basado en tablas. Además, se explorará la integración de soporte para **datos espaciales**. El proyecto busca desarrollar un **mini gestor de bases de datos** que implemente las operaciones fundamentales de **inserción, eliminación y búsqueda** de manera eficiente.

***

## Descripción de la Aplicación

Se desarrollará una **herramienta de organización y gestión de archivos planos (flat files)** que maneja datos con distintas estructuras. \
Esta aplicación puede ser utilizada en múltiples escenarios donde se requiera **ordenar, catalogar y recuperar información de manera rápida y estructurada**. 

Ejemplos de su uso incluyen:

* **Organización de Informes o Documentos:** Indexar grandes volúmenes de informes para búsquedas rápidas.
* **Gestión de Datos de Personas:** Almacenar y buscar eficientemente registros de usuarios o clientes.
* **Análisis de Datos de Compras/Transacciones:** Ordenar y consultar datos transaccionales, potencialmente incorporando **índices espaciales** para analizar ubicaciones geográficas de las transacciones.

La aplicación servirá como un banco de pruebas para **combinar e integrar diversas técnicas de indexación**, permitiendo la validación funcional del sistema mediante el uso de **archivos planos con datos reales**.

***

## Resultados Esperados

Al aplicar y comparar las diferentes técnicas de indexación (como B-trees, índices hash, y potencialmente estructuras de datos espaciales), esperamos obtener los siguientes resultados:

1. **Optimización del Rendimiento:** Lograr una **alta eficiencia** en las operaciones fundamentales (**inserción, eliminación y búsqueda**) en comparación con soluciones no indexadas o indexadas de forma subóptima.
2. **Claridad y Documentación:** Producir un **código con estructura clara** e incluir una **breve documentación técnica** que justifique el diseño, las decisiones de implementación (especialmente en la elección de las técnicas de indexación) y que detalle los resultados de las pruebas de rendimiento.
3. **Soporte a Datos Complejos:** Integrar con éxito el soporte para **datos espaciales**, ampliando la capacidad de la herramienta más allá de los datos puramente alfanuméricos.
# Algoritmos
## Sequential

Para nuestro proyecto hemos desarrollado una estructura **Sequential Index File** (Archivo Secuencial Indexado con Zona Auxiliar), diseñada para mantener un **acceso ordenado y eficiente** a los registros almacenados en disco, combinando una **región principal estática (D)** con una **región auxiliar dinámica (A)**.

El objetivo de esta estructura es **preservar el orden lógico de los registros** sin necesidad de reescribir continuamente la totalidad del archivo, permitiendo **inserciones, búsquedas y eliminaciones eficientes**, y reorganizando periódicamente el contenido para compactar la información.

### Arquitectura general

El archivo secuencial se compone de tres elementos principales:

1. **Región principal (D):** Contiene los registros ordenados de forma compacta. Es el cuerpo base del índice y se construye de manera batch, garantizando el orden físico por clave.
2. **Región auxiliar (A):** Espacio destinado a las nuevas inserciones. Los registros se enlazan mediante punteros lógicos (`next_ptr`), conservando el orden lógico total sin modificar la región D.
3. **Cabecera (Header):** Contiene tres valores clave:
   - `main_count`: cantidad de registros en la región D.  
   - `aux_count`: cantidad de registros en la región A.  
   - `head_ptr`: puntero lógico al primer registro del orden total.

Esta estructura **mantiene una lista lógica ordenada** (`head_ptr → next_ptr → ...`) que conecta registros de ambas regiones, haciendo posible recorrer los datos en orden creciente de claves, aun cuando los nuevos registros se encuentren físicamente dispersos.

---

### Insert

La operación `insert()` agrega nuevos registros sin alterar la región principal, preservando el orden lógico:

1. **Ubicación de inserción:**  
   Se utiliza una **búsqueda binaria** sobre la región principal (D) para determinar el punto de inserción adecuado (`lower_bound_d`).  
2. **Inserción en la región auxiliar (A):**  
   - Se crea un nuevo registro con su `offset` y `value`.  
   - El registro se escribe al final de la región auxiliar.  
3. **Actualización de punteros lógicos:**  
   - Si la lista está vacía, el nuevo registro se convierte en el `head_ptr`.  
   - En caso contrario, se recorren los punteros hasta ubicar el predecesor (`prev_ptr`) y el sucesor (`cur_ptr`), y se inserta el nuevo nodo entre ambos (`prev → new → cur`).  
4. **Reorganización periódica:**  
   Para evitar que la zona auxiliar crezca indefinidamente, el sistema activa una **reorganización automática** cuando el tamaño de `A` supera un umbral dependiente de `log₂(main_count)`.  
   En esta reorganización, todos los registros válidos de D y A se fusionan en una nueva D ordenada.

**Complejidad:**  
- Promedio: O(log n + m)  
- Mejor caso: O(log n)  
 donde *m* es el número de nodos en la zona auxiliar antes de la reorganización.

---

### Delete

La operación `delete()` recorre la lista lógica y **marca los registros como eliminados (tombstone)**, sin necesidad de compactar inmediatamente el archivo.

1. **Recorrido lógico:**  
   Se parte del `head_ptr` y se avanza siguiendo los punteros `next_ptr`.  
2. **Comparación ordenada:**  
   Dado que la lista está ordenada por clave, si `key_actual > key_buscada`, el proceso puede detenerse anticipadamente.  
3. **Marcado de eliminación:**  
   Cuando se encuentra un valor igual a la clave (`value == key`), el campo `offset` se sustituye por `DELETED_PTR = -1`, dejando constancia de la eliminación.  
4. **Reorganización diferida:**  
   Los registros eliminados no se borran físicamente hasta la siguiente reorganización, donde se vuelca la lista limpia en una nueva región principal compacta.

**Complejidad:**  
- O(n) en el peor caso, pero en la práctica O(log n + m) gracias al orden lógico y a la posibilidad de corte temprano.

---

### Search

La función `search()` permite recuperar todos los `offsets` cuyos valores coincidan con una clave dada.

1. **Inicio en el puntero principal (`head_ptr`):**  
   Se recorre la lista ordenada enlazada que une tanto registros de D como de A.  
2. **Comparación progresiva:**  
   - Si el valor actual es menor que la clave, se continúa.  
   - Si es igual, se añade el `offset` a los resultados.  
   - Si es mayor, la búsqueda se detiene (ya que los siguientes serán mayores).  
3. **Eficiencia:**  
   Gracias al orden lógico, la búsqueda se realiza con una complejidad O(log n + k), donde *k* es el número de coincidencias.

---

### Range Search

El método `search_range(lo, hi)` permite realizar búsquedas por **rango de valores** `[lo, hi]` en orden ascendente.

1. **Identificación del punto inicial:**  
   Se realiza una **búsqueda binaria (`lower_bound_d`)** sobre la región D para localizar el primer registro cuyo valor sea mayor o igual a `lo`.  
2. **Exploración secuencial:**  
   Desde el registro encontrado o desde el `head_ptr` si no existe un predecesor, se recorre la lista lógica usando los punteros `next_ptr`.  
3. **Filtrado por rango:**  
   - Los registros con `value < lo` son omitidos.  
   - Se añaden todos los `offsets` con valores dentro del rango.  
   - Al superar `hi`, el recorrido se detiene (la lista está ordenada).  
4. **Resultado:**  
   Se devuelve la lista de `offsets` que cumplen la condición, ya ordenada de manera natural.

**Complejidad:**  
O(log n + k), siendo *k* el número de registros dentro del rango.

---

### Resumen Sequential

| **Algoritmo**   | **Mejor Caso** | **Peor Caso**          |
|------------------|----------------|-------------------------|
| Insert           | O(log n)       | O(log n + m)           |
| Delete           | O(log n)       | O(log n + m)           |
| Search           | O(log n)       | O(log n + k)           |
| Range Search     | O(log n + k)   | O(log n + k + m)       |

**Leyenda:**  
- *n*: número de registros en la región principal (D).  
- *m*: número de registros en la región auxiliar (A).  
- *k*: número de resultados devueltos en la búsqueda o rango.

## Hash

### Insert
### Delete
### Search
### Range Search

## BPluss Tree
Este módulo proporciona una implementación de un índice **Árbol B+** (`BPlusTree`) que opera directamente sobre disco, utilizando la clase auxiliar `BPlusNode` para representar los nodos del árbol. Está diseñado específicamente para funcionar como un índice secundario, mapeando **claves** a **punteros** (offsets) que indican la ubicación de los registros completos en un archivo de datos principal.

La estructura se basa en nodos (`BPlusNode`) de tamaño fijo, determinado por la constante `ORDER` (que define el número máximo de claves por nodo). Esto optimiza las operaciones de I/O al leer/escribir bloques de tamaño predecible. 

Características clave:
- **Persistencia en Disco:** Toda la estructura del árbol reside en un archivo binario (`.idx`).
- **Balanceado:** El árbol se mantiene balanceado automáticamente durante inserciones y eliminaciones, garantizando un rendimiento logarítmico.
- **Nodos Hoja Enlazados:** Los nodos hoja están conectados secuencialmente (`next_leaf`), permitiendo búsquedas por rango eficientes.
- **Manejo de Tipos (Intento):** Incluye una función de comparación (`_cmp`) que intenta manejar claves numéricas y de texto, aunque el empaquetado/desempaquetado actual está fijo para enteros.

---

### Insert

La inserción de un par `(clave, puntero)` sigue estos pasos:
1.  **Búsqueda:** Se busca la **hoja** apropiada donde debería residir la nueva clave, descendiendo desde la raíz y usando búsqueda binaria (`binary_intern`) en cada nodo interno.
2.  **Inserción en Hoja:**
    * Si la hoja tiene espacio (menos de `ORDER` claves), la clave y el puntero se insertan manteniendo el orden. Se utiliza `bisect_left` (adaptado con `_cmp`) para encontrar la posición correcta.
    * Si la hoja está **llena** (`ORDER` claves), se produce un **split**:
        * La hoja se divide en dos nodos hoja.
        * La clave central (aproximadamente) se **promueve** al nodo padre.
        * Los punteros `next_leaf` se actualizan para mantener la cadena.
3.  **Propagación de Splits:** Si la promoción de una clave causa que un **nodo interno** se llene, este también se divide:
    * El nodo interno se divide en dos.
    * La clave central se promueve al padre.
    * Este proceso puede continuar recursivamente **hasta la raíz**. Si la raíz se divide, la **altura del árbol aumenta** en uno.

La complejidad típica de la inserción es **O(log<sub>B</sub> N)**, donde B es el `ORDER` y N el número de claves, debido a la naturaleza balanceada del árbol.

---

### Delete

La eliminación de una clave sigue un proceso similar pero inverso al de inserción:
1.  **Búsqueda:** Se localiza la **hoja** que contiene la clave a eliminar, descendiendo desde la raíz.
2.  **Eliminación en Hoja:** Se elimina la clave y su puntero asociado de la hoja.
3.  **Manejo de Underflow:** Si, tras la eliminación, el número de claves en la hoja cae por debajo del mínimo (`MIN_KEYS`), se produce un **underflow**:
    * **Préstamo (Redistribución):** Se intenta tomar prestada una clave del hermano izquierdo o derecho si este tiene claves suficientes (más de `MIN_KEYS`). Esto implica ajustar también la clave separadora en el nodo padre.
    * **Fusión (Merge):** Si ninguno de los hermanos puede prestar, la hoja se fusiona con uno de sus hermanos (izquierdo o derecho). Esto requiere eliminar la clave separadora del nodo padre.
4.  **Propagación de Underflow:** La eliminación de una clave en el padre (debido a una fusión) puede causar un underflow en el nodo interno. Este se maneja de forma similar: intentando redistribuir con un hermano interno o fusionando nodos internos. Este proceso puede propagarse **hasta la raíz**. Si la raíz queda vacía (con un solo puntero), esa raíz se elimina y su único hijo se convierte en la nueva raíz, **disminuyendo la altura** del árbol.

La complejidad típica de la eliminación también es **O(log<sub>B</sub> N)**.

---

### Search

La búsqueda de una clave específica (`search` o `find`) es muy eficiente:
1.  **Descenso:** Se comienza en la raíz y se utiliza búsqueda binaria (`binary_intern` adaptado con `_cmp`) en cada nodo interno para decidir qué puntero seguir hacia el siguiente nivel.
2.  **Localización en Hoja:** Al llegar a un nodo hoja, se usa búsqueda binaria (`binary_leaf` adaptado con `_cmp`) para encontrar la clave exacta.
3.  **Resultado:**
    * `search`: Devuelve el primer puntero encontrado para esa clave (o `None`).
    * `find`: Devuelve una **lista** de todos los punteros asociados a esa clave (maneja duplicados), escaneando hacia los lados en la hoja y potencialmente en las hojas siguientes si hay duplicados que cruzan límites de nodo.

La complejidad de encontrar la primera clave es **O(log<sub>B</sub> N)**. La función `find` puede tener una complejidad adicional si hay muchos duplicados (`+d`, donde `d` es el número de duplicados).

---

### Range Search

Gracias a los punteros `next_leaf`, la búsqueda por rango (`range_search(inicio, fin)`) es eficiente:
1.  **Localizar Inicio:** Se busca la **hoja** y la posición donde debería estar `begin_key` (usando la misma lógica de descenso que `search`).
2.  **Escaneo Secuencial:**
    * Se recorren las claves/punteros en la hoja actual desde la posición encontrada. Si una clave está dentro del rango `[begin_key, end_key]`, se añade su puntero a los resultados.
    * Si se llega al final de la hoja actual, se sigue el puntero `next_leaf` para pasar a la siguiente hoja.
    * Se repite el escaneo en las hojas siguientes.
3.  **Terminación:** El proceso se detiene cuando se encuentra una clave mayor que `end_key` o cuando se llega al final de la última hoja.

La complejidad es **O(log<sub>B</sub> N + k)**, donde `log N` es el costo de encontrar la hoja inicial y `k` es el número de elementos dentro del rango recuperados.

---

### Resumen B+ Tree

| Algoritmo      | Complejidad Típica | Notas                                                    |
| :------------- | :----------------- | :------------------------------------------------------- |
| Insert         | O(log<sub>B</sub> N) | Puede involucrar splits que suben hasta la raíz.           |
| Delete         | O(log<sub>B</sub> N) | Puede involucrar merges/redistribuciones hasta la raíz. |
| Search (Exacto) | O(log<sub>B</sub> N) | Búsqueda logarítmica hasta la hoja.                    |
| Find (Duplicados)| O(log<sub>B</sub> N + d) | `d` = número de duplicados encontrados.               |
| Range Search   | O(log<sub>B</sub> N + k) | `k` = número de elementos en el rango.                |

*(N es el número total de claves en el índice, B es el `ORDER` del árbol)*


## ISAM

Para nuestro proyecto hemos desarrollado una estructura **ISAM** (*Indexed Sequential Access Method*) diseñada para optimizar las búsquedas en grandes volúmenes de datos almacenados en disco.

Nuestro ISAM implementa una arquitectura **multinivel**, conformada por **tres niveles de índices jerárquicos**, donde:  
- **Nivel 1 y Nivel 2:** Actúan como índices intermedios (nivel raíz y secundario) que apuntan a las páginas de datos ubicadas en el nivel 3.  
- **Nivel 3:** Contiene los registros reales, ordenados por clave.  
- **Overflow:** Almacena los registros adicionales que exceden la capacidad del *batch* inicial.  

La estructura se construye inicialmente de forma **batch**, ordenando todos los registros según la clave. Esto garantiza búsquedas eficientes con una complejidad de **O(log n)** mediante búsqueda binaria en cada nivel.  
Para manejar inserciones posteriores sin necesidad de reorganizar los índices estáticos, ISAM implementa un sistema de **páginas de overflow encadenadas**, que almacenan los nuevos registros manteniendo la consistencia del acceso secuencial.

---

### Insert

Esta función utiliza el mismo mecanismo de búsqueda binaria multinivel que `search()` para localizar la página de datos donde debe insertarse el nuevo registro según su clave.  
Se presentan dos casos principales:

- **Caso 1:** Si la página principal tiene espacio disponible (menos de **BLOCK_FACTOR** registros), el registro se inserta directamente, se mantiene el orden ascendente por ID y se actualiza la página en disco.  
- **Caso 2:** Si la página está llena, el sistema recurre al mecanismo de *overflow*:  
  - Si no existe una cadena de overflow, se crea una nueva página y se enlaza mediante el puntero **next_page**.  
  - Si ya existe, se recorre la cadena hasta encontrar una página con espacio o se crea una nueva al final de la cadena.

---

### Delete

El algoritmo navega por los índices multinivel utilizando búsqueda binaria para ubicar la página de datos correspondiente.  
Una vez identificada, filtra los registros de la página principal creando una nueva lista que excluye el registro con la clave especificada.  
Si el tamaño de la lista disminuye, significa que el registro fue encontrado y eliminado; en ese caso, la página se actualiza y la operación retorna `TRUE`.  
Si el registro no se encuentra en la página principal pero existe una cadena de overflow, el proceso se repite recorriendo secuencialmente cada página de overflow hasta eliminar el registro o agotar la cadena.

---

### Search

Primero se carga el índice de **nivel 1 (raíz)** y se aplica una búsqueda binaria para determinar qué página de **nivel 2** explorar.  
Luego se repite el proceso en el nivel 2 para identificar la página de datos correspondiente del nivel 3.  
Una vez en la página de datos, se recorre la lista de registros de forma secuencial hasta encontrar la clave buscada.  
Si el registro no está en la página principal y existe una cadena de overflow (indicada por `next_page != -1`), se continúa la búsqueda recorriendo todas las páginas de overflow encadenadas hasta hallarlo o llegar al final de la cadena.

---

### Range Search

El algoritmo identifica las páginas de **nivel 2** que podrían contener los límites del rango mediante búsqueda binaria en el **nivel 1**.  
Posteriormente, determina todas las páginas intermedias entre `nivel_2_start` y `nivel_2_end` que potencialmente almacenan datos dentro del rango.  
Para cada página de nivel 2 identificada, se repite el proceso en el **nivel 3**: se localizan las páginas de datos que contienen los límites inferior y superior, y se exploran todas las páginas intermedias.  
En cada página de datos visitada, se recopilan los registros cuyo ID se encuentra dentro del rango especificado.
Finalmente, los resultados se ordenan por ID antes de retornarlos.

---

### Resumen ISAM

| Algoritmo     | Mejor Caso    | Peor Caso       |
|:-------------- |:--------------|:----------------|
| Insert         | O(log n)      | O(log n + m)    |
| Delete         | O(log n)      | O(log n + m)    |
| Search         | O(log n)      | O(log n)        |
| Range Search   | O(log n + k)  | O(log n + k)    |

## Rtree

# Experimentación

## Sequential
![](Images\Sequential.jpg)
## Hash

## BPlus Tree
![](Images\Btree.jpg)
## ISAM
![](Images\ISAM.png)
## Rtree


# Conclusiones
