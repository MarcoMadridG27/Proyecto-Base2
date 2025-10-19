import os
import json
from typing import Any, Dict, List, Optional, Tuple, Iterator

from src.model.record import RecordSchema
from src.dbms.file_manager import FileManager

from src.dbms.sequential import SequentialFile
from src.dbms.isam import ISAMIndex
from src.dbms.extendible_hash import ExtendibleHash
from src.dbms.bplustree import BPlusTree
from src.dbms.Rtree import RTree  # RTree persistente (rtree/libspatialindex)

INDEX_TYPES = {
    "sequential": SequentialFile,
    "isam": ISAMIndex,
    "hash": ExtendibleHash,
    "btree": BPlusTree,
    "rtree": RTree,
}

# Ruta donde la clase RTree escribe sus archivos (coincidir con tu implementación)
RTREE_BASE_DIR = "/app/src/dbms/data_index"


class SchemaManager:
    """
    - Crea tablas e índices (1D y RTree multi-col).
    - INSERT/DELETE actualizando índices.
    - SELECT con eq/range + NEARBY/KNN (RTree).
    Persistencia en catalog.json: columns, index_types, index_names, spatial_map.

    Notas:
      * Para RTree multicol guardamos una "clave virtual" __rtree__(c1,c2,...)
        en index_types/index_names y en spatial_map (virt_key -> [cols]).
      * En el load, si abrir el RTree falla, recreamos sus archivos y repoblamos.
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.catalog_path = os.path.join(data_dir, "catalog.json")
        self.tables: Dict[str, Dict[str, Any]] = {}
        if os.path.exists(self.catalog_path):
            self._load_catalog()

    # ------------- helpers de ruta/rtree -------------

    @staticmethod
    def _rtree_prefix(table: str, idx_name: str) -> str:
        """
        Prefijo absoluto del índice espacial, consistente con la clase RTree.
        P.ej.: /app/src/dbms/data_index/{table}_{idx_name}
        """
        return os.path.join(RTREE_BASE_DIR, f"{table}_{idx_name or 'rtree'}")

    def _safe_open_rtree(self, table: str, cols: List[str], idx_name: str) -> Tuple[RTree, bool]:
        """
        Intenta abrir el RTree. Si falla por corrupción, borra .data/.index/.sqlite
        y lo recrea. Devuelve (rtree, rebuilt_flag).
        """
        dim = len(cols)
        rebuilt = False
        try:
            rt = RTree(table, f"{dim}f", idx_name)
            # Si tu clase RTree tiene 'count', úsalo para comprobar estado (opcional)
            try:
                _ = getattr(rt, "count")  # sólo para no romper si no existe
            except Exception:
                pass
            return rt, rebuilt
        except Exception:
            # recrear: borrar prefijos
            prefix = self._rtree_prefix(table, idx_name)
            for ext in (".data", ".index", ".sqlite"):
                try:
                    path = prefix + ext
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass
            # crear limpio
            rt = RTree(table, f"{dim}f", idx_name)
            rebuilt = True
            return rt, rebuilt

    # ---------------- Catalogo ----------------

    def _save_catalog(self) -> None:
        catalog: Dict[str, Any] = {}
        for t, info in self.tables.items():
            catalog[t] = {
                "columns": info["schema"].columns,
                "index_types": dict(info.get("_index_types", {})),
                "index_names": dict(info.get("_index_names", {})),
                "spatial_map": dict(info.get("_spatial_map", {})),  # virt_key -> [cols]
            }
        with open(self.catalog_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2)

    def _load_catalog(self) -> None:
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        for t, meta in catalog.items():
            schema = RecordSchema(meta["columns"])
            filepath = os.path.join(self.data_dir, f"{t}.dat")
            fm = FileManager(filepath, schema)

            idx_types: Dict[str, str] = meta.get("index_types", {})
            idx_names: Dict[str, str] = meta.get("index_names", {})
            spatial_map: Dict[str, List[str]] = meta.get("spatial_map", {})

            indexes: Dict[str, Any] = {}

            # 1) Índices 1D reales (skip rtree/virt_key aquí)
            for colkey, typ in idx_types.items():
                if colkey in spatial_map or typ == "rtree":
                    continue
                ctor = INDEX_TYPES.get(typ)
                if not ctor:
                    continue
                column = next((c for c in schema.columns if c["name"] == colkey), None)
                if column is None:
                    continue
                column_format = self.get_column_format(column["type"])
                idx_name = idx_names.get(colkey, colkey)
                indexes[colkey] = ctor(t, column_format, idx_name)

            # 2) RTree multicol (virt_key -> [cols])
            rebuilt_any = False
            for virt_key, cols in spatial_map.items():
                idx_name = idx_names.get(virt_key, virt_key)
                rt, rebuilt = self._safe_open_rtree(t, cols, idx_name)
                indexes[virt_key] = rt
                rebuilt_any = rebuilt_any or rebuilt

            # registrar tabla
            self.tables[t] = {
                "schema": schema,
                "file": fm,
                "indexes": indexes,
                "_index_types": dict(idx_types),
                "_index_names": dict(idx_names),
                "_spatial_map": dict(spatial_map),
            }

            # Si hubo recreación, repoblar sólo esos RTrees
            if spatial_map:
                for virt_key, cols in spatial_map.items():
                    idx = self.tables[t]["indexes"].get(virt_key)
                    # criterio: si el sqlite/items está vacío, repoblamos
                    needs_rebuild = False
                    try:
                        # Si la clase RTree trae 'count', úsala; si no, intentamos un intersection vacío
                        if hasattr(idx, "count"):
                            needs_rebuild = (idx.count() == 0)
                        else:
                            # si no hay count, probamos una intersección con una bbox imposible
                            # (debería devolver 0; no prueba existencia real, pero evita duplicar)
                            needs_rebuild = False
                    except Exception:
                        needs_rebuild = True

                    if needs_rebuild:
                        for off, row in self._iter_with_offsets(t):
                            try:
                                point = [float(row[c]) for c in cols]
                            except Exception:
                                continue
                            try:
                                idx.insert(point, off)
                            except Exception:
                                # Si falla una tupla errónea, seguimos con las demás
                                pass

    # ---------------- Crear tabla ----------------

    def create_table(
        self,
        table: str,
        columns: List[Dict[str, str]],
        index_map: Optional[Dict[str, str]] = None,
    ) -> str:
        if table in self.tables:
            return f"La tabla {table} ya existe"

        schema = RecordSchema(columns)
        path = os.path.join(self.data_dir, f"{table}.dat")
        fm = FileManager(path, schema)

        indexes: Dict[str, Any] = {}
        idx_types: Dict[str, str] = {}
        idx_names: Dict[str, str] = {}
        if index_map:
            for col, typ in index_map.items():
                ctor = INDEX_TYPES.get(typ)
                if not ctor:
                    raise ValueError(f"Tipo de índice no soportado: {typ}")
                if col not in [c["name"] for c in columns]:
                    raise ValueError(f"Columna {col} no existe en {table}")
                column_type = next(c["type"] for c in columns if c["name"] == col)
                column_format = self.get_column_format(column_type)
                idx = ctor(table, column_format, col)
                indexes[col] = idx
                idx_types[col] = typ
                idx_names[col] = col

        self.tables[table] = {
            "schema": schema,
            "file": fm,
            "indexes": indexes,
            "_index_types": idx_types,
            "_index_names": idx_names,
            "_spatial_map": {},
        }
        self._save_catalog()
        return f"Tabla {table} creada con {len(columns)} columnas"

    # ---------------- Crear índice (1D o RTree) ----------------

    def _index_name_exists(self, idx_name: str) -> bool:
        # revisa en memoria
        for _t, info in self.tables.items():
            names = info.get("_index_names", {})
            if idx_name in names.values():
                return True
        # revisa en disco
        if os.path.exists(self.catalog_path):
            with open(self.catalog_path, "r", encoding="utf-8") as f:
                cat = json.load(f)
            for _t, meta in cat.items():
                names = meta.get("index_names", {})
                if idx_name in names.values():
                    return True
        return False

    def create_index(self, table: str, columns: List[str], index_type: str, idx_name: str) -> str:
        """
        columns:
          - 1 col  -> sequential / isam / btree / hash
          - >=2 col -> rtree (espacial)
        """
        if table not in self.tables:
            raise ValueError(f"La tabla {table} no existe.")
        if index_type not in INDEX_TYPES:
            raise ValueError(f"Tipo de índice no soportado: {index_type}")
        if self._index_name_exists(idx_name):
            raise ValueError(f"El nombre de índice '{idx_name}' ya existe en el catálogo.")

        info = self.tables[table]
        schema_cols = [c["name"] for c in info["schema"].columns]

        # --- RTree multi-columna ---
        if index_type == "rtree":
            if len(columns) < 2:
                raise ValueError("RTree requiere >= 2 columnas")
            for c in columns:
                if c not in schema_cols:
                    raise ValueError(f"Columna {c} no existe en {table}")

            virt_key = f"__rtree__({','.join(columns)})"
            rtree, _ = self._safe_open_rtree(table, columns, idx_name)

            info["indexes"][virt_key] = rtree
            info.setdefault("_index_types", {})[virt_key] = index_type
            info.setdefault("_index_names", {})[virt_key] = idx_name
            info.setdefault("_spatial_map", {})[virt_key] = list(columns)

            # Poblar con los datos actuales
            for off, row in self._iter_with_offsets(table):
                try:
                    point = [float(row[c]) for c in columns]
                    rtree.insert(point, off)
                except Exception:
                    pass

            self._save_catalog()
            return f"Índice RTree '{idx_name}' creado en {table} sobre ({', '.join(columns)})"

        # --- Índices 1D ---
        if len(columns) != 1:
            raise ValueError("Índices 1D deben declararse con una sola columna")

        col = columns[0]
        if col not in schema_cols:
            raise ValueError(f"Columna {col} no existe en {table}")

        ctor = INDEX_TYPES[index_type]
        column_type = next(c["type"] for c in info["schema"].columns if c["name"] == col)
        column_format = self.get_column_format(column_type)
        idx = ctor(table, column_format, idx_name)

        info["indexes"][col] = idx
        info.setdefault("_index_types", {})[col] = index_type
        info.setdefault("_index_names", {})[col] = idx_name

        # Poblar 1D
        for off, row in self._iter_with_offsets(table):
            key = row.get(col)
            if key is not None:
                idx.insert(self._normalize(key), off)

        self._save_catalog()
        return f"Índice '{idx_name}' ({index_type}) creado en {table}({col}) con formato {column_format}"

    # ---------------- SELECT ----------------

    def select(
        self,
        table: str,
        columns: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if table not in self.tables:
            raise ValueError(f"Tabla {table} no existe")

        t = self.tables[table]
        fm: FileManager = t["file"]
        out: List[Dict[str, Any]] = []

        # Sin WHERE => full-scan
        if not where:
            for row in fm.scan_all():
                out.append(self._project(row, columns))
                if limit and len(out) >= limit:
                    break
            return out

        # --- Espaciales ---
        if where["type"] == "rt_range":
            cols = where["columns"]
            point = [float(x) for x in where["point"]]
            radius = float(where["radius"])
            virt_key = f"__rtree__({','.join(cols)})"

            idx = t["indexes"].get(virt_key)
            if not idx:
                raise ValueError(f"No existe índice RTree para {table}({','.join(cols)})")

            for off in idx.range_search(point, radius):
                row = fm.read_record(off)
                if row:
                    out.append(self._project(row, columns))
                    if limit and len(out) >= limit:
                        break
            return out

        if where["type"] == "rt_knn":
            cols = where["columns"]
            point = [float(x) for x in where["point"]]
            k = int(where["k"])
            virt_key = f"__rtree__({','.join(cols)})"

            idx = t["indexes"].get(virt_key)
            if not idx:
                raise ValueError(f"No existe índice RTree para {table}({','.join(cols)})")

            for off in idx.knn_search(point, k):
                row = fm.read_record(off)
                if row:
                    out.append(self._project(row, columns))
                    if limit and len(out) >= limit:
                        break
            return out

        # --- Igualdad 1D ---
        if where["type"] == "eq":
            col = where.get("column")
            val = self._normalize(where.get("value"))
            idx = t["indexes"].get(col)
            if idx:
                for off in idx.search(val):
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
            return out

        # --- Rango 1D ---
        if where["type"] == "range":
            col = where.get("column")
            low, high = where.get("low"), where.get("high")
            idx = t["indexes"].get(col)
            if idx:
                if isinstance(idx, ExtendibleHash) or not hasattr(idx, "search_range"):
                    raise ValueError("El índice Hash no soporta rangos")
                for off in idx.search_range(low, high):
                    row = fm.read_record(off)
                    if row:
                        out.append(self._project(row, columns))
                        if limit and len(out) >= limit:
                            break
            else:
                for row in fm.scan_all():
                    if self._match_range(row.get(col), low, high):
                        out.append(self._project(row, columns))
                        if limit and len(out) >= limit:
                            break
            return out

        # Caso no reconocido: devolvemos full-scan por compatibilidad
        for row in fm.scan_all():
            out.append(self._project(row, columns))
            if limit and len(out) >= limit:
                break
        return out

    # ---------------- Insert ----------------

    def insert(self, table: str, row: Any) -> int:
        if table not in self.tables:
            raise ValueError(f"Tabla {table} no existe.")

        t = self.tables[table]
        fm: FileManager = t["file"]

        # normalizar a dict
        if not isinstance(row, dict):
            columns = t["schema"].columns
            values = row
            record_dict = {col["name"]: val for col, val in zip(columns, values)}
        else:
            record_dict = row

        off_set = fm.append_record(record_dict)

        # 1D
        for colkey, idx in t["indexes"].items():
            if colkey.startswith("__rtree__("):
                continue
            col_value = record_dict.get(colkey)
            if col_value is not None:
                idx.insert(self._normalize(col_value), off_set)

        # RTrees
        spmap = t.get("_spatial_map", {})
        for virt_key, cols in spmap.items():
            idx = t["indexes"].get(virt_key)
            if not idx:
                continue
            try:
                point = [float(record_dict.get(c)) for c in cols]
                if any(v is None for v in point):
                    continue
                idx.insert(point, off_set)
            except Exception:
                pass

        return off_set

    # ---------------- Delete ----------------

    def delete(self, table: str, where: Dict[str, Any]) -> int:
        if table not in self.tables:
            raise ValueError(f"La tabla {table} no existe.")

        t = self.tables[table]
        fm: FileManager = t["file"]
        deleted = 0

        col = where.get("column")
        val = self._normalize(where.get("value"))
        driving_idx = t["indexes"].get(col)

        if driving_idx:
            offs = driving_idx.delete(val)  # offsets o [-1]
        else:
            offs = []
            for off, row in self._iter_with_offsets(table):
                if row.get(col) == val:
                    offs.append(off)

        if not offs or (len(offs) == 1 and offs[0] == -1):
            return 0

        rows_by_off = {off: fm.read_record(off) for off in offs}

        # limpiar índices secundarios (incluye RTrees)
        for off in offs:
            row = rows_by_off.get(off)
            if not row:
                continue
            for icol, idx in t["indexes"].items():
                if icol == col:
                    continue
                if isinstance(idx, RTree) or icol.startswith("__rtree__("):
                    try:
                        idx.delete(off)
                    except Exception:
                        pass
                else:
                    key = row.get(icol)
                    if key is not None:
                        try:
                            idx.delete(self._normalize(key))
                        except Exception:
                            pass

        # borrar del archivo
        for off in offs:
            fm.delete_record(off)
            deleted += 1

        self._save_catalog()
        return deleted

    # ---------------- Utilidades ----------------

    def close_all(self):
        """Cierra todos los índices (útil en on_shutdown para evitar corrupción)."""
        for tinfo in self.tables.values():
            for idx in tinfo.get("indexes", {}).values():
                closer = getattr(idx, "close", None)
                if callable(closer):
                    try:
                        closer()
                    except:
                        pass

    def _project(self, row: Dict[str, Any], cols: Optional[List[str]]) -> Dict[str, Any]:
        if not cols or cols == ["*"]:
            return row
        return {c: row.get(c) for c in cols}

    def _iter_with_offsets(self, table: str) -> Iterator[Tuple[int, Dict[str, Any]]]:
        fm: FileManager = self.tables[table]["file"]
        yield from fm.scan_all_with_offsets()

    @staticmethod
    def _normalize(v: Any) -> Any:
        if isinstance(v, str):
            return v.strip().strip("'\"")
        return v

    @staticmethod
    def _match_range(value: Any, low: Any, high: Any) -> bool:
        if value is None:
            return False
        if low is not None and value < low:
            return False
        if high is not None and value > high:
            return False
        return True

    # --- formatos para índices 1D ---

    @staticmethod
    def get_column_format(column_type: str) -> str:
        if column_type.startswith("VARCHAR"):
            length = int(column_type[len("VARCHAR["):-1])
            return f"{length}s"
        if column_type == "INT":
            return "i"
        if column_type == "DATE":
            return "10s"
        if column_type == "FLOAT":
            return "f"
        return "100s"
