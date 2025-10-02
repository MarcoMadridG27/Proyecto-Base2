# core/schema_manager.py
import os
import json
from src.record import RecordSchema
from src.dbms.file_manager import FileManager
from src.dbms.sequential import SequentialFile
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
                # Si quieres más detalle de qué tipo de índice era, debes guardarlo en JSON
                indexes[col] = SequentialFile(tname, col)

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
                    indexes[col] = SequentialFile(table_name, col)
                elif idx_type == "isam":
                    indexes[col] = ISAMIndex(table_name, col)
                elif idx_type == "hash":
                    indexes[col] = ExtendibleHash(table_name, col)
                elif idx_type == "btree":
                    indexes[col] = BPlusTree(table_name, col)
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
                index.add(key, offset)

        return {"success": True, "message": f"Registro insertado en {table_name}", "offset": offset}

    # ---------------------------
    # Select
    # ---------------------------
    def select(self, table_name, columns, condition=None, index=None, limit=None):
        table = self.tables[table_name]
        schema, file_manager, indexes = table["schema"], table["file"], table["indexes"]

        # Recuperar todos los registros
        results = []
        all_records = file_manager.scan_all()

        for rec in all_records:
            # Normalizar en dict
            rec_dict = rec if isinstance(rec, dict) else {
                schema.columns[i]["name"]: rec[i] for i in range(len(schema.columns))
            }

            # Evaluar condición si existe
            if condition:
                try:
                    if not eval(condition.replace("=", "=="), {}, rec_dict):
                        continue
                except Exception as e:
                    print(f"Error evaluando condición: {e}")
                    continue

            # Proyección de columnas
            if columns and columns != ["*"]:
                projected = {col: rec_dict.get(col) for col in columns}
                results.append(projected)
            else:
                results.append(rec_dict)

            # Aplicar LIMIT temprano para eficiencia
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
