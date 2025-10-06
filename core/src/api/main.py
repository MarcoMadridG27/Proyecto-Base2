from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import shutil
import csv
import time

from src.parser.executor import Executor
from src.schema_manager import SchemaManager

# Inicializamos Executor
executor = Executor(data_dir="data")

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

class IndexRequest(BaseModel):
    index_type: str
    table_name: str
    column: str  # Asegurarse de que se reciba el nombre de la columna para crear el índice

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
        result = executor.execute(request.query, use_index=use_index)
        execution_time = time.time() - start_time

        # Normalizar salida de SELECT vs otras operaciones
        if isinstance(result, dict) and "result" in result and "used_index" in result:
            return {
                "ok": True,
                "result": result["result"],
                "used_index": result["used_index"],
                "index_warning": result.get("index_warning"),
                "execution_time": execution_time,
            }
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
        # Asegúrate de que el cuerpo de la petición tenga un parámetro 'column' que indique la columna en la que se crea el índice
        idx_type = request.index_type.lower()
        if idx_type not in ("sequential",):
            return {"ok": False, "error": f"Index type '{request.index_type}' not implemented yet. Available: sequential"}
        query = f"CREATE INDEX {idx_type} ON {request.table_name} ({request.column})"

        result = executor.execute(query)
        return {"ok": True, "message": f"{idx_type} index created on {request.table_name} column {request.column}", "result": result}
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