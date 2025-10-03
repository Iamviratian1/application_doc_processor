# Clean Document Processor

A sophisticated four-agent document processing system designed for mortgage applications. This system orchestrates document ingestion, data extraction, validation, and formatting through specialized agents.

## Architecture Overview

The system consists of four specialized agents working in coordination:

1. **Document Ingestion Agent** - Handles document upload, validation, and initial processing setup
2. **Data Extraction Agent** - Extracts data using AWS Textract with intelligent field detection
3. **Data Validation Agent** - Cross-validates extracted data against application form data
4. **Data Formatting Agent** - Formats and stores final data in the golden table for decision engine

## Features

- **Multi-document Processing**: Handle multiple documents simultaneously
- **Intelligent Document Classification**: Automatic document type detection
- **AWS Textract Integration**: Advanced OCR and field extraction
- **Data Validation**: Cross-validation between application forms and documents
- **Conflict Resolution**: Smart resolution of data conflicts
- **Golden Table**: Structured final data ready for decision engine
- **Real-time Processing**: Background job processing with status tracking
- **Comprehensive Logging**: Full audit trail of all processing steps

## Quick Start

### Prerequisites

- Python 3.8+
- Supabase account
- AWS account with Textract access
- PostgreSQL database

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd application_document_processor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp env.example .env
# Edit .env with your credentials
```

4. Set up the database:
```bash
# Run the schema creation script
psql -d your_database -f database/schema.sql
```

5. Start the application:
```bash
python main.py
```

## Configuration

### Environment Variables

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `AWS_S3_BUCKET`: S3 bucket for document storage
- `AWS_REGION`: AWS region (default: us-east-1)

### Document Types Supported

- Mortgage Application Forms
- T4 Tax Forms
- Employment Letters
- Bank Statements
- Pay Stubs
- Credit Reports
- Property Assessments
- Insurance Documents

## API Endpoints

### Process Documents
```http
POST /api/v1/process-documents
Content-Type: multipart/form-data

files: [file1, file2, ...]
application_id: string
applicant_type: "applicant" | "co_applicant"
```

### Get Processing Status
```http
GET /api/v1/processing-status/{application_id}
```

### Get Golden Data
```http
GET /api/v1/golden-data/{application_id}
```

### Retry Processing
```http
POST /api/v1/retry-processing/{application_id}
```

### System Metrics
```http
GET /api/v1/metrics
```

## Database Schema

The system uses a comprehensive database schema with the following main tables:

- `applications`: Application metadata and status
- `documents`: Raw document storage and metadata
- `extracted_data`: Data extracted by the extraction agent
- `validation_results`: Validation results from the validation agent
- `golden_data`: Final formatted data for decision engine
- `processing_logs`: Audit trail of all processing steps
- `document_jobs`: Job queue management

## Agent Details

### Document Ingestion Agent
- File validation and type detection
- Storage management
- Initial document classification
- Job queue creation

### Data Extraction Agent
- AWS Textract integration
- Intelligent field extraction
- Confidence scoring
- Raw response storage

### Data Validation Agent
- Cross-validation logic
- Mismatch detection
- Severity assessment
- Flagging for review

### Data Formatting Agent
- Data normalization
- Conflict resolution
- Golden table population
- Quality scoring

## Processing Pipeline

1. **Upload**: Documents are uploaded and validated
2. **Ingestion**: Files are stored and classified
3. **Extraction**: Data is extracted using AWS Textract
4. **Validation**: Extracted data is validated against application forms
5. **Formatting**: Final data is formatted and stored in golden table
6. **Decision Ready**: Data is ready for decision engine

## Monitoring and Logging

The system provides comprehensive monitoring through:

- Real-time processing status
- Detailed processing logs
- Performance metrics
- Error tracking and retry mechanisms

## Error Handling

- Automatic retry mechanisms for failed jobs
- Comprehensive error logging
- Graceful degradation
- Manual intervention capabilities

## Performance Considerations

- Concurrent processing with configurable limits
- Background job processing
- Efficient database queries with proper indexing
- Optimized AWS Textract usage

## Security

- Secure file storage
- Environment variable protection
- Input validation
- Audit trail maintenance

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions, please contact the development team or create an issue in the repository.
