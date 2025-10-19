from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import shutil
import csv
import time

from src.parser.executor import Executor
from src.schema_manager import SchemaManager
import pathlib

# Inicializamos Executor: compute data_dir relative to this file so it works
# when the process cwd is the repository root.
CURRENT_DIR = pathlib.Path(__file__).resolve().parent
CORE_ROOT = CURRENT_DIR.parent.parent  # core/src -> core
DATA_DIR = str(CORE_ROOT.joinpath("data"))
executor = Executor(data_dir=DATA_DIR)

app = FastAPI(
    title="Mini DB Backend",
    description="Proyecto BD2 - Motor de base de datos con índices",
    version="1.0"
)

# Configuración de CORS para permitir peticiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # puedes restringir a ["http://localhost:3000"] si prefieres
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# MODELOS
# -------------------------------
class QueryRequest(BaseModel):
    query: str
    use_index: bool  # Se añade el parámetro use_index
    index_hint: Optional[str] = None

class IndexRequest(BaseModel):
    index_type: str
    table_name: str
    column: Optional[str] = None  # prefer single-column name for non-spatial indexes
    columns: Optional[list] = None  # for spatial indexes, allow explicit columns list

# -------------------------------
# ENDPOINTS
# -------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "message": "Backend running!"}

@app.post("/query")
def run_query(request: QueryRequest):
    use_index = request.use_index  # Recibe el parámetro use_index
    try:
        print(f"Query recibida: {request.query} | Use Index: {use_index}")  # Debug
        result = None
        execution_time = None
        
        # Ejecutar la consulta con o sin índice
        start_time = time.time()
        result = executor.execute(request.query, use_index=use_index, index_hint=request.index_hint)
        execution_time = time.time() - start_time

        # Normalizar salida de SELECT vs otras operaciones
        if isinstance(result, dict) and "result" in result and "used_index" in result:
            resp = {
                "ok": True,
                "result": result["result"],
                "used_index": result["used_index"],
                "index_warning": result.get("index_warning"),
                "execution_time": execution_time,
            }
            # include used_index_type if present
            if "used_index_type" in result:
                resp["used_index_type"] = result["used_index_type"]
            if "used_index_columns" in result:
                resp["used_index_columns"] = result["used_index_columns"]
            return resp
        else:
            return {
                "ok": True,
                "result": result,
                "execution_time": execution_time
            }

    except Exception as e:
        print(f"Error: {str(e)}")  # Debug
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), table_name: str = Form("uploaded_table")):
    """
    Sube un CSV, lo guarda como tabla en el motor y queda persistido en catalog.json
    """
    try:
        os.makedirs("data", exist_ok=True)
        save_path = os.path.join("data", file.filename)

        # Guardar archivo CSV en disco
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        headers = []
        rows = []
        all_data = []
        record_count = 0

        # Leer el CSV
        with open(save_path, newline='', encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader)  # primera fila = cabeceras

            for i, row in enumerate(reader):
                all_data.append(row)
                if i < 10:  # preview
                    rows.append(row)
                record_count = i + 1

        # Normalizar headers (sin espacios, todo lowercase)
        clean_headers = [col.strip().replace(" ", "_").replace("-", "_").lower() for col in headers]

        # Definir columnas como lista de dicts (para SchemaManager)
        columns_def = [{"name": col, "type": "VARCHAR[100]"} for col in clean_headers]

        # --- Crear tabla solo si no existe ---
        if table_name in executor.schema_manager.tables:
            return JSONResponse(
                content={"ok": False, "error": f"La tabla '{table_name}' ya existe."},
                status_code=400
            )

        executor.schema_manager.create_table(table_name, columns_def)

        inserted = 0
        failed = 0

        # Insertar cada fila como diccionario
        for row_data in all_data:
            try:
                record_dict = {col: val.strip() for col, val in zip(clean_headers, row_data)}
                executor.schema_manager.insert(table_name, record_dict)
                inserted += 1
            except Exception as insert_error:
                print(f"[ERROR] insertando fila {inserted + failed + 1}: {insert_error}")
                failed += 1

        # Verificar que se insertaron los datos
        verify = executor.schema_manager.select(table_name, ["*"], None)
        print(f"[DEBUG] Registros en {table_name}: {len(verify)}")

        return {
            "ok": True,
            "fileName": file.filename,
            "tableName": table_name,
            "fileSize": f"{round(os.path.getsize(save_path)/1024, 2)} KB",
            "recordCount": record_count,
            "inserted": inserted,
            "failed": failed,
            "headers": clean_headers,
            "rows": rows,
            "message": f"Tabla '{table_name}' creada y persistida. Insertados: {inserted}, Fallidos: {failed}"
        }

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[ERROR] upload: {error_detail}")
        return JSONResponse(
            content={"ok": False, "error": str(e), "detail": error_detail},
            status_code=500
        )

