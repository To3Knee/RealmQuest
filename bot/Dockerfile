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
# Install dependencies (Git required for voice-recv)
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
