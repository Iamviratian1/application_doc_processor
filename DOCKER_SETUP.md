# Docker Setup Guide

This guide will help you set up and run the Clean Document Processor using Docker.

## Prerequisites

- Docker Desktop installed and running
- Docker Compose installed
- AWS account with Textract access
- Supabase account

## Quick Start

### 1. Clone and Navigate
```bash
cd application_document_processor
```

### 2. Configure Environment
```bash
# Copy the environment template
cp env.docker .env

# Edit .env with your actual credentials
# Required: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, AWS credentials, AWS_S3_BUCKET
```

### 3. Start Services
```bash
# On Windows
start.bat

# On Linux/Mac
./start.sh
```

### 4. Verify Installation
- API: http://localhost:8000
- Health Check: http://localhost:8000/api/v1/health
- API Documentation: http://localhost:8000/docs

## Manual Setup

### 1. Build Docker Image
```bash
docker-compose build
```

### 2. Start Services
```bash
docker-compose up -d
```

### 3. Check Logs
```bash
docker-compose logs -f document-processor
```

### 4. Stop Services
```bash
docker-compose down
```

## Configuration

### Document Types and Fields
Edit `config/documents.yaml` to modify:
- Document types supported
- Fields to extract from each document type
- Validation rules
- Processing configuration

### Environment Variables
Edit `.env` file:
```bash
# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
SUPABASE_STORAGE_BUCKET=documents

# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key_here
AWS_REGION=us-east-1
AWS_S3_BUCKET=your_s3_bucket_name_here

# Application Configuration
LOG_LEVEL=INFO
MAX_FILE_SIZE=52428800
MAX_CONCURRENT_UPLOADS=5
MAX_CONCURRENT_JOBS=3
```

## Services

### Document Processor API
- **Port**: 8000
- **Health Check**: `/api/v1/health`
- **API Docs**: `/docs`

### Redis (Optional)
- **Port**: 6379
- Used for job queue management

### Nginx (Optional)
- **Port**: 80
- Reverse proxy with rate limiting
- File upload size limits

## API Endpoints

### Process Documents
```bash
curl -X POST "http://localhost:8000/api/v1/process-documents" \
  -F "files=@document1.pdf" \
  -F "files=@document2.pdf" \
  -F "application_id=APP123" \
  -F "applicant_type=applicant"
```

### Get Processing Status
```bash
curl "http://localhost:8000/api/v1/processing-status/APP123"
```

### Get Golden Data
```bash
curl "http://localhost:8000/api/v1/golden-data/APP123"
```

## Troubleshooting

### Common Issues

1. **Docker not running**
   ```bash
   # Start Docker Desktop
   # Check: docker info
   ```

2. **Environment variables not set**
   ```bash
   # Check .env file exists and has correct values
   cat .env
   ```

3. **Service not starting**
   ```bash
   # Check logs
   docker-compose logs document-processor
   ```

4. **Health check failing**
   ```bash
   # Check if port 8000 is available
   netstat -an | grep 8000
   ```

### Useful Commands

```bash
# View all logs
docker-compose logs -f

# Restart services
docker-compose restart

# Rebuild without cache
docker-compose build --no-cache

# Stop and remove containers
docker-compose down

# Remove volumes (careful!)
docker-compose down -v
```

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py
```

### Docker Development
```bash
# Build development image
docker-compose -f docker-compose.dev.yml build

# Run with volume mounts for live reload
docker-compose -f docker-compose.dev.yml up
```

## Production Deployment

### Environment Setup
1. Set up production environment variables
2. Configure SSL certificates for Nginx
3. Set up monitoring and logging
4. Configure backup strategies

### Scaling
- Use Docker Swarm or Kubernetes for orchestration
- Scale horizontally with load balancer
- Use external Redis cluster for job queue
- Use managed database services

## Security Considerations

- Use secrets management for sensitive data
- Enable SSL/TLS encryption
- Implement proper authentication
- Regular security updates
- Network segmentation

## Monitoring

### Health Checks
- Application health: `/api/v1/health`
- Docker health checks configured
- Nginx health check endpoint

### Logging
- Application logs: `./logs/`
- Docker logs: `docker-compose logs`
- Structured logging with timestamps

### Metrics
- Processing metrics: `/api/v1/metrics`
- System metrics via Docker stats
- Custom business metrics

## Support

For issues and questions:
1. Check logs: `docker-compose logs -f`
2. Verify configuration: `.env` and `config/documents.yaml`
3. Test connectivity: `curl http://localhost:8000/api/v1/health`
4. Check Docker status: `docker-compose ps`
