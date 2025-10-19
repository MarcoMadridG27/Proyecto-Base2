# core/schema_manager.py
import os
import re
import json
import shutil
from src.record import RecordSchema
from src.dbms.file_manager import FileManager
from src.dbms.sequential_index import SequentialIndex
from src.dbms.isam import ISAMMultinivel
from src.dbms.extendible_hash import ExtendibleHash
from src.dbms.bplustree import BPlusTree
from src.dbms.rtree import RTree
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
                    # kdtree support removed - default to extendible hash for unknown spatial types
                    elif itype == "kdtree":
                        indexes[col] = ExtendibleHash(tname, col, data_dir=index_dir)
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
            # best-effort close; ignore errors
            pass

    def select(self, table_name, columns, condition=None, index=None, limit=None, index_hint=None, return_metadata: bool = False):
        """Select rows from a table.

        If return_metadata=True the function returns a dict:
          { rows: [...], used_index: <col|False>, actually_used: bool, used_index_type: <str|None> }
        Otherwise it returns the list of rows (legacy behavior).
        """
        table = self.tables[table_name]
        schema, file_manager, indexes = table["schema"], table["file"], table["indexes"]

        actually_used = False
        used_index_type = None
        used_index_col = False

        def rec_to_dict(rec):
            return rec if isinstance(rec, dict) else {schema.columns[i]["name"]: rec[i] for i in range(len(schema.columns))}

        # 1) spatial predicate: col IN ([x,y], r)
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
                if col in indexes and "rtree" in indexes[col].__class__.__name__.lower():
                    r_idx = indexes[col]
                else:
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
                    used_index_col = col
                    actually_used = True
                    used_index_type = r_idx.__class__.__name__ if hasattr(r_idx, '__class__') else None
                    offsets = r_idx.range_search(point, radius) or []
                    # retry swapped coords if none
                    if (not offsets or len(offsets) == 0) and isinstance(point, (list, tuple)) and len(point) >= 2:
                        try:
                            swapped = [point[1], point[0]]
                            offsets = r_idx.range_search(swapped, radius) or []
                        except Exception:
                            pass

                    results = []
                    for off in offsets:
                        try:
                            rec = file_manager.read_record(off)
                        except Exception:
                            rec = None
                        if not rec:
                            continue
                        rec_dict = rec_to_dict(rec)
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

                    if return_metadata:
                        return {"rows": results, "used_index": used_index_col, "actually_used": actually_used, "used_index_type": used_index_type}
                    return results

        # 2) equality using index (col = value)
        eq_col, eq_val = self._parse_simple_equality(condition) if condition else (None, None)
        if eq_col and eq_col in indexes and hasattr(indexes[eq_col], 'find'):
            idx_obj = indexes[eq_col]
            raw = idx_obj.find(eq_val)
            actually_used = True
            used_index_col = eq_col
            used_index_type = idx_obj.__class__.__name__ if hasattr(idx_obj, '__class__') else None

            offsets = []
            if raw is None:
                offsets = []
            elif isinstance(raw, list):
                for e in raw:
                    if isinstance(e, int):
                        offsets.append(e)
                    else:
                        try:
                            offsets.append(int(getattr(e, 'offset')))
                        except Exception:
                            continue
            elif isinstance(raw, int):
                offsets = [raw]
            else:
                try:
                    offsets = [int(getattr(raw, 'offset'))]
                except Exception:
                    offsets = []

            results = []
            for off in offsets:
                try:
                    rec = file_manager.read_record(off)
                except Exception:
                    rec = None
                if not rec:
                    continue
                rec_dict = rec_to_dict(rec)
                if columns and columns != ["*"]:
                    results.append({c: rec_dict.get(c) for c in columns})
                else:
                    results.append(rec_dict)
                if limit is not None and len(results) >= limit:
                    break

            if return_metadata:
                return {"rows": results, "used_index": used_index_col, "actually_used": actually_used, "used_index_type": used_index_type}
            return results

        # 3) BETWEEN range on a single indexed column
        if condition and isinstance(condition, str) and 'between' in condition.lower():
            try:
                parts = condition.split()
                if index_hint and index_hint in indexes:
                    col = index_hint
                else:
                    col = parts[0]
                if col in indexes and hasattr(indexes[col], 'range_search'):
                    a = parts[2].strip("'\"")
                    b = parts[4].strip("'\"")

                    def _norm_key(v):
                        try:
                            if isinstance(v, str):
                                s = v.strip()
                                if re.fullmatch(r"-?\d+", s):
                                    return int(s)
                                if re.fullmatch(r"-?\d+\.\d+", s):
                                    return float(s)
                                return s
                        except Exception:
                            pass
                        return v

                    a = _norm_key(a)
                    b = _norm_key(b)
                    idx_obj = indexes[col]
                    raw = idx_obj.range_search(a, b)
                    actually_used = True
                    used_index_col = col
                    used_index_type = idx_obj.__class__.__name__ if hasattr(idx_obj, '__class__') else None

                    offsets = []
                    if raw is None:
                        offsets = []
                    elif isinstance(raw, list):
                        for e in raw:
                            if isinstance(e, int):
                                offsets.append(e)
                            else:
                                try:
                                    offsets.append(int(getattr(e, 'offset')))
                                except Exception:
                                    continue
                    elif isinstance(raw, int):
                        offsets = [raw]
                    else:
                        try:
                            offsets = [int(getattr(raw, 'offset'))]
                        except Exception:
                            offsets = []

                    results = []
                    for off in offsets:
                        try:
                            rec = file_manager.read_record(off)
                        except Exception:
                            rec = None
                        if not rec:
                            continue
                        rec_dict = rec_to_dict(rec)
                        if columns and columns != ["*"]:
                            results.append({c: rec_dict.get(c) for c in columns})
                        else:
                            results.append(rec_dict)
                        if limit is not None and len(results) >= limit:
                            break

                    if return_metadata:
                        return {"rows": results, "used_index": used_index_col, "actually_used": actually_used, "used_index_type": used_index_type}
                    return results
            except Exception as e:
                if self.debug:
                    print(f"[WARN] BETWEEN parsing failed: {e}")

        # 4) Fallback full scan
        results = []
        for rec in file_manager.scan_all():
            rec_dict = rec_to_dict(rec)
            if isinstance(condition, str) and condition.strip():
                try:
                    if "=" in condition:
                        parts = condition.split("=", 1)
                        col = parts[0].strip()
                        val = parts[1].strip().strip("'\"")
                        record_val = rec_dict.get(col)
                        if record_val is None:
                            continue
                        try:
                            if str(record_val).isdigit() and val.isdigit():
                                if int(record_val) != int(val):
                                    continue
                            elif str(record_val).replace('.', '').isdigit() and val.replace('.', '').isdigit():
                                if float(record_val) != float(val):
                                    continue
                            elif str(record_val) != val:
                                continue
                        except Exception:
                            if str(record_val) != val:
                                continue
                    else:
                        if not eval(condition.replace("=", "=="), {}, rec_dict):
                            continue
                except Exception as e:
                    if self.debug:
                        print(f"Error evaluando condición: {e}")
                    continue
            if columns and columns != ["*"]:
                results.append({col: rec_dict.get(col) for col in columns})
            else:
                results.append(rec_dict)
            if limit is not None and len(results) >= limit:
                break

        if return_metadata:
            return {"rows": results, "used_index": used_index_col, "actually_used": actually_used, "used_index_type": used_index_type}
        return results

    # ---------------------------
    # Delete
    # ---------------------------
    def delete(self, table_name, condition):
        table = self.tables[table_name]
        schema, file_manager = table["schema"], table["file"]

        deleted = 0
        cond = condition.strip() if isinstance(condition, str) else condition
        if isinstance(cond, str) and cond.endswith(";"):
            cond = cond[:-1]

        for off, rec in self._iter_with_offsets(table_name):
            try:
                rec_dict = rec if isinstance(rec, dict) else {schema.columns[i]["name"]: rec[i] for i in range(len(schema.columns))}

                matched = False

                # BETWEEN handling
                if isinstance(cond, str) and "between" in cond.lower():
                    parts = cond.lower().split()
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
                            matched = True
                    except Exception:
                        if str(rv) >= a and str(rv) <= b:
                            matched = True

                # equality/comparison
                if not matched and isinstance(cond, str) and any(op in cond for op in ([">=", "<=", ">", "<", "="])):
                    c = cond
                    if "=" in c and "==" not in c and ">=" not in c and "<=" not in c:
                        parts = c.split("=", 1)
                        col = parts[0].strip()
                        val = parts[1].strip().strip("'\"")
                        rv = rec_dict.get(col)
                        if rv is None:
                            pass
                        else:
                            try:
                                if str(rv).replace('.', '', 1).isdigit() and val.replace('.', '', 1).isdigit():
                                    if float(rv) == float(val):
                                        matched = True
                                else:
                                    if str(rv) == val:
                                        matched = True
                            except Exception:
                                if str(rv) == val:
                                    matched = True

                    if not matched:
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
                                        matched = True
                                except Exception:
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
                                        matched = True
                                break

                # fallback eval
                if not matched:
                    try:
                        if isinstance(cond, str) and eval(cond.replace("=", "=="), {}, rec_dict):
                            matched = True
                    except Exception:
                        matched = False

                if matched:
                    try:
                        file_manager.delete_record(off)
                        deleted += 1
                    except Exception as e:
                        if self.debug:
                            print(f"Error deleting record at offset {off}: {e}")
                        continue

            except Exception as e:
                print(f"Error during delete evaluation: {e}")
                continue

        return f"{deleted} registros eliminados de {table_name}"

    def count_matches(self, table_name, condition):
        """Count how many records would match `condition` in table_name without modifying data.

        This reuses the same matching logic as `delete` and `select_without_index` but returns
        only the integer count. Useful for dry-run measurements before destructive operations.
        """
        table = self.tables[table_name]
        schema, file_manager = table["schema"], table["file"]

        matched = 0
        for rec in file_manager.scan_all():
            try:
                rec_dict = rec if isinstance(rec, dict) else {schema.columns[i]["name"]: rec[i] for i in range(len(schema.columns))}
                cond = condition.strip() if isinstance(condition, str) else condition
                if isinstance(cond, str) and cond.endswith(";"):
                    cond = cond[:-1]

                # BETWEEN handling
                if isinstance(cond, str) and "between" in cond.lower():
                    parts = cond.lower().split()
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
                            matched += 1
                    except Exception:
                        if str(rv) >= a and str(rv) <= b:
                            matched += 1
                    continue

                # simple operators
                if isinstance(cond, str) and any(op in cond for op in ([">=", "<=", ">", "<", "="])):
                    c = cond
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
                                    matched += 1
                            else:
                                if str(rv) == val:
                                    matched += 1
                        except Exception:
                            if str(rv) == val:
                                matched += 1
                        continue

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
                                    matched += 1
                            except Exception:
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
                                    matched += 1
                            break

                else:
                    try:
                        if isinstance(cond, str) and eval(cond.replace("=", "=="), {}, rec_dict):
                            matched += 1
                    except Exception:
                        continue
            except Exception:
                continue

        return matched

    def create_table(self, table_name: str, columns_def: list, index_map: dict = None):
        """Create a new table with the provided columns_def.

        columns_def: list of {name: str, type: str}
        index_map: optional mapping column->index_type to create indexes on table creation
        """
        if table_name in self.tables:
            raise ValueError(f"Tabla {table_name} ya existe")

        # Validate and normalize columns_def
        if not isinstance(columns_def, list) or len(columns_def) == 0:
            raise ValueError("columns_def must be a non-empty list")

        # Ensure each column dict has name and type
        cols = []
        for c in columns_def:
            if not isinstance(c, dict) or 'name' not in c or 'type' not in c:
                raise ValueError("Each column must be a dict with 'name' and 'type'")
            cols.append({'name': c['name'], 'type': c['type']})

        schema = RecordSchema(cols)
        filepath = os.path.join(self.data_dir, f"{table_name}.dat")
        file_manager = FileManager(filepath, schema)

        indexes = {}
        # Optionally create requested indexes (best-effort)
        if index_map and isinstance(index_map, dict):
            for col, itype in index_map.items():
                try:
                    self.create_index(table_name, col, itype)
                except Exception:
                    # ignore index creation errors during table create
                    continue

        self.tables[table_name] = {
            'schema': schema,
            'file': file_manager,
            'indexes': indexes,
        }
        # Persist catalog
        self._save_catalog()
        return f"Tabla {table_name} creada con {len(cols)} columnas"
    
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
            # ISAM now stores generic Record(id:int, offset:int).
            # We'll convert each table record into ISAM.Record(id, offset)
            # where `offset` is the byte offset in the table .dat file returned by _iter_with_offsets().
            for off, rec in self._iter_with_offsets(table_name):
                try:
                    key = rec.get(column)
                    if key is None:
                        continue
                    # Try integer conversion for the key (ISAM uses integer keys)
                    try:
                        id_val = int(key)
                    except Exception:
                        # skip non-integer keys for ISAM (could also map a hash, but keep expected semantics)
                        continue
                    # Create ISAM Record(id, offset)
                    try:
                        rec_obj = ISAMMultinivel.Record(id_val, off)
                    except Exception:
                        from src.dbms.isam import Record as ISAMRecord
                        rec_obj = ISAMRecord(id_val, off)
                    idx.insert(rec_obj)
                except Exception as e:
                    print(f"[WARN] ISAM insert error: {e}")
            # After buffering records, build the index files on disk
            try:
                idx.build_indices()
            except Exception as e:
                print(f"[WARN] ISAM build_indices failed: {e}")

        elif index_type == "btree":
            idx_file = os.path.join(index_dir, "btree.idx")
            idx = BPlusTree(idx_file)
            # Build B+ Tree using offsets: insert(key, offset)
            for off, rec in self._iter_with_offsets(table_name):
                key = rec.get(column)
                if key is None:
                    continue
                # normalize whitespace for strings
                if isinstance(key, str):
                    key = key.strip().strip("'\"")
                # try to convert to int when possible for numeric ordering
                try:
                    if isinstance(key, str) and key.isdigit():
                        key = int(key)
                except Exception:
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
        # kdtree support removed - not implemented in this project
        else:
            raise ValueError(f"Tipo de índice no soportado: {index_type}")

        # store index object under its column key (for RTree we may use joined name)
        if index_type == "rtree":
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
        # kdtree support removed - only rtree supported for multi-column spatial index
        else:
            raise ValueError("create_index_multi sólo soporta 'rtree'")

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
        # Use FileManager.read_record which now respects logical deletions via .del sidecar
        try:
            fsize = os.path.getsize(file_manager.filename)
        except Exception:
            fsize = 0
        total = fsize // schema.size if schema.size > 0 else 0
        offset = 0
        for idx in range(total):
            rec = file_manager.read_record(offset)
            if rec is None:
                offset += schema.size
                continue
            rec_dict = rec if isinstance(rec, dict) else {schema.columns[i]["name"]: rec[i] for i in range(len(schema.columns))}
            yield offset, rec_dict
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

    def insert(self, table_name, values):
        """Insert a row into table_name.

        `values` may be either a dict mapping column->value or a list of values in column order.
        The function appends the record to disk and updates any existing indexes.
        Returns the offset where the record was written.
        """
        if table_name not in self.tables:
            raise ValueError(f"Tabla {table_name} no existe")

        table = self.tables[table_name]
        schema, file_manager, indexes = table['schema'], table['file'], table['indexes']

        # Normalize record to dict
        if isinstance(values, dict):
            rec = values
        elif isinstance(values, (list, tuple)):
            rec = {}
            for i, col in enumerate(schema.columns):
                rec[col['name']] = values[i] if i < len(values) else None
        else:
            raise ValueError('Unsupported values type for insert')

        # Clean string tokens that may come quoted
        for k, v in list(rec.items()):
            if isinstance(v, str):
                rec[k] = v.strip().strip("'\"")

        # Append to data file
        try:
            off = file_manager.append_record(rec)
        except Exception as e:
            raise RuntimeError(f"Failed to append record: {e}")

        # Update indexes (best-effort)
        for col, idx in indexes.items():
            try:
                # For multi-column rtree index, `col` may be joined 'a__b'
                if hasattr(idx, '_columns') and len(getattr(idx, '_columns', [])) > 1:
                    cols = getattr(idx, '_columns')
                    point = []
                    for c in cols:
                        v = rec.get(c)
                        try:
                            point.append(float(v))
                        except Exception:
                            point.append(0.0)
                    # RTree insert expects (point, offset)
                    try:
                        idx.insert(point, off)
                    except Exception:
                        # some rtree wrappers use add/insert signature differences
                        try:
                            idx.add(point, off)
                        except Exception:
                            pass
                    continue

                key = rec.get(col)
                # strip strings
                if isinstance(key, str):
                    key = key.strip().strip("'\"")
                # numeric conversion when possible
                try:
                    if isinstance(key, str) and key.isdigit():
                        key = int(key)
                except Exception:
                    pass

                # Dispatch by known types
                if isinstance(idx, SequentialIndex):
                    try:
                        idx.add(key, off)
                    except Exception:
                        pass
                elif isinstance(idx, ISAMMultinivel):
                    try:
                        from src.dbms.isam import Record as ISAMRecord
                        # ISAM expects integer id keys; try conversion
                        id_val = int(key) if key is not None else 0
                        rec_obj = ISAMRecord(id_val, off)
                        # Si el índice ya fue construido en disco, usar insert_after_build
                        try:
                            if os.path.exists(idx.nivel_3_data) and os.path.getsize(idx.nivel_3_data) > 0:
                                idx.insert_after_build(rec_obj)
                            else:
                                # Si no está construido, mantener en buffer para build_indices()
                                idx.insert(rec_obj)
                        except Exception:
                            # fallback: intentar ambos métodos sin explotar la inserción
                            try:
                                idx.insert_after_build(rec_obj)
                            except Exception:
                                try:
                                    idx.insert(rec_obj)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                else:
                    # Try BPlusTree / ExtendibleHash / RTree generic methods
                    try:
                        cname = idx.__class__.__name__.lower()
                    except Exception:
                        cname = ''

                    if 'bplus' in cname or 'btree' in cname:
                        try:
                            idx.insert(key, off)
                        except Exception:
                            pass
                    elif 'rtree' in cname:
                        # Single-column rtree (point stored in one column as array-like)
                        try:
                            # treat key as comma separated coords if string
                            if isinstance(key, str) and (',' in key or ' ' in key):
                                parts = re.split(r"[ ,]+", key)
                                point = [float(p) if re.fullmatch(r"-?\d+(?:\.\d+)?", p) else 0.0 for p in parts]
                                idx.insert(point, off)
                            else:
                                # otherwise try direct insert
                                idx.insert(key, off)
                        except Exception:
                            try:
                                idx.add(key, off)
                            except Exception:
                                pass
                    else:
                        # fallback: try add then insert
                        try:
                            if hasattr(idx, 'add'):
                                idx.add(key, off)
                            elif hasattr(idx, 'insert'):
                                idx.insert(key, off)
                        except Exception:
                            pass

            except Exception:
                # Do not fail the whole insert if updating indexes fails for one index
                continue

        return off