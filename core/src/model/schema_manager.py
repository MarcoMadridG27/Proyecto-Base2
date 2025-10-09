import os
import json
from typing import Any, Dict, List, Optional, Tuple, Iterator

from src.model.record import RecordSchema
from src.dbms.file_manager import FileManager

from src.dbms.sequential import SequentialFile
from src.dbms.isam import ISAMIndex
from src.dbms.extendible_hash import ExtendibleHash
from src.dbms.bplustree import BPlusTree
from src.dbms.rtree import RTree

# Mapa "tipo" -> clase de índice.
INDEX_TYPES = {
    "sequential": SequentialFile,
    "isam": ISAMIndex,
    "hash": ExtendibleHash,
    "btree": BPlusTree,
    "rtree": RTree,
}

class SchemaManager:
    """
    Gestor multi-tabla minimalista que soporta las siguientes operaciones:
      - create_table: Crea la tabla con su esquema y los índices opcionales.
      - insert: Inserta una fila en la tabla y actualiza los índices.
      - select: Realiza consultas con filtrado por igualdad o por rango, utilizando índices cuando estén disponibles.
      - delete: Elimina registros marcándolos como borrados (tombstone).
      - create_index: Crea un índice para una columna y lo puebla con registros.
    """

    def __init__(self, data_dir: str = "data"):
        """Inicializa el gestor de esquemas con el directorio de datos especificado."""
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.catalog_path = os.path.join(data_dir, "catalog.json")
        self.tables: Dict[str, Dict[str, Any]] = {}

        # Si ya existe un catálogo, lo carga y reconstruye la información de las tablas y sus índices.
        if os.path.exists(self.catalog_path):
            self._load_catalog()

    def _save_catalog(self) -> None:
        """
        Guarda los metadatos de las tablas en un archivo catalog.json:
        - columns: definición de las columnas de cada tabla.
        - index_types: tipos de índices por columna.
        """
        catalog: Dict[str, Any] = {}
        for t, info in self.tables.items():
            idx_types = dict(info.get("_index_types", {}))

            # Verifica que todos los índices tengan tipo en idx_types.
            for col in info.get("indexes", {}):
                if col not in idx_types:
                    raise RuntimeError(f"Falta index_type para {t}.{col}")

            catalog[t] = {
                "columns": info["schema"].columns,
                "index_types": idx_types,
            }

        with open(self.catalog_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2)

    def _load_catalog(self) -> None:
        """
        Carga el archivo catalog.json y reconstruye la información de las tablas:
        - RecordSchema
        - FileManager
        - Instancia de los índices según los tipos definidos.
        """
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        for t, meta in catalog.items():
            # Asegurarse de que las columnas están definidas
            if "columns" not in meta:
                raise ValueError(f"Las columnas de la tabla {t} no están definidas en el catálogo.")

            # Cargar el esquema de columnas y el archivo .dat correspondiente
            schema = RecordSchema(meta["columns"])
            filepath = os.path.join(self.data_dir, f"{t}.dat")
            fm = FileManager(filepath, schema)

            # Cargar los índices desde los tipos especificados en el catálogo
            idx_types: Dict[str, str] = meta.get("index_types", {})
            indexes: Dict[str, Any] = {}
            for col, typ in idx_types.items():
                ctor = INDEX_TYPES.get(typ)
                if not ctor:
                    raise ValueError(f"Tipo de índice desconocido en catálogo: {typ}")

                # Verificar que las columnas estén disponibles
                column = next((c for c in schema.columns if c["name"] == col))
                if column is None:
                    raise ValueError(f"Columna {col} no encontrada en la tabla {t}.")

                column_type = column["type"]
                column_format = self.get_column_format(column_type)
                indexes[col] = ctor(t, column_format)

            # Registra la tabla en memoria
            self.tables[t] = {
                "schema": schema,
                "file": fm,
                "indexes": indexes,
                "_index_types": dict(idx_types),
            }

    # ===================== Crear tabla =====================

    def create_table(
            self,
            table: str,
            columns: List[Dict[str, str]],
            index_map: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Crea una nueva tabla en la base de datos con su esquema y los índices opcionales.

        - columns: Define las columnas de la tabla como una lista de diccionarios.
        - index_map: Mapa de columnas a tipos de índice (opcional).
        """
        if table in self.tables:
            return f"La tabla {table} ya existe"

        # Crear el esquema de la tabla y el archivo .dat
        schema = RecordSchema(columns)
        path = os.path.join(self.data_dir, f"{table}.dat")
        fm = FileManager(path, schema)

        indexes: Dict[str, Any] = {}
        idx_types: Dict[str, str] = {}
        if index_map:
            for col, typ in index_map.items():
                if col not in [c["name"] for c in columns]:
                    raise ValueError(f"Columna {col} no existe en {table}")
                ctor = INDEX_TYPES.get(typ)
                if not ctor:
                    raise ValueError(f"Tipo de índice no soportado: {typ}")
                indexes[col] = ctor(table, col)
                idx_types[col] = typ

        # Guardar la tabla en memoria
        self.tables[table] = {
            "schema": schema,
            "file": fm,
            "indexes": indexes,
            "_index_types": idx_types,
        }
        self._save_catalog()
        return f"Tabla {table} creada con {len(columns)} columnas"

    # ===================== Selección =====================

    def select(
        self,
        table: str,
        columns: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        SELECT unificado:
        - Usa índice solo si la columna de la condición tiene índice en el catálogo.
        - Soporta igualdad (eq) y rangos (lt, le, gt, ge, range).
        - Si no hay índice, hace full-scan.
        """
        if table not in self.tables:
            raise ValueError(f"Tabla {table} no existe")

        t = self.tables[table]
        fm: FileManager = t["file"]
        out: List[Dict[str, Any]] = []

        if where:
            col = where.get("column")
            val = where.get("value")
            idx = t["indexes"].get(col) # solo fijarse en la columna de la condición

            if where["type"] == "eq":
                if idx:
                    for off in idx.search(self._normalize(val)):
                        row = fm.read_record(off)
                        if row:
                            out.append(self._project(row, columns))
                            if limit and len(out) >= limit:
                                break
                else:
                    for row in fm.scan_all():
                        if row.get(col) == val:
                            out.append(self._project(row, columns))
                            if limit and len(out) >= limit:
                                break

            elif where["type"] in ["range"]:
                low, high = where.get("low"), where.get("high")
                if idx:
                    # usar índice si soporta búsqueda por rango
                    for off in idx.search_range(low, high):
                        row = fm.read_record(off)
                        if row:
                            out.append(self._project(row, columns))
                            if limit and len(out) >= limit:
                                break
                else:
                    # full-scan si no hay índice
                    for row in fm.scan_all():
                        if self._match_range(row.get(col), low, high):
                            out.append(self._project(row, columns))
                            if limit and len(out) >= limit:
                                break

        else:
            # full-scan sin condiciones
            for row in fm.scan_all():
                out.append(self._project(row, columns))
                if limit and len(out) >= limit:
                    break

        return out

    def _match_range(self, value: Any, low: Any, high: Any) -> bool:
        """Verifica si el valor está dentro del rango especificado (inclusive)."""
        # Si el valor es None, lo consideramos fuera de rango
        if value is None:
            return False

        # Asegurarnos de que low y high no sean None antes de hacer la comparación
        if low is not None and value < low:
            return False
        if high is not None and value > high:
            return False
        return True

    # ===================== Utilidades internas =====================

    @staticmethod
    def _normalize(v: Any) -> Any:
        """Normaliza el valor (si es string, elimina espacios y comillas)."""
        if isinstance(v, str):
            return v.strip().strip("'\"")
        return v

    def _project(self, row: Dict[str, Any], cols: Optional[List[str]]) -> Dict[str, Any]:
        """Proyección de columnas (si cols=["*"] o None, retorna la fila tal cual)."""
        if not cols or cols == ["*"]:
            return row
        return {c: row.get(c) for c in cols}

    def _iter_with_offsets(self, table: str) -> Iterator[Tuple[int, Dict[str, Any]]]:
        """Generador (offset, fila) sobre todo el archivo, útil para procesos como eliminar."""
        fm: FileManager = self.tables[table]["file"]
        yield from fm.scan_all_with_offsets()

    # ===================== Insert =====================

    def insert(self, table: str, row: Dict[str, Any]) -> int:
        """
        Inserta un registro en la tabla y lo agrega en todos los índices.
        """
        if table not in self.tables:
            raise ValueError(f"Tabla {table} no existe.")

        t = self.tables[table]
        fm: FileManager = t["file"]
        # Verificar si 'row' es un diccionario
        if not(isinstance(row, dict)):
            # Si no es un diccionario, lo convertimos a uno
            columns = t["schema"].columns  # Listado de columnas de la tabla
            values = row  # Lista de valores para insertar

            # Convertir la lista de valores en un diccionario usando las columnas
            record_dict = {col["name"]: val for col, val in zip(columns, values)}
        # Si ya es un diccionario, usamos tal cual
        record_dict = row
        print(record_dict)
        # 1) Guardar el registro en memoria secundaria y obtener offset
        off_set = fm.append_record(record_dict)

        # 2) Insertar el registro en todos los índices
        for col, idx in t["indexes"].items():
            col_value = record_dict.get(col)
            if col_value is not None:
                idx.insert(col_value, off_set)

        return off_set

    # ===================== Delete =====================
    def delete(self, table: str, where: Dict[str, Any]) -> int:
        """
        Elimina un registro de la tabla y actualiza todos los índices correspondientes.
        """
        if table not in self.tables:
            raise ValueError(f"La tabla {table} no existe.")

        t = self.tables[table]
        fm: FileManager = t["file"]
        deleted = 0

        off_set=t["indexes"][where["column"]].delete(where["value"])
        record=fm.read_record(off_set)

        # eliminar en todos los índices de la tabla
        for col, idx in t["indexes"].items():
            if where["column"] != col:
                idx.delete(record[col])
        fm.delete_record(off_set)
        deleted+=1

        # Después de eliminar el registro, actualizar el catálogo
        self._save_catalog()

        return deleted

    # ===================== Crear Índice =====================
    @staticmethod
    def get_column_format(column_type: str) -> str:
        """
        Convierte el tipo de columna (por ejemplo 'VARCHAR[100]', 'INT', 'DATE') a un formato
        adecuado para ser utilizado en la creación de índices.
        """
        if column_type.startswith("VARCHAR"):
            # Extraer el número de caracteres entre corchetes y devolver el formato
            length = int(column_type[len("VARCHAR["): -1])  # obtiene el número entre corchetes
            return f"{length}s"  # Retorna un formato de cadena de longitud variable, ej: 100s
        elif column_type == "INT":
            return "i"  # Representación de un entero
        elif column_type == "DATE":
            return "10s"  # Representación de fecha como una cadena de 10 caracteres
        elif column_type == "FLOAT":
            return "f"  # Representación de flotante
        else:
            raise ValueError(f"Tipo de columna no soportado: {column_type}")

    def create_index(self, table: str, column: str, index_type: str) -> str:
        """
        Crea un índice para una columna específica de una tabla ya creada.
        Se utiliza el tipo de columna transformado en un formato adecuado.
        """
        # Verificar que la tabla exista
        if table not in self.tables:
            raise ValueError(f"La tabla {table} no existe.")

        # Verificar que la columna exista
        if column not in [c["name"] for c in self.tables[table]["schema"].columns]:
            raise ValueError(f"La columna {column} no existe en {table}.")

        # Obtener el tipo de la columna (por ejemplo, 'VARCHAR[100]', 'INT', etc.)
        column_type = next(c["type"] for c in self.tables[table]["schema"].columns if c["name"] == column)

        # Convertir el tipo de columna a formato (como '10s', 'i', 'f', etc.)
        column_format = self.get_column_format(column_type)

        # Verificar que el tipo de índice es válido
        if index_type not in INDEX_TYPES:
            raise ValueError(f"Tipo de índice no soportado: {index_type}")

        # Instanciar el índice usando el formato adecuado de la columna
        ctor = INDEX_TYPES[index_type]
        idx = ctor(table, column_format)  # Pasamos el formato en lugar de la columna directamente

        # Registrar el índice en la tabla
        self.tables[table]["indexes"][column] = idx
        self.tables[table]["_index_types"][column] = index_type

        # Poblar el índice
        for off, row in self._iter_with_offsets(table):
            key = row.get(column)
            if key is not None:
                idx.insert(self._normalize(key), off)

        # Guardar el catálogo con el nuevo índice
        self._save_catalog()

        return f"Índice {index_type} creado en {table}({column}) con formato {column_format}"

