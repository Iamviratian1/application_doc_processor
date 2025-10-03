# Application Document Processor

A comprehensive four-agent document processing system for mortgage applications, built with FastAPI, PostgreSQL, and AWS Textract.

## 🚀 Features

- **Document Ingestion Agent**: File upload, validation, and storage
- **Data Extraction Agent**: AWS Textract integration for intelligent field extraction
- **Data Validation Agent**: Field comparison and validation against application data
- **Data Formatting Agent**: Final data formatting and golden record creation

## 🏗️ Architecture

The system uses a microservices architecture with four specialized agents:

1. **Document Ingestion Agent**: Handles file uploads, validation, and initial processing
2. **Data Extraction Agent**: Uses AWS Textract to extract structured data from documents
3. **Data Validation Agent**: Compares extracted data against application form data
4. **Data Formatting Agent**: Creates final formatted records for decision-making

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python 3.11)
- **Database**: PostgreSQL with JSONB support
- **Cloud Services**: AWS Textract for OCR and data extraction
- **Containerization**: Docker & Docker Compose
- **Storage**: Local file system with S3 integration
- **API**: RESTful API with comprehensive endpoints

## 📋 Prerequisites

- Docker and Docker Compose
- AWS Account with Textract access
- Python 3.11+ (for local development)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/Iamviratian1/application_doc_processor.git
cd application_doc_processor
```

### 2. Configure Environment

Copy the environment file and update with your AWS credentials:

```bash
cp env.example env.docker
# Edit env.docker with your AWS credentials
```

### 3. Start the System

```bash
docker-compose up -d
```

### 4. Verify Installation

```bash
curl http://localhost:8000/health
```

## 📚 API Endpoints

### Core Endpoints

- **`POST /api/v1/process-documents`** - Upload documents for processing
- **`GET /api/v1/extracted-fields/{application_id}`** - Get all extracted fields
- **`GET /api/v1/field-status/{application_id}`** - Get field status with validation
- **`GET /api/v1/validation-results/{application_id}`** - Get validation results
- **`GET /api/v1/golden-data/{application_id}`** - Get final formatted data

### Management Endpoints

- **`GET /api/v1/application/{application_id}`** - Get application details
- **`GET /api/v1/processing-status/{application_id}`** - Get processing status
- **`GET /api/v1/required-documents/{application_id}`** - Get required documents
- **`GET /api/v1/missing-fields/{application_id}`** - Get missing fields

## 📄 Supported Document Types

- **Mortgage Application Forms** - Primary application data
- **Driver's Licenses** - Identity verification
- **Employment Letters** - Income verification
- **Bank Statements** - Financial verification
- **T4 Forms** - Tax information
- **Utility Bills** - Address verification
- **Marriage Certificates** - Marital status
- **PR Cards** - Residency status
- **Rental Agreements** - Housing information

## 🔧 Configuration

### Document Configuration

Document types and field mappings are configured in `config/documents.yaml`:

```yaml
mortgage_application:
  classification_keywords: ["mortgage", "application", "loan"]
  mandatory_for_applicant: true
  extraction_queries:
    - query: "What is the applicant's first name?"
      field_name: "applicant_first_name"
      field_type: "text"
      page: 1
```

### Validation Configuration

Validation rules are defined in `config/validation_config.py`:

```python
VALIDATION_RULES = {
    "applicant_first_name": {
        "required": True,
        "data_type": "text",
        "min_length": 2,
        "max_length": 50
    }
}
```

## 🧪 Testing

### Test Documents

Sample documents are provided in the `test_documents/` directory:

- `Mortgage_Application_Form.pdf` - Sample mortgage application
- `ontario-drivers-license.jpg` - Sample driver's license
- `employement letter.jpg` - Sample employment letter
- And more...

### Running Tests

```bash
# Test the complete workflow
python test_mortgage_application.py

# Test individual components
python test_local_documents.py
```

## 📊 Database Schema

The system uses PostgreSQL with the following key tables:

- **`applications`** - Application metadata
- **`documents`** - Document information and metadata
- **`extracted_data`** - Extracted field data (JSONB)
- **`validation_results`** - Validation results and summaries
- **`golden_data`** - Final formatted records
- **`processing_logs`** - Processing status and logs
- **`document_jobs`** - Job queue management

## 🔍 Monitoring and Logging

- **Processing Logs**: Real-time processing status
- **Validation Results**: Field-by-field validation status
- **Error Tracking**: Comprehensive error logging
- **Performance Metrics**: Processing times and success rates

## 🚀 Deployment

### Production Deployment

1. Update `env.docker` with production AWS credentials
2. Configure database connection settings
3. Set up proper logging and monitoring
4. Deploy using Docker Compose or Kubernetes

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/document_processor

# AWS
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# Application
LOG_LEVEL=INFO
MAX_FILE_SIZE=10485760
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

- Create an issue in the GitHub repository
- Check the documentation in the `docs/` directory
- Review the architecture overview in `ARCHITECTURE.md`

## 🎯 Roadmap

- [ ] Additional document type support
- [ ] Enhanced validation rules
- [ ] Real-time processing dashboard
- [ ] API rate limiting
- [ ] Advanced error handling
- [ ] Performance optimizations

---

**Built with ❤️ for efficient document processing**