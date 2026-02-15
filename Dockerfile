# Multi-stage Dockerfile for OptiMATE
FROM python:3.10-slim as python-base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Set working directory
WORKDIR /app

# Copy backend requirements and install Python dependencies
COPY backend/requirements.txt ./backend/
RUN cd backend && pip install --no-cache-dir -r requirements.txt

# Copy frontend package files and install Node dependencies
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci

# Copy entire project
COPY . .

# Build frontend
RUN cd frontend && npm run build

# Expose port (Render will assign PORT env var)
EXPOSE 3000

# Start command
CMD cd frontend && npm start
