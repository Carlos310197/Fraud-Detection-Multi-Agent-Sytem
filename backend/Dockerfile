FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app

# Create data directories
RUN mkdir -p /app/app/data/input /app/app/data/store /app/app/data/vector

# Set environment variables
ENV PYTHONPATH=/app
ENV APP_ENV=local
ENV STORAGE_BACKEND=local_json
ENV DATA_DIR=/app/app/data/input
ENV STORE_DIR=/app/app/data/store
ENV VECTOR_DIR=/app/app/data/vector
ENV LLM_PROVIDER=mock
ENV EMBEDDINGS_PROVIDER=mock
ENV WEB_SEARCH_PROVIDER=mock

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
