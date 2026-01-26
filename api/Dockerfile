# ===============================================================
# Script Name: Dockerfile
# Script Location: /opt/RealmQuest/api/Dockerfile
# Date: 2026-01-26
# Version: 18.9.0
# About: Hard-coded Model Cache to prevent boot loops
# ===============================================================

FROM python:3.11-slim

# Install System Dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    libopus-dev \
    libopus0 \
    libffi-dev \
    libsodium-dev \
    ffmpeg \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- OPTIMIZATION: FORCE MODEL PERSISTENCE ---
# We set the cache directory explicitly so it survives the build
ENV SENTENCE_TRANSFORMERS_HOME=/app/data/cache
ENV TRANSFORMERS_CACHE=/app/data/cache
ENV HF_HOME=/app/data/cache

# Create dir and Pre-download the model into the image
RUN mkdir -p /app/data/cache && \
    python3 -c "import chromadb.utils.embedding_functions as ef; ef.DefaultEmbeddingFunction()"

# Copy Source Code
COPY . .

EXPOSE 8000

# CMD: Crucial! Host must be 0.0.0.0 to be visible outside Docker
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]