# core/schema_manager.py
import os
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
            "indexes": indexes
        }
        return f"Tabla {table_name} creada con {len(columns)} columnas"

    def insert(self, table_name, values):
        table = self.tables[table_name]
        schema, file_manager, indexes = table["schema"], table["file"], table["indexes"]

        # Convertir lista de valores a diccionario y limpiar
        if isinstance(values, list):
            record_dict = {}
            for i, col_def in enumerate(schema.columns):
                col_name = col_def["name"]
                if i < len(values):
                    val = values[i]
                    # Limpiar valor (quitar comillas)
                    if isinstance(val, str):
                        val = val.strip().strip("'\"")
                    record_dict[col_name] = val
                else:
                    record_dict[col_name] = None
        else:
            record_dict = values

        # Debug: mostrar solo el primer insert
        if file_manager.filename.endswith('.dat'):
            file_size = os.path.getsize(file_manager.filename) if os.path.exists(file_manager.filename) else 0
            if file_size == 0:
                print(f"Primer registro: {record_dict}")

        # Guardar en archivo
        offset = file_manager.append_record(record_dict)
        
        # Actualizar índices
        for col, index in indexes.items():
            key = record_dict.get(col)
            if key is not None:
                if isinstance(key, str):
                    key = key.strip().strip("'\"")
                index.add(key, offset)

        return {"success": True, "message": f"Registro insertado en {table_name}", "offset": offset}
    def select(self, table_name, columns, condition, index=None):
        table = self.tables[table_name]
        schema, file_manager, indexes = table["schema"], table["file"], table["indexes"]

        # Si no hay condición → scan completo
        if not condition:
            records = file_manager.scan_all()
            print(f"Scan completo de {table_name}: {len(records)} registros")  # Debug
            return records

        # Si se especifica índice
        if index and index in indexes:
            try:
                key = condition.split("=")[-1].strip().strip("'\"")
                offsets = indexes[index].search(key)
                return [file_manager.read_record(off) for off in offsets]
            except Exception as e:
                print(f"Error usando índice {index}: {e}")
                # Fallback a scan completo

        # Scan completo con filtrado
        results = []
        all_records = file_manager.scan_all()
        
        for rec in all_records:
            try:
                # Convertir record a dict si no lo es
                if isinstance(rec, list):
                    rec_dict = {}
                    for i, col_def in enumerate(schema.columns):
                        if i < len(rec):
                            rec_dict[col_def["name"]] = rec[i]
                else:
                    rec_dict = rec
                    
                # Evaluar condición de forma segura
                if eval(condition.replace("=", "=="), {}, rec_dict):
                    results.append(rec)
            except Exception as e:
                print(f"Error evaluando condición para registro: {e}")
                continue
                
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
