FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# EXPOSE port 8000
EXPOSE 8000

# CMD: Crucial! Host must be 0.0.0.0 to be visible outside Docker
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

RUN pip install --upgrade pip && \
    pip install --default-timeout=300 --retries 10 --no-cache-dir -r requirements.txt