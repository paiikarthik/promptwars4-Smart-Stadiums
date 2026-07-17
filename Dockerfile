# Use official lightweight Python image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if any are needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=8080
ENV TESTING=true

EXPOSE 8080

# Start server using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "extended_app:app"]
