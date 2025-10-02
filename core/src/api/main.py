from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import shutil
import csv

from src.parser.executor import Executor

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

class IndexRequest(BaseModel):
    index_type: str
    table_name: str

# -------------------------------
# ENDPOINTS
# -------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "message": "Backend running!"}

@app.post("/query")
def run_query(request: QueryRequest):
    try:
        print(f"Query recibida: {request.query}")  # Debug
        result = executor.execute(request.query)
        print(f"Resultado: {result}")  # Debug - VER ESTO
        print(f"Tipo resultado: {type(result)}")  # Debug
        return {"ok": True, "result": result}
    except Exception as e:
        print(f"Error: {str(e)}")  # Debug
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), table_name: str = Form("uploaded_table")):
    try:
        os.makedirs("data", exist_ok=True)
        save_path = os.path.join("data", file.filename)

        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        headers = []
        rows = []
        all_data = []
        record_count = 0
        
        with open(save_path, newline='', encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader)
            
            for i, row in enumerate(reader):
                all_data.append(row)
                if i < 10:
                    rows.append(row)
                record_count = i + 1

        clean_headers = [col.strip().replace(' ', '_').replace('-', '_').lower() for col in headers]
        columns_def = ", ".join([f"{col} VARCHAR[100]" for col in clean_headers])
        create_query = f'CREATE TABLE {table_name} ({columns_def})'
        
        print(f"Ejecutando CREATE: {create_query}")
        executor.execute(create_query)

        inserted = 0
        failed = 0
        
        for row_data in all_data:
            try:
                formatted_values = []
                for val in row_data:
                    val_str = str(val).strip()
                    if val_str.replace('.', '').replace('-', '').isdigit():
                        formatted_values.append(val_str)
                    else:
                        val_escaped = val_str.replace("'", "''")
                        formatted_values.append(f"'{val_escaped}'")
                
                values_str = ", ".join(formatted_values)
                insert_query = f"INSERT INTO {table_name} VALUES ({values_str})"
                
                print(f"INSERT query: {insert_query}")  # ← AGREGAR ESTO
                result = executor.execute(insert_query)
                print(f"INSERT result: {result}")  # ← AGREGAR ESTO
                inserted += 1
                
            except Exception as insert_error:
                print(f"Error insertando fila {inserted + failed + 1}: {insert_error}")
                import traceback
                traceback.print_exc()  # ← AGREGAR ESTO para ver el error completo
                failed += 1

        # Verificar que se insertaron los datos
        verify_query = f"SELECT * FROM {table_name}"
        verify_result = executor.execute(verify_query)
        print(f"Verificación - registros en tabla: {len(verify_result)}")  # ← AGREGAR ESTO

        return {
            "ok": True,
            "fileName": file.filename,
            "fileSize": f"{round(os.path.getsize(save_path)/1024, 2)} KB",
            "recordCount": record_count,
            "inserted": inserted,
            "failed": failed,
            "headers": clean_headers,
            "rows": rows,
            "message": f"Tabla '{table_name}' creada. Insertados: {inserted}, Fallidos: {failed}"
        }
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error en upload: {error_detail}")
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
        # Aquí decides cómo se traduce la petición a una consulta en tu motor
        query = f"CREATE INDEX {request.index_type.upper()} ON {request.table_name}"
        result = executor.execute(query)
        return {"ok": True, "message": f"{request.index_type} index created on {request.table_name}", "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}
