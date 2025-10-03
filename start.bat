@echo off
REM Clean Document Processor Startup Script for Windows

echo 🚀 Starting Clean Document Processor with Local PostgreSQL...

REM Check if .env file exists
if not exist .env (
    echo ⚠️  .env file not found. Creating from template...
    copy env.docker .env
    echo 📝 Please edit .env file with your AWS credentials before running again.
    echo 🔧 Database will use local PostgreSQL (no changes needed)
    pause
    exit /b 1
)

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker and try again.
    pause
    exit /b 1
)

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ docker-compose is not installed. Please install docker-compose and try again.
    pause
    exit /b 1
)

REM Create logs directory
if not exist logs mkdir logs

REM Build and start services
echo 🔨 Building Docker images...
docker-compose build

echo 🚀 Starting services...
docker-compose up -d

REM Wait for services to be ready
echo ⏳ Waiting for services to be ready...
timeout /t 10 /nobreak >nul

REM Check health
echo 🏥 Checking service health...
curl -f http://localhost:8000/api/v1/health >nul 2>&1
if errorlevel 1 (
    echo ❌ Service health check failed. Check logs with: docker-compose logs
    pause
    exit /b 1
) else (
echo ✅ Document Processor is running successfully!
echo 🌐 API available at: http://localhost:8000
echo 📊 Health check: http://localhost:8000/api/v1/health
echo 📚 API docs: http://localhost:8000/docs
echo 🗄️  PostgreSQL database: localhost:5432/document_processor
echo 📊 Database admin: Connect with postgres/postgres123
)

echo 🎉 Clean Document Processor is ready!
echo.
echo 📋 Quick Commands:
echo   View logs: docker-compose logs -f
echo   Stop services: docker-compose down
echo   Restart: docker-compose restart
echo   Rebuild: docker-compose build --no-cache
echo.
echo 🔧 Configuration:
echo   Edit config: ./config/documents.yaml
echo   Edit environment: .env

pause
