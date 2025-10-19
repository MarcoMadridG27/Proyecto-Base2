# core/schema_manager.py
import os
import re
import json
import shutil
from src.record import RecordSchema
from src.dbms.file_manager import FileManager
from src.dbms.sequential import SequentialFile
from src.dbms.sequential_index import SequentialIndex
from src.dbms.isam import ISAMMultinivel
from src.dbms.extendible_hash import ExtendibleHash
from src.dbms.bplustree import BPlusTree
from src.dbms.rtree import RTree
from src.dbms.kdtree import KDTree
from src.dbms.file_manager import reset_disk_accesses, get_disk_accesses


class SchemaManager:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.catalog_path = os.path.join(self.data_dir, "catalog.json")
        self.tables = {}  # {table_name: {"schema": RecordSchema, "file": FileManager, "indexes": {col: idx}}}

        # Restaurar catálogo si existe
        if os.path.exists(self.catalog_path):
            self._load_catalog()

        # debug flag: enable detailed condition-eval prints when DB_DEBUG=1
        self.debug = os.environ.get("DB_DEBUG", "0") == "1"

    # ---------------------------
    # Persistencia del catálogo
    # ---------------------------
    def _save_catalog(self):
        catalog = {}
        for tname, tinfo in self.tables.items():
            # store indexes as a mapping column -> index_type for reliable reload
            idx_map = {}
            for col, idx_obj in tinfo["indexes"].items():
                itype = None
                if isinstance(idx_obj, SequentialIndex):
                    itype = "sequential"
                elif isinstance(idx_obj, ISAMMultinivel):
                    itype = "isam"
                elif isinstance(idx_obj, BPlusTree):
                    itype = "btree"
                else:
                    # fallback by class name
                    cname = idx_obj.__class__.__name__.lower()
                    if "extend" in cname or "hash" in cname:
                        itype = "hash"
                    elif "rtree" in cname:
                        itype = "rtree"
                    else:
                        itype = "unknown"

                idx_map[col] = itype

            catalog[tname] = {
                "columns": tinfo["schema"].columns,
                "indexes": idx_map,
            }
        with open(self.catalog_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2)

    def _load_catalog(self):
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        for tname, meta in catalog.items():
            schema = RecordSchema(meta["columns"])
            filepath = os.path.join(self.data_dir, f"{tname}.dat")
            file_manager = FileManager(filepath, schema)

            indexes = {}
            # meta["indexes"] could be either a list (old format) or a mapping col->type
            idx_meta = meta.get("indexes", {})
            if isinstance(idx_meta, list):
                # legacy: assume hash
                for col in idx_meta:
                    index_dir = os.path.join(self.data_dir, "idx_hash", tname, col)
                    os.makedirs(index_dir, exist_ok=True)
                    indexes[col] = ExtendibleHash(tname, col, data_dir=index_dir)
            elif isinstance(idx_meta, dict):
                for col, itype in idx_meta.items():
                    index_dir = os.path.join(self.data_dir, f"idx_{itype}", tname, col)
                    os.makedirs(index_dir, exist_ok=True)
                    if itype == "sequential":
                        indexes[col] = SequentialIndex(tname, col, data_dir=index_dir)
                    elif itype == "isam":
                        indexes[col] = ISAMMultinivel(
                            os.path.join(index_dir, "nivel_1.dat"),
                            os.path.join(index_dir, "nivel_2.dat"),
                            os.path.join(index_dir, "nivel_3.dat"),
                            os.path.join(index_dir, "overflow.dat"),
                        )
                    elif itype == "btree":
                        indexes[col] = BPlusTree(os.path.join(index_dir, "btree.idx"))
                    elif itype == "hash":
                        indexes[col] = ExtendibleHash(tname, col, data_dir=index_dir)
                    elif itype == "rtree":
                        # support joined column names for spatial indexes like 'x__y' or 'lat__lon__alt'
                        cols = col.split("__") if "__" in col else [col]
                        dimension = 3 if len(cols) >= 3 else 2
                        idx = RTree(tname, col, data_dir=index_dir, dimension=dimension)
                        try:
                            idx._columns = cols
                        except Exception:
                            pass
                        indexes[col] = idx
                    elif itype == "kdtree":
                        # kdtree uses a persistent pickle file inside index_dir
                        dimension = 3 if "__" in col and len(col.split("__")) >= 3 else 2
                        try:
                            indexes[col] = KDTree(tname, col, data_dir=index_dir, dimension=dimension)
                        except Exception:
                            indexes[col] = KDTree(tname, col, data_dir=index_dir, dimension=dimension)
                    else:
                        # unknown: try extendible hash as a safe default
                        indexes[col] = ExtendibleHash(tname, col, data_dir=index_dir)

            self.tables[tname] = {
                "schema": schema,
                "file": file_manager,
                "indexes": indexes,
            }

        print(f"[DEBUG] Catálogo restaurado con {len(self.tables)} tablas")

    def reload_catalog(self):
        """Force reloading catalog.json from disk and reinstantiate tables/indexes."""
        self.tables = {}
        if os.path.exists(self.catalog_path):
            self._load_catalog()
        else:
            print("[WARN] catalog.json not found during reload")

    def drop_index(self, table_name: str, column: str):
        """Remove index files for a given table.column and update in-memory/catalog.

        This removes directories under data/idx_* for the table/column, removes the index
        object from memory, and updates catalog.json.
        """
        if table_name not in self.tables:
            raise ValueError(f"Tabla {table_name} no existe")

        idxs = self.tables[table_name].get("indexes", {})
        if column not in idxs:
            raise ValueError(f"No index on column {column} for table {table_name}")

        # If an index object exists in memory, try to close it to release file handles
        try:
            idx_obj = self.tables[table_name]["indexes"].get(column)
            if idx_obj is not None and hasattr(idx_obj, "close"):
                try:
                    idx_obj.close()
                except Exception:
                    pass
        except Exception:
            pass

        # remove on-disk index directories across possible index types
        for _t in ("sequential", "isam", "btree", "hash", "rtree"):
            path = os.path.join(self.data_dir, f"idx_{_t}", table_name, column)
            if os.path.exists(path):
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                    else:
                        # remove tree
                        import shutil
                        shutil.rmtree(path)
                except Exception as e:
                    print(f"[WARN] Failed to remove index path {path}: {e}")

        # Remove index object from memory and persist catalog
        try:
            del self.tables[table_name]["indexes"][column]
        except Exception:
            pass
        self._save_catalog()

    # ---------------------------
    # Crear tabla
    # ---------------------------
    def create_table(self, table_name, columns, index_map=None):
        schema = RecordSchema(columns)
        filepath = os.path.join(self.data_dir, f"{table_name}.dat")
        file_manager = FileManager(filepath, schema)

        indexes = {}
        if index_map:
            for col, idx_type in index_map.items():
                # uniform index directory: data/idx_{type}/{table}/{column}/...
                index_dir = os.path.join(self.data_dir, f"idx_{idx_type}", table_name, col)
                os.makedirs(index_dir, exist_ok=True)
                if idx_type == "sequential":
                    indexes[col] = SequentialIndex(table_name, col, data_dir=index_dir)
                elif idx_type == "isam":
                    indexes[col] = ISAMMultinivel(
                        os.path.join(index_dir, "nivel_1.dat"),
                        os.path.join(index_dir, "nivel_2.dat"),
                        os.path.join(index_dir, "nivel_3.dat"),
                        os.path.join(index_dir, "overflow.dat"),
                    )
                elif idx_type == "btree":
                    idx_file = os.path.join(index_dir, "btree.idx")
                    indexes[col] = BPlusTree(idx_file)
                elif idx_type == "hash":
                    indexes[col] = ExtendibleHash(table_name, col, data_dir=index_dir)
                elif idx_type == "rtree":
                    idx = RTree(table_name, col, data_dir=index_dir)
                    try:
                        idx._columns = [col]
                    except Exception:
                        pass
                    indexes[col] = idx
                else:
                    indexes[col] = ExtendibleHash(table_name, col, data_dir=index_dir)

        self.tables[table_name] = {
            "schema": schema,
            "file": file_manager,
            "indexes": indexes,
        }

        self._save_catalog()
        return f"Tabla {table_name} creada con {len(columns)} columnas"

    # ---------------------------
    # Insertar registro
    # ---------------------------
    def insert(self, table_name, values):
        table = self.tables[table_name]
        schema, file_manager, indexes = table["schema"], table["file"], table["indexes"]

        if isinstance(values, list):
            record_dict = {}
            for i, col_def in enumerate(schema.columns):
                col_name = col_def["name"]
                if i < len(values):
                    val = values[i]
                    if isinstance(val, str):
                        val = val.strip().strip("'\"")
                    record_dict[col_name] = val
                else:
                    record_dict[col_name] = None
        else:
            record_dict = values

        offset = file_manager.append_record(record_dict)

        for col, index in indexes.items():
            # Support for RTree multi-column indexes: index._columns can be present
            key = None
            if hasattr(index, "_columns"):
                cols = index._columns
                parts = [record_dict.get(c) for c in cols]
                # if all parts are None, skip
                if all(p is None for p in parts):
                    continue
                # sanitize string parts
                parts = [p.strip().strip("'\"") if isinstance(p, str) else p for p in parts]
                # use tuple for composite spatial key
                key = tuple(parts)
            else:
                key = record_dict.get(col)
                if key is None:
                    continue
                if isinstance(key, str):
                    key = key.strip().strip("'\"")

            # Índice simple almacena offset del .dat
            if hasattr(index, "add"):
                index.add(key, offset)

        return {"success": True, "message": f"Registro insertado en {table_name}", "offset": offset}

    # ---------------------------
    # Select
    # ---------------------------
    def select(self, table_name, columns, condition=None, index=None, limit=None, index_hint=None):
        table = self.tables[table_name]
        schema, file_manager, indexes = table["schema"], table["file"], table["indexes"]

        # Spatial query detection: pattern like "col IN ([x, y], radius)"
        if isinstance(condition, str) and condition.strip():
            m = re.match(r"\s*([A-Za-z0-9_]+)\s+in\s*\(\s*\[?([^\]]+)\]?\s*,\s*([0-9\.]+)\s*\)\s*$", condition, re.I)
            if m:
                col = m.group(1)
                point_str = m.group(2)
                radius = float(m.group(3))
                try:
                    point = [float(x.strip()) for x in point_str.split(",")]
                except Exception:
                    point = [0.0, 0.0]

                # find rtree index covering this column
                r_idx = None
                # direct index under same name
                if col in indexes and "rtree" in indexes[col].__class__.__name__.lower():
                    r_idx = indexes[col]
                else:
                    # search for any rtree index whose _columns contains this column
                    for k, v in indexes.items():
                        try:
                            if "rtree" in v.__class__.__name__.lower():
                                cols = getattr(v, "_columns", None)
                                if cols and col in cols:
                                    r_idx = v
                                    break
                        except Exception:
                            continue

                if r_idx is not None:
                    offsets = r_idx.range_search(point, radius)
                    # If no results, try swapped coordinate order (users may supply [lat, lon])
                    if (not offsets or len(offsets) == 0) and isinstance(point, (list, tuple)) and len(point) >= 2:
                        try:
                            swapped = [point[1], point[0]]
                            print(f"[DEBUG] spatial search returned 0; retrying with swapped coords {swapped}")
                            offsets = r_idx.range_search(swapped, radius)
                        except Exception:
                            pass
                    results = []
                    for off in offsets:
                        rec = file_manager.read_record(off)
                        if not rec:
                            continue
                        rec_dict = rec if isinstance(rec, dict) else {
                            schema.columns[i]["name"]: rec[i] for i in range(len(schema.columns))
                        }
                        # normalize coordinates: if index covers x/y or joined cols, add 'coordenadas'
                        try:
                            cols = getattr(r_idx, '_columns', None)
                            if cols and len(cols) >= 2:
                                lon_val = rec_dict.get(cols[0])
                                lat_val = rec_dict.get(cols[1])
                                if lon_val is not None and lat_val is not None:
                                    rec_dict['coordenadas'] = [float(lon_val), float(lat_val)]
                        except Exception:
                            pass
                        if columns and columns != ["*"]:
                            projected = {c: rec_dict.get(c) for c in columns}
                            results.append(projected)
                        else:
                            results.append(rec_dict)
                        if limit is not None and len(results) >= limit:
                            break
                    return results
                else:
                    # try to auto-create a composite rtree index if table has coordinate columns
                    cols = [c["name"] for c in self.tables[table_name]["schema"].columns]
                    low = [c.lower() for c in cols]
                    pair = None
                    for a, b in [("x", "y"), ("y", "x"), ("lat", "lon"), ("lon", "lat"), ("latitude", "longitude"), ("longitude", "latitude"), ("lng", "lat")]:
                        if a in low and b in low:
                            pair = (cols[low.index(a)], cols[low.index(b)])
                            break

                    if pair:
                        # create joined index name by calling create_index; pass the first column as trigger
                        try:
                            # This will create an index at data/idx_rtree/<table>/<joined>
                            self.create_index(table_name, pair[0], "rtree")
                            # reload the index object
                            joined = "__".join([pair[0], pair[1]])
                            r_idx = self.tables[table_name]["indexes"].get(joined)
                            if r_idx is not None:
                                offsets = r_idx.range_search(point, radius)
                                # retry with swapped coords if none found
                                if (not offsets or len(offsets) == 0) and isinstance(point, (list, tuple)) and len(point) >= 2:
                                    try:
                                        swapped = [point[1], point[0]]
                                        print(f"[DEBUG] spatial search (post-build) returned 0; retrying with swapped coords {swapped}")
                                        offsets = r_idx.range_search(swapped, radius)
                                    except Exception:
                                        pass
                                results = []
                                for off in offsets:
                                    rec = file_manager.read_record(off)
                                    if not rec:
                                        continue
                                    rec_dict = rec if isinstance(rec, dict) else {
                                        schema.columns[i]["name"]: rec[i] for i in range(len(schema.columns))
                                    }
                                    try:
                                        cols = getattr(r_idx, '_columns', None)
                                        if cols and len(cols) >= 2:
                                            lon_val = rec_dict.get(cols[0])
                                            lat_val = rec_dict.get(cols[1])
                                            if lon_val is not None and lat_val is not None:
                                                rec_dict['coordenadas'] = [float(lon_val), float(lat_val)]
                                    except Exception:
                                        pass
                                    if columns and columns != ["*"]:
                                        projected = {c: rec_dict.get(c) for c in columns}
                                        results.append(projected)
                                    else:
                                        results.append(rec_dict)
                                    if limit is not None and len(results) >= limit:
                                        break
                                return results
                        except Exception:
                            pass
                    # If we reach here and no rtree index could be used or builder failed,
                    # fall back to a full scan spatial filter (Euclidean distance) so query returns results.
                    try:
                        # assume 'col' is the column name holding coordinates (array or string) or one of pair columns
                        def parse_point_from_record(rec, column_name):
                            val = rec.get(column_name)
                            if val is None:
                                return None
                            if isinstance(val, (list, tuple)) and len(val) >= 2:
                                return float(val[0]), float(val[1])
                            if isinstance(val, str):
                                s = val.strip()
                                if s.startswith("[") and s.endswith("]"):
                                    s = s[1:-1]
                                parts = [p.strip() for p in s.split(",") if p.strip()]
                                if len(parts) >= 2:
                                    return float(parts[0]), float(parts[1])
                                return None
                            return None

                        # try parse point from 'col' (the queried column) or from the first coordinate column in table
                        results = []
                        target = tuple(point)
                        for rec in file_manager.scan_all():
                            rec_dict = rec if isinstance(rec, dict) else {schema.columns[i]["name"]: rec[i] for i in range(len(schema.columns))}
                            pt = parse_point_from_record(rec_dict, col)
                            if pt is None:
                                # try common paired columns
                                if pair:
                                    try:
                                        px = float(rec_dict.get(pair[0]))
                                        py = float(rec_dict.get(pair[1]))
                                        pt = (px, py)
                                    except Exception:
                                        pt = None
                            if pt is None:
                                continue
                            dx = pt[0] - target[0]
                            dy = pt[1] - target[1]
                            import math
                            if math.hypot(dx, dy) <= radius:
                                # attach normalized coordenadas
                                try:
                                    rec_dict['coordenadas'] = [float(pt[0]), float(pt[1])]
                                except Exception:
                                    pass
                                if columns and columns != ["*"]:
                                    projected = {c: rec_dict.get(c) for c in columns}
                                    results.append(projected)
                                else:
                                    results.append(rec_dict)
                                if limit is not None and len(results) >= limit:
                                    break
                        return results
                    except Exception:
                        pass

        # Intento: si hay condición simple col = value y existe índice, usarlo
        # choose index column: prefer index_hint, then equality column, then any available
        chosen_col = None
        if index_hint and index_hint in indexes:
            chosen_col = index_hint
        else:
            eq_col, eq_val = self._parse_simple_equality(condition) if condition else (None, None)
            if eq_col and eq_col in indexes and hasattr(indexes[eq_col], "find"):
                chosen_col = eq_col

        if chosen_col and hasattr(indexes[chosen_col], "find"):
            # equality query using chosen index
            eq_val = eq_val if 'eq_val' in locals() else None
            offsets = indexes[chosen_col].find(eq_val)
            results = []
            for off in offsets:
                rec = file_manager.read_record(off)
                if not rec:
                    continue
                rec_dict = rec if isinstance(rec, dict) else {
                    schema.columns[i]["name"]: rec[i] for i in range(len(schema.columns))
                }
                if columns and columns != ["*"]:
                    projected = {col: rec_dict.get(col) for col in columns}
                    results.append(projected)
                else:
                    results.append(rec_dict)
                if limit is not None and len(results) >= limit:
                    break
            return results

        # Rango: si la condición es BETWEEN en la misma columna con índice secuencial
        if condition and isinstance(condition, str) and "between" in condition.lower():
            try:
                parts = condition.lower().split()
                # form: col between a and b
                col = parts[0]
                if col in indexes and hasattr(indexes[col], "range_search"):
                    a = parts[2].strip("'\"")
                    b = parts[4].strip("'\"")
                    offsets = indexes[col].range_search(a, b)
                    results = []
                    for off in offsets:
                        rec = file_manager.read_record(off)
                        if not rec:
                            continue
                        rec_dict = rec if isinstance(rec, dict) else {
                            schema.columns[i]["name"]: rec[i] for i in range(len(schema.columns))
                        }
                        if columns and columns != ["*"]:
                            projected = {c: rec_dict.get(c) for c in columns}
                            results.append(projected)
                        else:
                            results.append(rec_dict)
                        if limit is not None and len(results) >= limit:
                            break
                    return results
            except Exception as e:
                print(f"[WARN] BETWEEN parsing failed: {e}")

        # Fallback: full scan
        results = []
        for rec in file_manager.scan_all():
            rec_dict = rec if isinstance(rec, dict) else {
                schema.columns[i]["name"]: rec[i] for i in range(len(schema.columns))
            }
            if isinstance(condition, str) and condition.strip():
                try:
                    # Evaluar condición con conversión de tipos
                    if "=" in condition:
                        parts = condition.split("=", 1)
                        col = parts[0].strip()
                        val = parts[1].strip().strip("'\"")
                        
                        # Comparar con conversión de tipos
                        record_val = rec_dict.get(col)
                        if record_val is not None:
                            # Intentar comparación numérica si ambos son números
                            try:
                                if str(record_val).isdigit() and val.isdigit():
                                    if int(record_val) != int(val):
                                        continue
                                elif str(record_val).replace('.', '').isdigit() and val.replace('.', '').isdigit():
                                    if float(record_val) != float(val):
                                        continue
                                elif str(record_val) != val:
                                    continue
                            except:
                                if str(record_val) != val:
                                    continue
                        else:
                            continue
                    else:
                        # Fallback a eval para condiciones complejas
                        if not eval(condition.replace("=", "=="), {}, rec_dict):
                            continue
                except Exception as e:
                    if self.debug:
                        print(f"Error evaluando condición: {e}")
                    continue
            if columns and columns != ["*"]:
                projected = {col: rec_dict.get(col) for col in columns}
                results.append(projected)
            else:
                results.append(rec_dict)
            if limit is not None and len(results) >= limit:
                break
        return results

    # ---------------------------
    # Delete
    # ---------------------------
    def delete(self, table_name, condition):
        table = self.tables[table_name]
        schema, file_manager = table["schema"], table["file"]

        deleted = 0
        cond = condition.strip() if isinstance(condition, str) else condition
        # normalize: remove trailing semicolon
        if isinstance(cond, str) and cond.endswith(";"):
            cond = cond[:-1]

        for off, rec in self._iter_with_offsets(table_name):
            try:
                rec_dict = rec if isinstance(rec, dict) else {schema.columns[i]["name"]: rec[i] for i in range(len(schema.columns))}

                # simple BETWEEN handling: "col BETWEEN a AND b"
                if isinstance(cond, str) and "between" in cond.lower():
                    parts = cond.lower().split()
                    # expect: col between a and b
                    col = parts[0]
                    a = parts[2].strip("'\"")
                    b = parts[4].strip("'\"")
                    rv = rec_dict.get(col)
                    if rv is None:
                        continue
                    try:
                        rvf = float(rv)
                        af = float(a)
                        bf = float(b)
                        if af <= rvf <= bf:
                            file_manager.delete_record(off)
                            deleted += 1
                    except Exception:
                        # non-numeric comparison
                        if str(rv) >= a and str(rv) <= b:
                            file_manager.delete_record(off)
                            deleted += 1
                    continue

                # simple equality/comparison handling
                if isinstance(cond, str) and any(op in cond for op in [">=", "<=", ">", "<", "="]):
                    c = cond
                    # equality
                    if "=" in c and "==" not in c and ">=" not in c and "<=" not in c:
                        parts = c.split("=", 1)
                        col = parts[0].strip()
                        val = parts[1].strip().strip("'\"")
                        rv = rec_dict.get(col)
                        if rv is None:
                            continue
                        try:
                            if str(rv).replace('.', '', 1).isdigit() and val.replace('.', '', 1).isdigit():
                                if float(rv) == float(val):
                                    file_manager.delete_record(off)
                                    deleted += 1
                            else:
                                if str(rv) == val:
                                    file_manager.delete_record(off)
                                    deleted += 1
                        except Exception:
                            if str(rv) == val:
                                file_manager.delete_record(off)
                                deleted += 1
                        continue

                    # >=, <=, >, <
                    for op in ([">=", ">", "<=", "<"]):
                        if op in c:
                            parts = c.split(op, 1)
                            col = parts[0].strip()
                            val = parts[1].strip().strip("'\"")
                            rv = rec_dict.get(col)
                            if rv is None:
                                break
                            try:
                                rvf = float(rv)
                                vf = float(val)
                                ok = False
                                if op == ">=":
                                    ok = rvf >= vf
                                elif op == ">":
                                    ok = rvf > vf
                                elif op == "<=":
                                    ok = rvf <= vf
                                elif op == "<":
                                    ok = rvf < vf
                                if ok:
                                    file_manager.delete_record(off)
                                    deleted += 1
                            except Exception:
                                # string compare
                                sval = str(rv)
                                if op == ">=":
                                    ok = sval >= val
                                elif op == ">":
                                    ok = sval > val
                                elif op == "<=":
                                    ok = sval <= val
                                elif op == "<":
                                    ok = sval < val
                                if ok:
                                    file_manager.delete_record(off)
                                    deleted += 1
                            break

                else:
                    # fallback to eval (with = -> ==)
                    try:
                        if isinstance(cond, str) and eval(cond.replace("=", "=="), {}, rec_dict):
                            file_manager.delete_record(off)
                            deleted += 1
                    except Exception:
                        continue
            except Exception as e:
                print(f"Error during delete evaluation: {e}")
                continue
        return f"{deleted} registros eliminados de {table_name}"
    
    # ---------------------------
    # Crear índice
    # ---------------------------
    
    def create_index(self, table_name, column, index_type):
        if table_name not in self.tables:
            raise ValueError(f"Tabla {table_name} no existe")

        if column not in [c["name"] for c in self.tables[table_name]["schema"].columns]:
            raise ValueError(f"La columna {column} no existe en la tabla {table_name}")


        # Remove any existing index files for this table/column across index types
        # First, close and remove any in-memory index objects that reference this column
        try:
            idxs = self.tables[table_name].get("indexes", {})
            for key in list(idxs.keys()):
                obj = idxs.get(key)
                try:
                    cols = getattr(obj, "_columns", None)
                except Exception:
                    cols = None
                # if exact key matches, or this column is part of a composite index, close and remove
                if key == column or (cols and column in cols) or ("__" in key and column in key.split("__")):
                    try:
                        if hasattr(obj, "close"):
                            obj.close()
                    except Exception:
                        pass
                    try:
                        del self.tables[table_name]["indexes"][key]
                    except Exception:
                        pass
        except Exception:
            pass

        # remove on-disk index directories across possible index types
        for _t in ("sequential", "isam", "btree", "hash", "rtree"):
            old_dir = os.path.join(self.data_dir, f"idx_{_t}", table_name, column)
            if os.path.exists(old_dir):
                try:
                    if os.path.isfile(old_dir):
                        os.remove(old_dir)
                    else:
                        shutil.rmtree(old_dir)
                except Exception as e:
                    print(f"[WARN] Failed to remove old index dir {old_dir}: {e}")

        # Build index files under data/idx_{type}/{table}/{column}/
        index_dir = os.path.join(self.data_dir, f"idx_{index_type}", table_name, column)
        os.makedirs(index_dir, exist_ok=True)

        if index_type == "sequential":
            idx = SequentialIndex(table_name, column, data_dir=index_dir)
            for off, rec in self._iter_with_offsets(table_name):
                key = rec.get(column)
                if key is not None:
                    if isinstance(key, str):
                        key = key.strip().strip("'\"")
                    idx.add(key, off)
            # ensure main area is reconstructed/sorted after bulk build
            try:
                idx.reconstruct()
            except Exception:
                pass

        elif index_type == "isam":
            idx = ISAMMultinivel(
                os.path.join(index_dir, "nivel_1.dat"),
                os.path.join(index_dir, "nivel_2.dat"),
                os.path.join(index_dir, "nivel_3.dat"),
                os.path.join(index_dir, "overflow.dat"),
            )
            for off, rec in self._iter_with_offsets(table_name):
                try:
                    idx.insert(rec)
                except Exception as e:
                    print(f"[WARN] ISAM insert error: {e}")

        elif index_type == "btree":
            idx_file = os.path.join(index_dir, "btree.idx")
            idx = BPlusTree(idx_file)
            for off, rec in self._iter_with_offsets(table_name):
                key = rec.get(column)
                if key is not None:
                    if isinstance(key, str):
                        try:
                            key = int(key)
                        except:
                            pass
                    try:
                        idx.insert(key, off)
                    except Exception as e:
                        print(f"[WARN] BPlusTree insert error: {e}")

        elif index_type == "hash":
            idx = ExtendibleHash(table_name, column, data_dir=index_dir)
            try:
                idx.clear()
            except Exception:
                pass
            for off, rec in self._iter_with_offsets(table_name):
                key = rec.get(column)
                if key is not None:
                    if isinstance(key, str):
                        key = key.strip().strip("'\"")
                    idx.add(key, off)

        elif index_type == "rtree":
            # For RTree we try to auto-detect spatial coordinate columns and allow multi-column indexes.
            # Common names: x,y ; lat,lon ; lon,lat ; latitude,longitude ; lng,lat ; and optionally z/alt for 3D.
            cols = [c["name"] for c in self.tables[table_name]["schema"].columns]
            lower = [c.lower() for c in cols]

            def find_pair(a, b):
                if a in lower and b in lower:
                    return (cols[lower.index(a)], cols[lower.index(b)])
                return None

            pair = None
            for a, b in [("x", "y"), ("y", "x"), ("lat", "lon"), ("lon", "lat"), ("latitude", "longitude"), ("longitude", "latitude"), ("lng", "lat")]:
                p = find_pair(a, b)
                if p:
                    pair = p
                    break

            # detect z/alt column
            zcol = None
            for zcand in ("z", "alt", "altitude"):
                if zcand in lower:
                    zcol = cols[lower.index(zcand)]
                    break

            chosen_cols = None
            if pair:
                chosen_cols = list(pair)
                if zcol:
                    chosen_cols.append(zcol)
            else:
                # fallback: if user supplied a column that looks like coords array, keep it
                if column in cols:
                    chosen_cols = [column]
                else:
                    # pick first two numeric-like columns as fallback
                    chosen_cols = cols[:2] if len(cols) >= 2 else cols

            # create readable directory name from joined column names
            joined = "__".join(chosen_cols)
            index_dir = os.path.join(self.data_dir, f"idx_{index_type}", table_name, joined)
            os.makedirs(index_dir, exist_ok=True)

            # dimension = 3 if we have 3 columns, else 2
            dimension = 3 if len(chosen_cols) >= 3 else 2
            idx = RTree(table_name, joined, data_dir=index_dir, dimension=dimension)
            # record which columns this index covers so insert/select can use them
            try:
                idx._columns = chosen_cols
            except Exception:
                pass
        elif index_type == "kdtree":
            # create a KD-Tree index (pure Python) stored under data/idx_kdtree/<table>/<column>/
            # Use same auto-detection logic as rtree for chosen columns
            cols = [c["name"] for c in self.tables[table_name]["schema"].columns]
            lower = [c.lower() for c in cols]

            def find_pair(a, b):
                if a in lower and b in lower:
                    return (cols[lower.index(a)], cols[lower.index(b)])
                return None

            pair = None
            for a, b in [("x", "y"), ("y", "x"), ("lat", "lon"), ("lon", "lat"), ("latitude", "longitude"), ("longitude", "latitude"), ("lng", "lat")]:
                p = find_pair(a, b)
                if p:
                    pair = p
                    break

            zcol = None
            for zcand in ("z", "alt", "altitude"):
                if zcand in lower:
                    zcol = cols[lower.index(zcand)]
                    break

            chosen_cols = None
            if pair:
                chosen_cols = list(pair)
                if zcol:
                    chosen_cols.append(zcol)
            else:
                if column in cols:
                    chosen_cols = [column]
                else:
                    chosen_cols = cols[:2] if len(cols) >= 2 else cols

            joined = "__".join(chosen_cols)
            index_dir = os.path.join(self.data_dir, f"idx_kdtree", table_name, joined)
            os.makedirs(index_dir, exist_ok=True)
            dimension = 3 if len(chosen_cols) >= 3 else 2
            try:
                idx = KDTree(table_name, joined, data_dir=index_dir, dimension=dimension)
                try:
                    idx._columns = chosen_cols
                except Exception:
                    pass
                # populate from existing records
                for off, rec in self._iter_with_offsets(table_name):
                    try:
                        parts = [rec.get(c) for c in chosen_cols]
                        if all(p is None for p in parts):
                            continue
                        key = tuple(parts)
                        idx.add(key, off)
                    except Exception:
                        continue
            except Exception as e:
                print(f"[WARN] KDTree creation failed: {e}")
            # Populate the RTree from existing table records using an external builder
            try:
                # call external script to build the index in an isolated process to avoid C-level crashes
                import subprocess, sys
                script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "build_rtree_index.py")
                cols_csv = ",".join(chosen_cols)
                cmd = [sys.executable, script, self.data_dir, table_name, joined, cols_csv]
                try:
                    # run in chunks to isolate crashes; each chunk will process up to chunk_size records
                    chunk_size = 2000
                    start = 0
                    max_retries = 3
                    while True:
                        chunk_cmd = cmd + [str(start), str(chunk_size)]
                        try:
                            subprocess.check_call(chunk_cmd)
                        except subprocess.CalledProcessError as e:
                            print(f"[WARN] RTree builder chunk failed with exit {e.returncode} at start={start}")
                            # if crash code is common (e.g., access violation), retry a few times then abort
                            max_retries -= 1
                            if max_retries <= 0:
                                break
                            continue
                        # if succeeded, probe how many were inserted by reading the index (count)
                        try:
                            tmp_idx = RTree(table_name, joined, data_dir=index_dir, dimension=dimension)
                            inserted = tmp_idx.count()
                            tmp_idx.close()
                        except Exception:
                            # unknown, advance by chunk
                            inserted = chunk_size

                        if inserted < chunk_size:
                            # last chunk probably finished
                            break
                        start += chunk_size
                except Exception as e:
                    print(f"[WARN] RTree builder invocation failed: {e}")
            except Exception:
                pass
        else:
            raise ValueError(f"Tipo de índice no soportado: {index_type}")

        # store index object under its column key (for RTree/KDTree we may use joined name)
        if index_type in ("rtree", "kdtree"):
            key_name = "__".join(idx._columns) if hasattr(idx, "_columns") else column
        else:
            key_name = column
        self.tables[table_name]["indexes"][key_name] = idx
        self._save_catalog()
        return f"Índice {index_type} creado en {table_name}({key_name})"

    def create_index_multi(self, table_name: str, columns: list, index_type: str):
        """
        Create a multi-column spatial index (rtree or kdtree) using the explicit list of columns.
        This mirrors the logic in create_index for spatial types but accepts a columns list directly.
        """
        if table_name not in self.tables:
            raise ValueError(f"Tabla {table_name} no existe")
        cols = list(columns)
        if len(cols) == 0:
            raise ValueError("Debe proporcionar al menos una columna para el índice")

        joined = "__".join(cols)
        index_dir = os.path.join(self.data_dir, f"idx_{index_type}", table_name, joined)
        os.makedirs(index_dir, exist_ok=True)

        dimension = 3 if len(cols) >= 3 else 2
        if index_type == "rtree":
            idx = RTree(table_name, joined, data_dir=index_dir, dimension=dimension)
            try:
                idx._columns = cols
            except Exception:
                pass
            # populate using builder script (reuse existing create_index behavior)
            try:
                import subprocess, sys
                script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "build_rtree_index.py")
                cols_csv = ",".join(cols)
                cmd = [sys.executable, script, self.data_dir, table_name, joined, cols_csv]
                # single-shot for multi create
                subprocess.check_call(cmd)
            except Exception as e:
                print(f"[WARN] RTree multi-column builder failed: {e}")
        elif index_type == "kdtree":
            idx = KDTree(table_name, joined, data_dir=index_dir, dimension=dimension)
            try:
                idx._columns = cols
            except Exception:
                pass
            # populate from table records
            for off, rec in self._iter_with_offsets(table_name):
                try:
                    parts = [rec.get(c) for c in cols]
                    if all(p is None for p in parts):
                        continue
                    key = tuple(parts)
                    idx.add(key, off)
                except Exception:
                    continue
        else:
            raise ValueError("create_index_multi sólo soporta 'rtree' y 'kdtree'")

        # store and persist
        self.tables[table_name]["indexes"][joined] = idx
        self._save_catalog()
        return f"Índice {index_type} creado en {table_name}({joined})"

    def compare_query_methods(self, table_name: str, columns, condition: str, methods=None):
        """Run the same selection using different index technologies and measure time + disk accesses.

        Returns a list of { technique, time_ms, disk_accesses, records }
        """
        if methods is None:
            methods = ["sequential", "isam", "btree", "hash", "rtree"]

        if table_name not in self.tables:
            raise ValueError(f"Tabla {table_name} no existe")

        results = []
        # We'll run select with use_index True after ensuring the specified index exists
        for m in methods:
            # ensure index exists for the column
            try:
                if columns and isinstance(columns, list):
                    # assume single column compare
                    col = columns[0]
                else:
                    col = columns

                if col not in [c["name"] for c in self.tables[table_name]["schema"].columns]:
                    raise ValueError(f"Columna {col} no existe en {table_name}")

                # create index if absent (best-effort)
                if col not in self.tables[table_name]["indexes"]:
                    try:
                        self.create_index(table_name, col, m)
                    except Exception:
                        # cannot create this index type (e.g., rtree on non-spatial), skip
                        results.append({"technique": m, "time_ms": None, "disk_accesses": None, "records": None, "error": "could not create index"})
                        continue

                # reset counters
                reset_disk_accesses()

                import time
                start = time.time()
                rows = self.select(table_name, columns, condition)
                end = time.time()

                da = get_disk_accesses()
                results.append({
                    "technique": m,
                    "time_ms": round((end - start) * 1000, 3),
                    "disk_accesses": da,
                    "records": len(rows) if isinstance(rows, list) else 0,
                })
            except Exception as e:
                results.append({"technique": m, "time_ms": None, "disk_accesses": None, "records": None, "error": str(e)})

        return results
    
    def select_without_index(self, table_name, columns, condition, limit=None):
            table = self.tables[table_name]
            schema, file_manager = table["schema"], table["file"]

            results = []
            for rec in file_manager.scan_all():
                try:
                    rec_dict = rec if isinstance(rec, dict) else {
                        schema.columns[i]["name"]: rec[i] for i in range(len(schema.columns))
                    }

                    # If no condition provided, accept all
                    if not isinstance(condition, str) or not condition.strip():
                        results.append(rec_dict)
                        if limit and len(results) >= limit:
                            break
                        continue

                    cond = condition.strip()
                    # remove trailing semicolon
                    if cond.endswith(";"):
                        cond = cond[:-1]

                    matched = False

                    # BETWEEN handling
                    if "between" in cond.lower():
                        try:
                            parts = cond.lower().split()
                            col = parts[0]
                            a = parts[2].strip("'\"")
                            b = parts[4].strip("'\"")
                            rv = rec_dict.get(col)
                            if rv is not None:
                                try:
                                    rvf = float(rv)
                                    af = float(a)
                                    bf = float(b)
                                    if af <= rvf <= bf:
                                        matched = True
                                except Exception:
                                    if str(rv) >= a and str(rv) <= b:
                                        matched = True
                        except Exception as e:
                            print(f"[WARN] BETWEEN parse failed: {e}")

                    # Comparison operators
                    if not matched:
                        for op in ([">=", "<=", ">", "<", "="]):
                            if op in cond:
                                left, right = cond.split(op, 1)
                                col = left.strip()
                                val = right.strip().strip("'\"")
                                rv = rec_dict.get(col)
                                if rv is None:
                                    break
                                try:
                                    rvf = float(rv)
                                    vf = float(val)
                                    if op == ">=":
                                        matched = rvf >= vf
                                    elif op == ">":
                                        matched = rvf > vf
                                    elif op == "<=":
                                        matched = rvf <= vf
                                    elif op == "<":
                                        matched = rvf < vf
                                    elif op == "=":
                                        matched = rvf == vf
                                except Exception:
                                    sval = str(rv)
                                    if op == ">=":
                                        matched = sval >= val
                                    elif op == ">":
                                        matched = sval > val
                                    elif op == "<=":
                                        matched = sval <= val
                                    elif op == "<":
                                        matched = sval < val
                                    elif op == "=":
                                        matched = sval == val
                                break

                    if matched:
                        if columns and columns != ["*"]:
                            projected = {col: rec_dict.get(col) for col in columns}
                            results.append(projected)
                        else:
                            results.append(rec_dict)

                    # Limitar resultados
                    if limit and len(results) >= limit:
                        break

                except Exception as e:
                    print(f"Error evaluando condición: {e}")
                    continue

            return results

    def _iter_with_offsets(self, table_name):
        """Itera registros devolviendo (offset, dict)."""
        table = self.tables[table_name]
        schema, file_manager = table["schema"], table["file"]
        with open(file_manager.filename, "rb") as f:
            offset = 0
            while True:
                binary = f.read(schema.size)
                if not binary or len(binary) < schema.size:
                    break
                if binary.strip(b"\x00") == b"":
                    offset += schema.size
                    continue
                rec = schema.unpack(binary)
                yield offset, (rec if isinstance(rec, dict) else {schema.columns[i]["name"]: rec[i] for i in range(len(schema.columns))})
                offset += schema.size

    def _parse_simple_equality(self, condition):
        try:
            # forma: "col == value" o "col = value"
            if condition is None:
                return None, None
            c = condition.replace("==", "=")
            if "=" not in c:
                return None, None
            left, right = c.split("=", 1)
            col = left.strip()
            val = right.strip().strip("'\"")
            return col, val
        except Exception:
            return None, None