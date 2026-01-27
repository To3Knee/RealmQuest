FROM python:3.10-slim-bullseye

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

COPY requirements.txt .
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# --- CRITICAL PATCH: VOICE ENCRYPTION FIX ---
# This fixes the "CryptoError" / cutting off sentences
RUN pip install --force-reinstall "git+https://github.com/imayhaveborkedit/discord-ext-voice-recv"
# --------------------------------------------

COPY . .

CMD ["python", "main.py"]