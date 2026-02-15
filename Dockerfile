# Multi-stage Dockerfile for OptiMATE
FROM python:3.10-slim as python-base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    ca-certificates \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 18.x manually (avoids apt permission issues)
# Cache bust: 2026-02-15-v2
ENV NODE_VERSION=18.20.6
RUN curl -fsSL https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz -o node.tar.xz \
    && tar -xf node.tar.xz -C /usr/local --strip-components=1 \
    && rm node.tar.xz \
    && node --version \
    && npm --version

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
