FROM python:3.10-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    KMP_DUPLICATE_LIB_OK=TRUE

WORKDIR /app

# Install system dependencies (libgomp1 required for FAISS / OpenMP)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Install PyTorch CPU-only version (saves ~2GB container size)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install remaining Python dependencies
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    transformers \
    faiss-cpu \
    pillow \
    scikit-learn \
    requests \
    beautifulsoup4 \
    pydantic

# Create necessary directories
RUN mkdir -p /app/backend /app/data /app/clothes /app/crops

# Copy backend code
COPY backend /app/backend

# Pre-seed initial database files, catalog index, wardrobe, and garment images
COPY data /app/data
COPY clothes /app/clothes
COPY crops /app/crops

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
