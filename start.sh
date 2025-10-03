#!/bin/bash

# Clean Document Processor Startup Script

echo "🚀 Starting Clean Document Processor..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp env.docker .env
    echo "📝 Please edit .env file with your actual credentials before running again."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose and try again."
    exit 1
fi

# Create logs directory
mkdir -p logs

# Build and start services
echo "🔨 Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check health
echo "🏥 Checking service health..."
if curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "✅ Document Processor is running successfully!"
    echo "🌐 API available at: http://localhost:8000"
    echo "📊 Health check: http://localhost:8000/api/v1/health"
    echo "📚 API docs: http://localhost:8000/docs"
else
    echo "❌ Service health check failed. Check logs with: docker-compose logs"
    exit 1
fi

echo "🎉 Clean Document Processor is ready!"
echo ""
echo "📋 Quick Commands:"
echo "  View logs: docker-compose logs -f"
echo "  Stop services: docker-compose down"
echo "  Restart: docker-compose restart"
echo "  Rebuild: docker-compose build --no-cache"
echo ""
echo "🔧 Configuration:"
echo "  Edit config: ./config/documents.yaml"
echo "  Edit environment: .env"
