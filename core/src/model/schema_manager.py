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
    Gestor multi-tabla minimalista:

      - create_table(table, columns, index_map):
          Crea el .dat (binario fijo) y los índices opcionales (vacíos).
      - insert(table, row):
          Appendea en el .dat (retorna offset) y actualiza TODOS los índices.
      - select_all(table, columns?, limit?):
          Full scan con proyección.
      - select(table, columns, where?, index?, limit?):
          Si where es igualdad {type:"eq",column,value} intenta usar índice; si no, full-scan.
      - delete(table, where):
          Igual que select, pero marcando registros como borrados.
      - create_index(table, column, index_type):
          Crea índice y lo puebla recorriendo el archivo con offsets.

    Catálogo persistido en data/catalog.json con:
      {
        "<tabla>": {
          "columns": [...],                # definición RecordSchema
          "index_types": {"col": "tipo"}   # metadatos para reconstruir índices
        }
      }

    En RAM guardamos:
      self.tables[tabla] = {
        "schema": RecordSchema,
        "file": FileManager,
        "indexes": {col: idx_obj},
        "_index_types": {col: "tipo"}
      }
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        parent_dir = os.path.dirname(self.data_dir)
        os.makedirs(parent_dir, exist_ok=True)
        self.catalog_path = os.path.join(self.data_dir, "catalog.json")
        self.tables: Dict[str, Dict[str, Any]] = {}  # ver estructura arriba

        # Si ya hay catálogo, reconstruye schemas, archivos e índices
        if os.path.exists(self.catalog_path):
            self._load_catalog()

    # ===================== Catálogo =====================

    def _save_catalog(self) -> None:
        """
        Persistimos SOLO metadatos seguros:
          - columns: definición del esquema
          - index_types: {col: "tipo"} para re-instanciar índices al iniciar
        (No se serializan objetos índice).
        """
        catalog: Dict[str, Any] = {}
        for t, info in self.tables.items():
            idx_types = dict(info.get("_index_types", {}))

            # Sanidad: si hay un índice instanciado sin tipo en idx_types es bug nuestro.
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
        Lee catalog.json y reconstruye:
          - RecordSchema
          - FileManager
          - Instancias de índices según 'index_types'
        """
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        for t, meta in catalog.items():
            # 1) schema + archivo .dat
            schema = RecordSchema(meta["columns"])
            filepath = os.path.join(self.data_dir, f"{t}.dat")
            fm = FileManager(filepath, schema)

            # 2) índices a partir de index_types
            idx_types: Dict[str, str] = meta.get("index_types", {})
            indexes: Dict[str, Any] = {}
            for col, typ in idx_types.items():
                ctor = INDEX_TYPES.get(typ)
                if not ctor:
                    raise ValueError(f"Tipo de índice desconocido en catálogo: {typ}")
                indexes[col] = ctor(t, col)

            # 3) registra en RAM
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
        Crea tabla:
          - Genera RecordSchema (tamaño fijo por fila).
          - Crea archivo binario <table>.dat (vacío).
          - Crea índices solicitados (vacíos) y guarda sus tipos en catálogo.

        columns: [{"name": "id", "type": "INT"}, ...]
        index_map: {"id": "btree", "fecha": "sequential"} (opcional)
        """
        if table in self.tables:
            return f"La tabla {table} ya existe"

        schema = RecordSchema(columns)
        path = os.path.join(self.data_dir, f"{table}.dat")
        fm = FileManager(path, schema)

        indexes: Dict[str, Any] = {}
        idx_types: Dict[str, str] = {}
        if index_map:
            for col, typ in index_map.items():
                # valida columna e índice
                if col not in [c["name"] for c in columns]:
                    raise ValueError(f"Columna {col} no existe en {table}")
                ctor = INDEX_TYPES.get(typ)
                if not ctor:
                    raise ValueError(f"Tipo de índice no soportado: {typ}")
                indexes[col] = ctor(table, col)
                idx_types[col] = typ

        self.tables[table] = {
            "schema": schema,
            "file": fm,
            "indexes": indexes,
            "_index_types": idx_types,
        }
        self._save_catalog()
        return f"Tabla {table} creada con {len(columns)} columnas"

    # ===================== Utilidades internas =====================

    @staticmethod
    def _normalize(v: Any) -> Any:
        """Si es string, recorta espacios y quita comillas; si no, lo deja igual."""
        if isinstance(v, str):
            return v.strip().strip("'\"")
        return v

    def _project(self, row: Dict[str, Any], cols: Optional[List[str]]) -> Dict[str, Any]:
        """Proyección de columnas (si cols=["*"] o None, retorna la fila tal cual)."""
        if not cols or cols == ["*"]:
            return row
        return {c: row.get(c) for c in cols}

    def _iter_with_offsets(self, table: str) -> Iterator[Tuple[int, Dict[str, Any]]]:
        """
        Generador (offset, fila) sobre todo el archivo.
        Usa FileManager.scan_all_with_offsets() para no cargar todo a RAM.
        """
        fm: FileManager = self.tables[table]["file"]
        yield from fm.scan_all_with_offsets()

    # ===================== Insert =====================

    def insert(self, table: str, row: Dict[str, Any]) -> int:
        """
        Inserta una fila y devuelve el offset físico.
        Luego inserta (key, offset) en TODOS los índices registrados de la tabla.
        """
        if table not in self.tables:
            raise ValueError(f"Tabla {table} no existe")

        t = self.tables[table]
        off = t["file"].append_record(row)

        for col, idx in t["indexes"].items():
            key = row.get(col)
            if key is not None:
                idx.add(self._normalize(key), off)

        return off

    # ===================== Select =====================

    def select_all(
        self,
        table: str,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Full-scan con proyección y LIMIT opcional."""
        if table not in self.tables:
            raise ValueError(f"Tabla {table} no existe")
        fm: FileManager = self.tables[table]["file"]

        out: List[Dict[str, Any]] = []
        for row in fm.scan_all():
            out.append(self._project(row, columns))
            if limit is not None and len(out) >= limit:
                break
        return out

    def _select_eq(
        self,
        table: str,
        column: str,
        value: Any,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Búsqueda por igualdad (col == value).
        Si existe índice en 'column': usa offsets y FileManager.read_at().
        Si no hay índice: full-scan filtrando.
        """
        t = self.tables[table]
        fm: FileManager = t["file"]
        idx = t["indexes"].get(column)

        # Ruta con índice
        if idx and hasattr(idx, "search") and hasattr(fm, "read_at"):
            out: List[Dict[str, Any]] = []
            for off in idx.search(self._normalize(value)):
                row = fm.read_record(off)  # puede ser None si fue borrado
                if row is None:
                    continue
                out.append(self._project(row, columns))
                if limit is not None and len(out) >= limit:
                    break
            return out

        # Ruta sin índice
        out: List[Dict[str, Any]] = []
        for row in fm.scan_all():
            if row.get(column) == value:
                out.append(self._project(row, columns))
                if limit is not None and len(out) >= limit:
                    break
        return out

    def select(
        self,
        table: str,
        columns: Optional[List[str]] = None,
        where: Optional[Any] = None,      # dict {"type":"eq",...} o string viejo
        index: Optional[str] = None,      # columna cuyo índice quieres priorizar
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        SELECT genérico:
          - Si 'where' es igualdad, intenta usar índice (si coincide con 'index'
            o si hay índice en esa columna). Si no, full-scan filtrando.
          - Si 'where' no es igualdad (o None), hace full-scan; como compatibilidad,
            si where es string complejo, usa eval() con '=' -> '==' (relajado).
        """
        if table not in self.tables:
            raise ValueError(f"Tabla {table} no existe")

        eq = where["column"], self._normalize(where["value"])
        if eq:
            col, val = eq
            # Si el usuario indicó "index=<col>" y existe ese índice, úsalo
            if index and col == index and index in self.tables[table]["indexes"]:
                return self._select_eq(table, col, val, columns, limit)
            # Si no se especificó index, pero hay índice en 'col', úsalo
            if col in self.tables[table]["indexes"]:
                return self._select_eq(table, col, val, columns, limit)
            # Igualdad sin índice -> full-scan filtrando
            fm: FileManager = self.tables[table]["file"]
            out: List[Dict[str, Any]] = []
            for row in fm.scan_all():
                if row.get(col) == val:
                    out.append(self._project(row, columns))
                    if limit is not None and len(out) >= limit:
                        break
            return out

        # Fallback: condición None o compleja (string). Compatibilidad con eval().
        fm: FileManager = self.tables[table]["file"]
        out: List[Dict[str, Any]] = []
        for row in fm.scan_all():
            try:
                if not where or eval(str(where).replace("=", "=="), {}, row):
                    out.append(self._project(row, columns))
                    if limit is not None and len(out) >= limit:
                        break
            except Exception:
                # condición malformada: ignora fila
                pass
        return out

    # ===================== Delete =====================

    def delete(self, table: str, where: Any) -> int:
        """
        DELETE por condición de igualdad.
        Si no es igualdad (o te llega string complejo), hace full-scan con eval().

        Retorna la cantidad de registros marcados como borrados (tombstone).
        """
        if table not in self.tables:
            raise ValueError(f"Tabla {table} no existe")

        t = self.tables[table]
        fm: FileManager = t["file"]
        eq = where["column"], self._normalize(where["value"])

        # Caso con igualdad col==val
        if eq:
            col, val = eq
            idx = t["indexes"].get(col)
            deleted = 0

            # Ruta con índice -> offsets directos
            if idx and hasattr(idx, "search"):
                for off in idx.search(self._normalize(val)):
                    if fm.delete_record(off):
                        deleted += 1
                return deleted

            # Ruta sin índice -> escaneo con offsets reales
            for off, row in self._iter_with_offsets(table):
                if row.get(col) == val and fm.delete_record(off):
                    deleted += 1
            return deleted

        # Fallback (compatibilidad): eval() en full-scan
        deleted = 0
        for off, row in self._iter_with_offsets(table):
            try:
                if eval(str(where).replace("=", "=="), {}, row) and fm.delete_record(off):
                    deleted += 1
            except Exception:
                pass
        return deleted

    # ===================== Índices =====================

    def create_index(self, table: str, column: str, index_type: str) -> str:
        """
        Crea índice en 'column' y lo puebla con offsets actuales.
        Persiste el tipo en el catálogo para reconstruir en el próximo arranque.
        """
        if table not in self.tables:
            raise ValueError(f"Tabla {table} no existe")
        if index_type not in INDEX_TYPES:
            raise ValueError(f"Tipo de índice no soportado: {index_type}")
        if column not in [c["name"] for c in self.tables[table]["schema"].columns]:
            raise ValueError(f"La columna {column} no existe en {table}")

        ctor = INDEX_TYPES[index_type]
        idx = ctor(table, column)
        self.tables[table]["indexes"][column] = idx
        self.tables[table]["_index_types"][column] = index_type

        # Poblar con todos los registros actuales (streaming, con offsets)
        for off, row in self._iter_with_offsets(table):
            key = row.get(column)
            if key is not None:
                idx.add(self._normalize(key), off)

        self._save_catalog()
        return f"Índice {index_type} creado en {table}({column})"
