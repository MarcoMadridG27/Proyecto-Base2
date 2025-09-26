# main.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import shutil
import csv

from parser.executor import Executor

# Inicializamos Executor
executor = Executor(data_dir="data")

app = FastAPI(
    title="Mini DB Backend",
    description="Proyecto BD2 - Motor de base de datos con índices",
    version="1.0"
)

# -------------------------------
# MODELOS
# -------------------------------
class QueryRequest(BaseModel):
    query: str

# -------------------------------
# ENDPOINTS
# -------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "message": "Backend running!"}

@app.post("/query")
def run_query(request: QueryRequest):
    try:
        result = executor.execute(request.query)
        return {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), table_name: str = Form("uploaded_table")):
    """
    Sube un archivo CSV, lo guarda en disco, lo registra en el motor
    y devuelve metadata + previsualización.
    """
    try:
        os.makedirs("data", exist_ok=True)
        save_path = os.path.join("data", file.filename)

        # Guardar archivo en /data
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Leer CSV para obtener preview
        headers = []
        rows = []
        with open(save_path, newline='', encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader)  # primera fila
            for i, row in enumerate(reader):
                if i < 10:  # solo las primeras 10 filas
                    rows.append(row)
            record_count = i + 1

        # Ejecutar CREATE TABLE en tu motor (opcional, depende de tu lógica)
        query = f'CREATE TABLE {table_name} FROM FILE "{save_path}"'
        executor.execute(query)

        # Respuesta que tu frontend espera
        return {
            "ok": True,
            "fileName": file.filename,
            "fileSize": f"{round(os.path.getsize(save_path)/1024, 2)} KB",
            "recordCount": record_count,
            "headers": headers,
            "rows": rows
        }
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)
