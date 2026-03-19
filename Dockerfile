FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ffmpeg \
       ca-certificates \
       curl \
       git \
       libffi-dev \
       libgmp-dev \
       gcc \
       python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for caching
COPY requirements.txt /app/

# Install dependencies (skip playwright browser for now, install later if needed)
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application (lib, scripts, etc.)
COPY . /app

# Finalize project install (scripts/metadata)
RUN pip install --no-cache-dir .

# Default command starts the OpenAI-compatible API
EXPOSE 8000
CMD ["uvicorn", "lib.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
