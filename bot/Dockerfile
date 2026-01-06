FROM python:3.11-slim

# Install system dependencies for Discord Voice (Opus and FFmpeg)
RUN apt-get update && apt-get install -y \
    libopus-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]