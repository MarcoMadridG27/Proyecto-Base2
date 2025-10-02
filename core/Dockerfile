FROM python:3.12-slim

WORKDIR /app

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código
COPY . .

# Configurar PYTHONPATH para que reconozca 'src' como módulo raíz
ENV PYTHONPATH=/app

# Exponer puerto
EXPOSE 8000

# Comando para iniciar uvicorn
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]