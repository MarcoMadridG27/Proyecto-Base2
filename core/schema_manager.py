# core/schema_manager.py
import os
from core.record import RecordSchema
from core.file_manager import FileManager
from core.sequential import SequentialIndex
from core.isam import ISAMIndex
from core.extendible_hash import ExtendibleHash
from core.bplustree import BPlusTree
from core.rtree import RTree

class SchemaManager:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.tables = {}  # {table_name: {"schema": RecordSchema, "file": FileManager, "indexes": {col: idx}}}

    def create_table(self, table_name, columns, index_map=None):
        """
        columns: lista [{"name": "id", "type": "INT"}, ...]
        index_map: {"id": "isam", "nombre": "btree", "ubicacion": "rtree"}
        """
        schema = RecordSchema(columns)
        filepath = os.path.join(self.data_dir, f"{table_name}.dat")
        file_manager = FileManager(filepath, schema)

        # Crear índices según index_map
        indexes = {}
        if index_map:
            for col, idx_type in index_map.items():
                if idx_type == "sequential":
                    indexes[col] = SequentialIndex(table_name, col)
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
            "indexes": indexes
        }
        return f"Tabla {table_name} creada con {len(columns)} columnas"

    def insert(self, table_name, values):
        table = self.tables[table_name]
        schema, file_manager, indexes = table["schema"], table["file"], table["indexes"]

        offset = file_manager.append_record(values)
        # Actualizar índices
        for col, index in indexes.items():
            key = values[col] if isinstance(values, dict) else values[schema.columns.index({"name": col})]
            index.add(key, offset)

        return f"Registro insertado en {table_name}"

    def select(self, table_name, columns, condition, index=None):
        table = self.tables[table_name]
        file_manager, indexes = table["file"], table["indexes"]

        # Si no hay condición → scan completo
        if not condition:
            return file_manager.scan_all()

        # Si se especifica índice
        if index and index in indexes:
            key = int(condition.split("=")[-1])  # simplificación
            offsets = indexes[index].search(key)
            return [file_manager.read_record(off) for off in offsets]

        # Si no → scan completo filtrado
        results = []
        for rec in file_manager.scan_all():
            if eval(condition.replace("=", "=="), {}, rec):
                results.append(rec)
        return results

    def delete(self, table_name, condition):
        table = self.tables[table_name]
        file_manager = table["file"]

        # scan all, buscar registros que cumplen condición
        deleted = 0
        for off, rec in enumerate(file_manager.scan_all()):
            if eval(condition.replace("=", "=="), {}, rec):
                file_manager.delete_record(off * table["schema"].size)
                deleted += 1
        return f"{deleted} registros eliminados de {table_name}"
