# parser/executor.py
from src.parser.parser import SQLParser
from src.schema_manager import SchemaManager
import re


class Executor:
    def __init__(self, data_dir="data"):
        """
        El Executor se conecta con el SchemaManager, 
        que maneja tablas, archivos e índices.
        """
        self.schema_manager = SchemaManager(data_dir)
        self.parser = SQLParser()

    def execute(self, query: str, use_index: bool = True, index_hint: str = None, dry_run: bool = False):
        # Parseamos la consulta SQL
        ast = self.parser.parse(query)
        op = ast["operation"]

        if op == "create":
            # Crear tabla con posibles índices
            return self.schema_manager.create_table(
                ast["table"], ast["columns"], ast.get("index_map")
            )

        elif op == "insert":
            # Insertar datos en la tabla
            # If parser returned explicit columns, convert values to a mapping
            vals = ast.get("values")
            cols = ast.get("columns")
            if cols and isinstance(cols, list):
                # strip trailing commas from tokens and remove quotes
                cleaned = [v.strip().strip("'\"") for v in vals]
                def normalize_col(name):
                    return name.strip().replace(' ', '_').replace('/', '_').replace('-', '_').lower()
                mapping = {normalize_col(c): (cleaned[i] if i < len(cleaned) else None) for i, c in enumerate(cols)}
                if dry_run:
                    # simulate packing/validation but do not write to disk
                    try:
                        # attempt to pack to detect errors
                        schema = self.schema_manager.tables[ast["table"]]["schema"]
                        schema.pack(mapping)
                    except Exception:
                        # ignore packing errors in dry run, but return info
                        pass
                    return {"result": None, "executed": False, "dry_run": True}
                return self.schema_manager.insert(ast["table"], mapping)
            else:
                if dry_run:
                    try:
                        # try to validate values against schema if possible
                        schema = self.schema_manager.tables[ast["table"]]["schema"]
                        # values may be list: convert to dict for pack
                        rec = {}
                        for i, col in enumerate(schema.columns):
                            rec[col['name']] = vals[i] if i < len(vals) else None
                        schema.pack(rec)
                    except Exception:
                        pass
                    return {"result": None, "executed": False, "dry_run": True}
                return self.schema_manager.insert(ast["table"], vals)

        elif op == "delete":
            # Eliminar datos de la tabla
            if dry_run:
                # return count of matched rows without deleting
                count = self.schema_manager.count_matches(ast["table"], ast["condition"])
                return {"result": None, "dry_count": count}
            return self.schema_manager.delete(ast["table"], ast["condition"])

        elif op == "select":
            table_name = ast["table"]
            has_any_index = False
            try:
                tbl = self.schema_manager.tables.get(table_name)
                if tbl and tbl.get("indexes"):
                    has_any_index = len(tbl["indexes"]) > 0
            except Exception:
                has_any_index = False

            # Spatial predicate detection: prefer using a multi-column RTree when condition is spatial
            spatial_match = None
            if isinstance(ast.get("condition"), str) and ast.get("condition"):
                spatial_match = re.match(r"\s*([A-Za-z0-9_]+)\s+in\s*\(\s*\[?([^\]]+)\]?\s*,\s*([0-9\.]+)\s*\)\s*$", ast.get("condition"), re.I)

            if use_index and has_any_index:
                # Decide which index (column) to use as a hint based on condition and available indexes
                hint = None
                condition = ast.get("condition")
                # If spatial predicate detected, try to find or build a multi-column rtree index
                if spatial_match:
                    # prefer any existing rtree index that covers multiple columns
                    for col, idx_obj in tbl.get("indexes", {}).items():
                        try:
                            if "rtree" in idx_obj.__class__.__name__.lower():
                                cols = getattr(idx_obj, "_columns", None)
                                if cols and len(cols) > 1:
                                    hint = col
                                    break
                        except Exception:
                            continue
                    # if not found, attempt to auto-create a composite rtree using common pairs
                    if not hint:
                        cols = [c["name"] for c in self.schema_manager.tables[table_name]["schema"].columns]
                        low = [c.lower() for c in cols]
                        pair = None
                        for a, b in [("x", "y"), ("y", "x"), ("lat", "lon"), ("lon", "lat"), ("latitude", "longitude"), ("longitude", "latitude"), ("lng", "lat")]:
                            if a in low and b in low:
                                pair = (cols[low.index(a)], cols[low.index(b)])
                                break
                        if pair:
                            try:
                                # create composite rtree index; create_index will name it joined
                                self.schema_manager.create_index(table_name, pair[0], "rtree")
                                hint = "__".join([pair[0], pair[1]])
                            except Exception:
                                hint = None
                # 1) exact equality column
                eq_col, _ = self.schema_manager._parse_simple_equality(condition) if condition else (None, None)
                if eq_col and eq_col in tbl.get("indexes", {}):
                    hint = eq_col
                # 2) between clause
                if not hint and isinstance(condition, str) and "between" in condition.lower():
                    try:
                        parts = condition.lower().split()
                        col = parts[0]
                        if col in tbl.get("indexes", {}):
                            hint = col
                    except Exception:
                        pass
                # 3) look for indexed column names mentioned in condition
                # Use word-boundary matching to avoid matching single-letter columns inside longer names
                if not hint and isinstance(condition, str):
                    for col in tbl.get("indexes", {}).keys():
                        try:
                            if re.search(r"\b" + re.escape(col) + r"\b", condition, re.I):
                                hint = col
                                break
                        except Exception:
                            continue
                # 4) if still no hint, pick by priority of index types
                if not hint:
                    priority = ["btree", "isam", "hash", "rtree", "sequential"]
                    def idx_type_name(obj):
                        cname = obj.__class__.__name__.lower()
                        if "bplus" in cname or "bplustree" in cname or "btree" in cname:
                            return "btree"
                        if "isam" in cname:
                            return "isam"
                        if "extend" in cname or "hash" in cname:
                            return "hash"
                        if "rtree" in cname:
                            return "rtree"
                        if "sequential" in cname:
                            return "sequential"
                        return cname

                    best_col = None
                    best_rank = len(priority)
                    for col, idx_obj in tbl.get("indexes", {}).items():
                        tname = idx_type_name(idx_obj)
                        if tname in priority:
                            rank = priority.index(tname)
                            if rank < best_rank:
                                best_rank = rank
                                best_col = col
                    hint = best_col

                # Call select with an index hint (may be None)
                # If caller provided an explicit index_hint, prefer it over the computed hint
                final_hint_raw = index_hint if index_hint else hint
                # normalize if frontend passed 'table.column'
                if isinstance(final_hint_raw, str) and "." in final_hint_raw:
                    final_hint = final_hint_raw.split(".")[-1]
                else:
                    final_hint = final_hint_raw

                # If the selected index (or available best) is an RTree, ignore single-column hint
                # and choose the rtree index key present in the table indexes (which may be joined cols)
                if final_hint:
                    idx_obj = tbl.get("indexes", {}).get(final_hint)
                    try:
                        cname = idx_obj.__class__.__name__.lower() if idx_obj is not None else ""
                    except Exception:
                        cname = ""
                    if "rtree" in cname:
                        # Prefer a multi-column rtree index (joined key like 'x__y') if available
                        chosen = None
                        for k, v in tbl.get("indexes", {}).items():
                            try:
                                if "rtree" in v.__class__.__name__.lower():
                                    cols = getattr(v, "_columns", None)
                                    # prefer indexes that explicitly cover multiple columns
                                    if cols and len(cols) > 1:
                                        chosen = k
                                        break
                                    # otherwise remember a single-column rtree as a fallback
                                    if chosen is None:
                                        chosen = k
                            except Exception:
                                continue
                        if chosen:
                            final_hint = chosen
                # Ask SchemaManager to return metadata about whether the index was actually used.
                meta = self.schema_manager.select(
                    table_name,
                    ast["columns"],
                    ast.get("condition"),
                    index=ast.get("index"),
                    limit=ast.get("limit"),
                    index_hint=final_hint,
                    return_metadata=True,
                )

                # Default fallbacks
                rows = None
                actually_used = False
                used_col = final_hint
                idx_type = None
                used_index_columns = None
                warning = None

                # If SchemaManager returned the metadata dict, use it to determine actual usage
                if isinstance(meta, dict) and "rows" in meta:
                    rows = meta.get("rows")
                    actually_used = bool(meta.get("actually_used", False))
                    # Prefer the used_index reported by schema manager if present
                    used_col = meta.get("used_index") if meta.get("used_index") else final_hint
                    used_index_obj = None
                    try:
                        used_index_obj = tbl.get("indexes", {}).get(used_col) if tbl else None
                    except Exception:
                        used_index_obj = None

                    # determine index type string from the actual index object
                    try:
                        if used_index_obj is not None:
                            cname = used_index_obj.__class__.__name__.lower()
                            if "bplus" in cname or "bplustree" in cname or "btree" in cname:
                                idx_type = "btree"
                            elif "isam" in cname:
                                idx_type = "isam"
                            elif "extend" in cname or "hash" in cname:
                                idx_type = "hash"
                            elif "rtree" in cname:
                                idx_type = "rtree"
                            elif "sequential" in cname or "sidx" in cname:
                                idx_type = "sequential"
                            else:
                                idx_type = cname
                    except Exception:
                        idx_type = None

                    try:
                        if used_index_obj is not None and hasattr(used_index_obj, "_columns"):
                            used_index_columns = list(getattr(used_index_obj, "_columns"))
                    except Exception:
                        used_index_columns = None

                    if not actually_used:
                        warning = f"Requested index hint '{final_hint}' was not applicable for table '{table_name}'"
                else:
                    # Legacy behavior: SchemaManager returned rows only. Treat hint->used as best-effort.
                    rows = meta
                    actually_used = bool(final_hint)
                    try:
                        used_index_obj = tbl.get("indexes", {}).get(final_hint) if tbl else None
                        if used_index_obj is not None:
                            cname = used_index_obj.__class__.__name__.lower()
                            if "bplus" in cname or "bplustree" in cname or "btree" in cname:
                                idx_type = "btree"
                            elif "isam" in cname:
                                idx_type = "isam"
                            elif "extend" in cname or "hash" in cname:
                                idx_type = "hash"
                            elif "rtree" in cname:
                                idx_type = "rtree"
                            elif "sequential" in cname or "sidx" in cname:
                                idx_type = "sequential"
                            else:
                                idx_type = cname
                    except Exception:
                        idx_type = None

                detected_col = used_col if used_col else 'none'
                print(f"[DEBUG] Executor.execute: detected_column={detected_col} actually_used={actually_used} using_index_type={idx_type if idx_type else 'none'}")

                return {"result": rows, "used_index": (used_col if actually_used else False), "used_index_type": (idx_type if actually_used and idx_type else False), "used_index_columns": (used_index_columns if actually_used and used_index_columns else False), "index_warning": warning}
            elif use_index and not has_any_index:
                # No hay índices disponibles, ejecutar sin índice pero con advertencia
                rows = self.schema_manager.select_without_index(
                    table_name,
                    ast["columns"],
                    ast["condition"],
                    limit=ast.get("limit")
                )
                return {"result": rows, "used_index": False, "index_warning": f"No indexes available for table '{table_name}'"}
            else:
                rows = self.schema_manager.select_without_index(
                    table_name,
                    ast["columns"],
                    ast["condition"],
                    limit=ast.get("limit")
                )
                return {"result": rows, "used_index": False, "index_warning": None}

        elif op == "create_index":
            # Crear un índice en una columna de una tabla
            return self.schema_manager.create_index(
                ast["table"], ast["column"], ast["index_type"]
            )

        else:
            raise ValueError(f"Operación no soportada: {op}")


if __name__ == "__main__":
    exe = Executor()

    # Simulaciones de operaciones SQL
    q1 = "CREATE TABLE Restaurantes (id INT, nombre VARCHAR[20], fecha DATE) USING btree(id)"
    print(exe.execute(q1))  # Crear tabla con índice BTree en 'id'

    q2 = "INSERT INTO Restaurantes VALUES (1, 'KFC', '2023-01-01')"
    print(exe.execute(q2))  # Insertar un registro en Restaurantes

    q3 = "SELECT * FROM Restaurantes WHERE id = 1"
    print(exe.execute(q3))  # Consultar registros con 'id' = 1

    q4 = "CREATE INDEX btree ON Restaurantes (nombre)"
    print(exe.execute(q4))  # Crear índice BTree en la columna 'nombre'