@app.post("/create_index")
def create_index(request: IndexRequest):
    """
    Crea un índice en la tabla especificada usando el motor DBMS.
    """
    try:
        idx_type = request.index_type.lower()
        if idx_type not in ("sequential", "isam", "btree", "hash", "rtree", "kdtree"):
            return {"ok": False, "error": f"Index type '{request.index_type}' not implemented yet. Available: sequential, isam, btree, hash, rtree, kdtree"}

        # If explicit columns array provided and spatial index requested, call SchemaManager helper
        if request.columns and idx_type in ("rtree", "kdtree"):
            cols = request.columns
            # validate list
            if not isinstance(cols, list) or len(cols) == 0:
                return {"ok": False, "error": "columns must be a non-empty list when provided"}
            # call SchemaManager helper to build multi-column spatial index
            res = executor.schema_manager.create_index_multi(request.table_name, cols, idx_type)
            return {"ok": True, "message": res}

        # Fallback to legacy single-column create via executor (parses CREATE INDEX SQL)
        if not request.column:
            return {"ok": False, "error": "Missing 'column' for index creation"}
        query = f"CREATE INDEX {idx_type} ON {request.table_name} ({request.column})"
        result = executor.execute(query)
        return {"ok": True, "message": f"{idx_type} index created on {request.table_name} column {request.column}", "result": result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}


@app.post("/compare_query")
def compare_query(request: dict):
    """Request body: { table: str, columns: ["col"], condition: str, methods?: ["sequential","isam",...] }
    Returns per-technique timings and disk access counts.
    """
    try:
        table = request.get("table")
        cols = request.get("columns")
        cond = request.get("condition")
        methods = request.get("methods")
        res = executor.schema_manager.compare_query_methods(table, cols, cond, methods=methods)
        return {"ok": True, "result": res}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# -------------------------------
# Esquema/Metadatos
# -------------------------------
@app.get("/get_table_columns")
def get_table_columns(table_name: str):
    try:
        if table_name not in executor.schema_manager.tables:
            return {"ok": False, "error": f"Tabla '{table_name}' no existe"}

        table_info = executor.schema_manager.tables[table_name]
        columns_meta = table_info["schema"].columns  # lista de dicts { name, type }
        column_names = [c.get("name") for c in columns_meta]
        return {"ok": True, "columns": column_names}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/sequential_index_info")
def sequential_index_info(table_name: str, column: str):
    try:
        if table_name not in executor.schema_manager.tables:
            return {"ok": False, "error": f"Tabla '{table_name}' no existe"}
        idx = executor.schema_manager.tables[table_name]["indexes"].get(column)
        if not idx or not hasattr(idx, "info"):
            return {"ok": False, "error": "No sequential index for given table/column"}
        return {"ok": True, "info": idx.info()}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/system_stats")
def system_stats():
    try:
        total_records = 0
        total_tables = len(executor.schema_manager.tables)
        total_indexes = 0
        
        for table_name, table_info in executor.schema_manager.tables.items():
            # Count records in each table
            try:
                records = table_info["file"].scan_all()
                total_records += len(records)
            except:
                pass
            # Count indexes
            total_indexes += len(table_info["indexes"])
        
        return {
            "ok": True,
            "stats": {
                "total_records": total_records,
                "total_tables": total_tables,
                "total_indexes": total_indexes,
                "tables": list(executor.schema_manager.tables.keys())
            }
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

# -------------------------------
# Endpoint: List tables with indexes
# -------------------------------
@app.get("/tables_with_indexes")
def tables_with_indexes():
    try:
        result = []
        for table_name, table_info in executor.schema_manager.tables.items():
            indexed = []
            for col, idx_obj in table_info.get("indexes", {}).items():
                # determine index type
                itype = None
                try:
                    cname = idx_obj.__class__.__name__.lower()
                    if "sequential" in cname or isinstance(idx_obj, type(None)):
                        itype = "sequential"
                    elif "isam" in cname:
                        itype = "isam"
                    elif "bplustree" in cname or "bplus" in cname or "btree" in cname:
                        itype = "btree"
                    elif "extend" in cname or "hash" in cname:
                        itype = "hash"
                    elif "rtree" in cname:
                        itype = "rtree"
                    else:
                        itype = cname
                except Exception:
                    itype = "unknown"
                meta = {"column": col, "type": itype}
                # expose underlying covered columns for spatial indexes
                try:
                    cols = getattr(idx_obj, "_columns", None)
                    if cols:
                        meta["columns"] = list(cols)
                except Exception:
                    pass
                indexed.append(meta)
            if indexed:
                result.append({"table": table_name, "indexes": indexed})
        return {"ok": True, "tables": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/drop_index")
def drop_index(table_name: str, column: str):
    """Remove the index files for a table.column and update the catalog."""
    try:
        executor.schema_manager.drop_index(table_name, column)
        return {"ok": True, "message": f"Index dropped for {table_name}({column})"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/reload_catalog")
def reload_catalog():
    """Reload catalog.json from disk into memory (reinstantiates indexes)."""
    try:
        executor.schema_manager.reload_catalog()
        return {"ok": True, "message": "Catalog reloaded"}
    except Exception as e:
        return {"ok": False, "error": str(e)}