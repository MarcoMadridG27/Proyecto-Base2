# Proyecto 1 - Base de datos II

# Integrantes: 

| Nombre Completo | Código|
| :--- | :--- | 
| Marco Madrid |  |
| Henry Quispe |  |
| Maria Surco | 202110358 |
| Juan Inca |  |
| Joaquin Huamán |  |

# Introducción
# Algoritmos
## Sequential
### Insert
### Delete
### Search
### Range Search

## Hash

### Insert
### Delete
### Search
### Range Search

## BPluss Tree

### Insert
### Delete
### Search
### Range Search

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

# Conclusiones
