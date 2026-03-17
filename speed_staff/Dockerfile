# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Create logs directory
RUN mkdir -p /app/logs

# Make entrypoint script executable
RUN chmod +x /app/start.sh

# Run the entrypoint script
CMD ["/app/start.sh"]

# FROM python:3.12-slim

# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1

# WORKDIR /app

# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     libpq-dev \
#     gcc \
#     postgresql-client \
#     && rm -rf /var/lib/apt/lists/*

# COPY requirements.txt /app/
# RUN pip install --upgrade pip && \
#     pip install --no-cache-dir -r requirements.txt

# COPY . /app/

# RUN mkdir -p /app/logs /app/uploads

# RUN chmod +x /app/start.sh

# CMD ["/app/start.sh"]

