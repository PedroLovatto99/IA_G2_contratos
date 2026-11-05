FROM python:3.12-slim

WORKDIR /app

# versao CPU do torch: evita baixar varios GB de bibliotecas CUDA
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 8000
