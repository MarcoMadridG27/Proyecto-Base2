# core/schema_manager.py
import os
import json
from src.record import RecordSchema
from src.dbms.file_manager import FileManager
from src.dbms.sequential import SequentialFile
from src.dbms.sequential_index import SequentialIndex
from src.dbms.isam import ISAMIndex
from src.dbms.extendible_hash import ExtendibleHash
from src.dbms.bplustree import BPlusTree
from src.dbms.rtree import RTree


class SchemaManager:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.catalog_path = os.path.join(self.data_dir, "catalog.json")
        self.tables = {}  # {table_name: {"schema": RecordSchema, "file": FileManager, "indexes": {col: idx}}}

        # Restaurar catálogo si existe
        if os.path.exists(self.catalog_path):
            self._load_catalog()

    # ---------------------------
    # Persistencia del catálogo
    # ---------------------------
    def _save_catalog(self):
        catalog = {}
        for tname, tinfo in self.tables.items():
            catalog[tname] = {
                "columns": tinfo["schema"].columns,
                "indexes": list(tinfo["indexes"].keys()),
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
            for col in meta.get("indexes", []):
                # Cargamos un índice simple por igualdad (persistente JSON)
                indexes[col] = ExtendibleHash(tname, col, self.data_dir)

            self.tables[tname] = {
                "schema": schema,
                "file": file_manager,
                "indexes": indexes,
            }

        print(f"[DEBUG] Catálogo restaurado con {len(self.tables)} tablas")

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
                if idx_type == "sequential":
                    indexes[col] = SequentialIndex(table_name, col, self.data_dir)
                elif idx_type in ("hash", "btree", "isam"):
                    indexes[col] = ExtendibleHash(table_name, col, self.data_dir)
                elif idx_type == "rtree":
                    indexes[col] = RTree(table_name, col)

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
            key = record_dict.get(col)
            if key is not None:
                if isinstance(key, str):
                    key = key.strip().strip("'\"")
                # Índice simple almacena offset del .dat
                if hasattr(index, "add"):
                    index.add(key, offset)

        return {"success": True, "message": f"Registro insertado en {table_name}", "offset": offset}

    # ---------------------------
    # Select
    # ---------------------------
    def select(self, table_name, columns, condition=None, index=None, limit=None):
        table = self.tables[table_name]
        schema, file_manager, indexes = table["schema"], table["file"], table["indexes"]

        # Intento: si hay condición simple col = value y existe índice, usarlo
        eq_col, eq_val = self._parse_simple_equality(condition) if condition else (None, None)
        if eq_col and eq_col in indexes and hasattr(indexes[eq_col], "find"):
            offsets = indexes[eq_col].find(eq_val)
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
        for off, rec in enumerate(file_manager.scan_all()):
            if eval(condition.replace("=", "=="), {}, rec):
                file_manager.delete_record(off * schema.size)
                deleted += 1
        return f"{deleted} registros eliminados de {table_name}"
    
    # ---------------------------
    # Crear índice
    # ---------------------------
    
    def create_index(self, table_name, column, index_type):
        if table_name not in self.tables:
            raise ValueError(f"Tabla {table_name} no existe")

        if column not in [c["name"] for c in self.tables[table_name]["schema"].columns]:
            raise ValueError(f"La columna {column} no existe en la tabla {table_name}")

        if index_type == "sequential":
            idx = SequentialIndex(table_name, column, self.data_dir)
            # Construir índices desde el archivo actual
            for off, rec in self._iter_with_offsets(table_name):
                key = rec.get(column)
                if key is not None:
                    if isinstance(key, str):
                        key = key.strip().strip("'\"")
                    idx.add(key, off)
        elif index_type in ("hash", "btree", "isam"):
            idx = ExtendibleHash(table_name, column, self.data_dir)
            idx.clear()
            for off, rec in self._iter_with_offsets(table_name):
                key = rec.get(column)
                if key is not None:
                    if isinstance(key, str):
                        key = key.strip().strip("'\"")
                    idx.add(key, off)
        elif index_type == "rtree":
            idx = RTree(table_name, column)
        else:
            raise ValueError(f"Tipo de índice no soportado: {index_type}")

        self.tables[table_name]["indexes"][column] = idx
        self._save_catalog()
        return f"Índice {index_type} creado en {table_name}({column})"
    
    def select_without_index(self, table_name, columns, condition, limit=None):
            table = self.tables[table_name]
            schema, file_manager = table["schema"], table["file"]

            results = []
            for rec in file_manager.scan_all():
                try:
                    rec_dict = rec if isinstance(rec, dict) else {
                        schema.columns[i]["name"]: rec[i] for i in range(len(schema.columns))
                    }

                    # Evaluar condición de forma segura
                    if not isinstance(condition, str) or not condition.strip():
                        results.append(rec_dict)
                    else:
                        # Evaluar condición con conversión de tipos
                        try:
                            # Parsear condición simple: col = value
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
                                            if int(record_val) == int(val):
                                                results.append(rec_dict)
                                        elif str(record_val).replace('.', '').isdigit() and val.replace('.', '').isdigit():
                                            if float(record_val) == float(val):
                                                results.append(rec_dict)
                                        elif str(record_val) == val:
                                            results.append(rec_dict)
                                    except:
                                        if str(record_val) == val:
                                            results.append(rec_dict)
                        except Exception as e:
                            print(f"Error evaluando condición: {e}")
                            continue

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