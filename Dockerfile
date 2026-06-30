FROM python:3.11-slim

# Sistema: ffmpeg + fonts
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fonts-dejavu-core \
    fonts-liberation \
    libgl1 \
    libglib2.0-0 \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar dependencias primero (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY *.py .

# Directorio de trabajo temporal
RUN mkdir -p /tmp/bitacora

# Puerto Render
ENV PORT=8080
ENV OUTPUT_DIR=/tmp/bitacora
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD gunicorn bitacora_server:app \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --timeout 600 \
    --keep-alive 5 \
    --log-level info
