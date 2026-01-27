# ===============================================================
# Script Name: Dockerfile
# Script Location: /opt/RealmQuest/api/Dockerfile
# Date: 2026-01-27
# Version: 18.9.4 (Fixes Volume Trap)
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

# --- OPTIMIZATION: PERSISTENT CACHE POINTERS ---
ENV SENTENCE_TRANSFORMERS_HOME=/app/data/cache
ENV TRANSFORMERS_CACHE=/app/data/cache
ENV HF_HOME=/app/data/cache

# --- NEW: PACK MANAGEMENT TOOLS ---
RUN pip install --no-cache-dir redis pymongo chromadb sentence-transformers

# --- THE FIX: COPY TO ROOT (Avoids Volume Overwrite) ---
COPY packs_bundle /packs
# -------------------------------------------------------

# Copy Source Code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]