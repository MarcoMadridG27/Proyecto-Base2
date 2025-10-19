FROM python:3.12-slim

# 1) Dependencias del sistema: libspatialindex + toolchain (por si rtree compila)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libspatialindex-dev build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2) Instalar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3) Copiar el proyecto
COPY . .

# 4) Que Python vea /app como raíz de módulos
ENV PYTHONPATH=/app

EXPOSE 8000

# 5) Arranque (si vas a usar --reload, corre en dev; en prod quítalo)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
