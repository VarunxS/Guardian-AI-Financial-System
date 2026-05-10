# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT 8000

# Set work directory
WORKDIR /app

# Install system dependencies (needed for some python packages like PyMuPDF)
RUN apt-get update && apt-get install -y \
    build-essential \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Expose port
EXPOSE 8000

# Start command (using uvicorn directly for Render's simple setup)
# For Render, we use 0.0.0.0 to bind to all interfaces
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
