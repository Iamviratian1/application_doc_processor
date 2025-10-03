# Clean Document Processor Architecture

## Overview

This document processor implements a sophisticated four-agent architecture for processing mortgage documents and applications. The system is designed to handle multiple documents simultaneously, extract data using AWS Textract, validate the extracted data against application forms, and format the final data for decision engine consumption.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Document Processing Orchestrator              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Agent 1:      │  │   Agent 2:      │  │   Agent 3:      │ │
│  │   Document      │  │   Data           │  │   Data           │ │
│  │   Ingestion     │  │   Extraction     │  │   Validation    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Agent 4:      │  │   Job Queue     │  │   Database      │ │
│  │   Data          │  │   Service       │  │   Service       │ │
│  │   Formatting    │  │                 │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Four Agents

### 1. Document Ingestion Agent (`agents/document_ingestion_agent.py`)

**Responsibilities:**
- Document upload validation
- File type detection and classification
- Storage management (Supabase Storage)
- Initial document processing setup
- Job queue creation

**Key Features:**
- Supports multiple file formats (PDF, PNG, JPG, TIFF)
- File size validation (50MB limit)
- Concurrent upload processing
- Automatic document type detection
- Priority-based job creation

**Input:** Raw file content, filename, application_id
**Output:** Document records, storage paths, extraction jobs

### 2. Data Extraction Agent (`agents/data_extraction_agent.py`)

**Responsibilities:**
- AWS Textract integration
- Document analysis and field extraction
- Data type detection and normalization
- Confidence scoring
- Raw response storage

**Key Features:**
- Intelligent query-based extraction
- Form field detection
- Confidence-based filtering
- Document-specific query sets
- Error handling and retry logic

**Input:** Document content, document type
**Output:** Extracted field data, confidence scores, validation jobs

### 3. Data Validation Agent (`agents/data_validation_agent.py`)

**Responsibilities:**
- Cross-validation of application form vs document data
- Data consistency checks
- Mismatch detection and severity assessment
- Flagging for manual review
- Validation confidence scoring

**Key Features:**
- Field-specific validation rules
- Severity-based mismatch classification
- Similarity scoring algorithms
- Critical field identification
- Comprehensive validation reporting

**Input:** Application form data, extracted document data
**Output:** Validation results, mismatch flags, formatting jobs

### 4. Data Formatting Agent (`agents/data_formatting_agent.py`)

**Responsibilities:**
- Data normalization and formatting
- Conflict resolution between sources
- Golden table population
- Data quality scoring
- Final data structure preparation

**Key Features:**
- Source preference rules
- Data type-specific formatting
- Quality metrics calculation
- Decision engine readiness assessment
- Comprehensive data categorization

**Input:** Validation results, application data
**Output:** Golden table records, quality metrics

## Supporting Services

### Database Service (`services/database_service.py`)
- Supabase integration
- CRUD operations for all entities
- Transaction management
- Query optimization

### Storage Service (`services/storage_service.py`)
- File upload/download management
- Supabase Storage integration
- URL generation
- File lifecycle management

### Textract Service (`services/textract_service.py`)
- AWS Textract API integration
- Document analysis management
- Result processing
- Error handling

### Job Queue Service (`services/job_queue_service.py`)
- Background job processing
- Priority-based scheduling
- Retry mechanisms
- Status tracking

## Database Schema

### Core Tables

1. **applications** - Application metadata and status
2. **documents** - Raw document storage and metadata
3. **extracted_data** - Data extracted by extraction agent
4. **validation_results** - Validation results from validation agent
5. **golden_data** - Final formatted data for decision engine
6. **processing_logs** - Audit trail of all processing steps
7. **document_jobs** - Job queue management

### Key Features
- Comprehensive indexing for performance
- Automatic timestamp management
- JSONB support for flexible metadata
- Foreign key relationships
- Audit trail capabilities

## Configuration System

### Document Configuration (`config/document_config.py`)
- Document type definitions
- Field mappings
- Textract query sets
- Priority configurations

### Validation Configuration (`config/validation_config.py`)
- Field validation rules
- Tolerance settings
- Severity levels
- Critical field identification

### Formatting Configuration (`config/formatting_config.py`)
- Data transformation rules
- Conflict resolution policies
- Quality thresholds
- Output formatting

## Processing Pipeline

```
1. Document Upload
   ↓
2. Ingestion Agent
   ├── File validation
   ├── Type detection
   ├── Storage upload
   └── Job creation
   ↓
3. Extraction Agent
   ├── AWS Textract analysis
   ├── Field extraction
   ├── Confidence scoring
   └── Data storage
   ↓
4. Validation Agent
   ├── Cross-validation
   ├── Mismatch detection
   ├── Severity assessment
   └── Flagging
   ↓
5. Formatting Agent
   ├── Data normalization
   ├── Conflict resolution
   ├── Golden table population
   └── Quality scoring
   ↓
6. Decision Engine Ready
```

## API Endpoints

### Core Endpoints
- `POST /api/v1/process-documents` - Process multiple documents
- `GET /api/v1/processing-status/{application_id}` - Get processing status
- `GET /api/v1/golden-data/{application_id}` - Get golden data summary
- `POST /api/v1/retry-processing/{application_id}` - Retry failed processing
- `GET /api/v1/metrics` - System metrics

### Utility Endpoints
- `GET /api/v1/health` - Health check

## Key Features

### Concurrent Processing
- Multiple documents processed simultaneously
- Configurable concurrency limits
- Background job processing
- Priority-based scheduling

### Error Handling
- Comprehensive error logging
- Automatic retry mechanisms
- Graceful degradation
- Manual intervention capabilities

### Monitoring
- Real-time status tracking
- Performance metrics
- Audit trail
- Quality scoring

### Security
- Secure file storage
- Input validation
- Environment variable protection
- Audit logging

## Data Flow

1. **Upload Phase**: Documents uploaded via API
2. **Ingestion Phase**: Files validated, stored, and classified
3. **Extraction Phase**: Data extracted using AWS Textract
4. **Validation Phase**: Extracted data validated against application forms
5. **Formatting Phase**: Final data formatted and stored in golden table
6. **Decision Phase**: Data ready for decision engine consumption

## Quality Assurance

### Data Quality Metrics
- Verification percentage
- Confidence scoring
- Source reliability
- Completeness assessment

### Validation Levels
- Critical fields (exact match required)
- Important fields (tolerance-based)
- Standard fields (similarity-based)

### Conflict Resolution
- Source preference rules
- Confidence-based selection
- Manual override capabilities
- Audit trail maintenance

## Performance Considerations

### Optimization Strategies
- Database indexing
- Concurrent processing
- Efficient AWS Textract usage
- Caching mechanisms
- Resource pooling

### Scalability
- Horizontal scaling support
- Load balancing capabilities
- Queue-based processing
- Resource monitoring

## Deployment

### Requirements
- Python 3.8+
- Supabase account
- AWS account with Textract access
- PostgreSQL database

### Environment Setup
- Environment variable configuration
- Database schema initialization
- AWS credentials setup
- Supabase project configuration

This architecture provides a robust, scalable, and maintainable solution for document processing in mortgage applications, with clear separation of concerns and comprehensive error handling.
