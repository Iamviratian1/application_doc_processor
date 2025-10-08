"""
Clean Document Processor - Essential Endpoints Only
This file contains only the necessary endpoints for production use.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn

# Import orchestrator
from orchestrator import DocumentProcessingOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize orchestrator
try:
    from agents.document_ingestion_agent import DocumentIngestionAgent
    from agents.data_extraction_agent import DataExtractionAgent
    from agents.data_validation_agent import DataValidationAgent
    from services.database_service import DatabaseService
    from services.job_queue_service import JobQueueService
    from orchestrator import DocumentProcessingOrchestrator
    
    orchestrator = DocumentProcessingOrchestrator()
    logger.info("Orchestrator initialized successfully")
    
except Exception as e:
    logger.error(f"Failed to initialize orchestrator: {e}")
    import traceback
    logger.error(f"Traceback: {traceback.format_exc()}")
    raise e

def detect_document_type(filename: str) -> str:
    """Auto-detect document type based on filename patterns"""
    if not filename:
        return "unknown"
    
    filename_lower = filename.lower()
    
    # Driver's License patterns
    if any(keyword in filename_lower for keyword in ['driver', 'license', 'dl', 'drivers']):
        return "drivers_license"
    
    # Passport patterns
    if any(keyword in filename_lower for keyword in ['passport', 'pass']):
        return "passport"
    
    # PR Card patterns
    if any(keyword in filename_lower for keyword in ['pr', 'permanent', 'residence', 'prcard']):
        return "pr_card"
    
    # Employment Letter patterns
    if any(keyword in filename_lower for keyword in ['employment', 'job', 'work', 'letter', 'offer']):
        return "employment_letter"
    
    # Pay Stub patterns
    if any(keyword in filename_lower for keyword in ['pay', 'stub', 'payslip', 'salary', 'wage']):
        return "pay_stub"
    
    # T4 Form patterns
    if any(keyword in filename_lower for keyword in ['t4', 'tax', 'income', 't4form']):
        return "t4_form"
    
    # Bank Statement patterns
    if any(keyword in filename_lower for keyword in ['bank', 'statement', 'account', 'financial']):
        return "bank_statement"
    
    # Credit Report patterns
    if any(keyword in filename_lower for keyword in ['credit', 'report', 'score', 'bureau']):
        return "credit_report"
    
    # Mortgage Application patterns
    if any(keyword in filename_lower for keyword in ['mortgage', 'application', 'loan', 'app']):
        return "mortgage_application"
    
    # Property documents
    if any(keyword in filename_lower for keyword in ['property', 'house', 'home', 'purchase', 'sale']):
        return "purchase_agreement"
    
    # Insurance documents
    if any(keyword in filename_lower for keyword in ['insurance', 'policy', 'binder']):
        return "property_insurance"
    
    # Tax documents
    if any(keyword in filename_lower for keyword in ['tax', 'assessment', 'bill']):
        return "property_tax_bill"
    
    # Condo documents
    if any(keyword in filename_lower for keyword in ['condo', 'status', 'certificate', 'mls']):
        return "condo_status_certificate"
    
    # Default to unknown if no pattern matches
    return "unknown"

# Pydantic models
class ApplicationCreateRequest(BaseModel):
    applicant_name: str
    
    class Config:
        schema_extra = {
            "example": {
                "applicant_name": "John Doe"
            }
        }

# DocumentUploadRequest removed - using Form data instead

class ProcessingStatusResponse(BaseModel):
    application_id: str
    status: str
    total_documents: int
    processed_documents: int
    pending_documents: int
    failed_documents: int
    processing_percentage: float

class ValidationResponse(BaseModel):
    application_id: str
    validation_summary: Dict[str, Any]
    validation_results: List[Dict[str, Any]]
    golden_data_saved: bool

class GoldenDataResponse(BaseModel):
    application_id: str
    golden_data: Optional[Dict[str, Any]] = None
    status: str

# FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    try:
        logger.info("Starting Clean Document Processor")
        
        # Start job processor
        try:
            logger.info("Starting job processor")
            job_processor_task = asyncio.create_task(orchestrator.start_job_processor())
            logger.info("Job processor task created")
            
            # Store task reference for cleanup
            app.state.job_processor_task = job_processor_task
            
        except Exception as e:
            logger.error(f"Failed to start job processor: {str(e)}")
        
        logger.info("Clean Document Processor started successfully")
        
        yield
        
        # Cleanup
        if hasattr(app.state, 'job_processor_task'):
            app.state.job_processor_task.cancel()
            try:
                await app.state.job_processor_task
            except asyncio.CancelledError:
                pass
        
    except Exception as e:
        logger.error(f"Error in lifespan manager: {str(e)}")
        raise e

app = FastAPI(
    title="Clean Document Processor",
    description="AI-powered document processing system for mortgage applications",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper functions
def _values_match(value1: str, value2: str) -> bool:
    """Check if two values match (with normalization)"""
    if not value1 or not value2:
        return False
    
    # Normalize values for comparison
    v1 = str(value1).strip().lower().replace('"', '').replace("'", '')
    v2 = str(value2).strip().lower().replace('"', '').replace("'", '')
    
    # Exact match
    if v1 == v2:
        return True
    
    # Check for partial matches (for addresses, names, etc.)
    if len(v1) > 3 and len(v2) > 3:
        # Check if one contains the other (for addresses)
        if v1 in v2 or v2 in v1:
            return True
        
        # Check similarity for names
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, v1, v2).ratio()
        if similarity > 0.8:  # 80% similarity threshold
            return True
    
    return False

def _get_mismatch_severity(field_name: str, app_value: str, doc_value: str) -> str:
    """Determine the severity of a field mismatch"""
    critical_fields = ['sin', 'date_of_birth', 'first_name', 'last_name']
    
    if field_name.lower() in critical_fields:
        return "critical"
    
    # Check if it's a financial field
    if any(keyword in field_name.lower() for keyword in ['income', 'salary', 'amount', 'balance']):
        return "high"
    
    return "medium"

# ============================================================================
# ESSENTIAL ENDPOINTS
# ============================================================================

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Clean Document Processor",
        "version": "1.0.0",
        "agents": [
            "Document Ingestion Agent",
            "Data Extraction Agent", 
            "Data Validation Agent"
        ]
    }

@app.post("/api/v1/create-application")
async def create_application(request: ApplicationCreateRequest):
    """Create a new mortgage application"""
    try:
        # Generate unique application ID
        import uuid
        application_id = f"APP_{uuid.uuid4().hex[:8].upper()}"
        
        application_data = {
            "application_id": application_id,
            "applicant_name": request.applicant_name,
            "applicant_email": "not_provided@example.com",  # Default email since not required
            "application_type": "mortgage",
            "status": "document_upload",
            "meta_data": {
                "created_via": "api",
                "created_at": "2025-01-01T00:00:00Z"
            }
        }
        result = await orchestrator.create_application(application_data)
        return result
    except Exception as e:
        logger.error(f"Error creating application: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/process-documents")
async def process_documents(
    application_id: str = Form(...),
    files: List[UploadFile] = File(default=[])
):
    """Upload and process multiple documents for an application"""
    try:
        # Step 1: File Validation
        from agents.file_validation_agent import FileValidationAgent
        from config.yaml_config import YAMLConfigLoader
        
        # Initialize file validation agent
        config_loader = YAMLConfigLoader()
        file_validator = FileValidationAgent(config_loader)
        
        logger.info(f"=== FILE UPLOAD DEBUG ===")
        logger.info(f"Received {len(files) if files else 0} files for application {application_id}")
        logger.info(f"Files type: {type(files)}")
        if files:
            for i, file in enumerate(files):
                logger.info(f"File {i}: {file.filename if file and hasattr(file, 'filename') else 'None'}")
        logger.info(f"=== END FILE UPLOAD DEBUG ===")
        
        # Check if files were uploaded
        if not files or len(files) == 0:
            return {
                "application_id": application_id,
                "status": "success",
                "message": "Endpoint working - no files uploaded",
                "total_files": 0,
                "valid_files": 0,
                "invalid_files": 0,
                "processed_files": [],
                "validation_summary": {
                    "total": 0,
                    "valid": 0,
                    "invalid": 0,
                    "errors": []
                }
            }
        
        # Prepare files for validation
        file_tuples = []
        for file in files:
            if file and file.filename:
                file_content = await file.read()
                file_tuples.append((file_content, file.filename))
        
        # Validate files
        validation_result = await file_validator.validate_files(file_tuples, application_id)
        
        # Check if validation passed
        if not validation_result["overall_valid"]:
            return {
                "application_id": application_id,
                "status": "validation_failed",
                "message": "File validation failed",
                "validation_result": validation_result,
                "error": "One or more files failed validation. Please check the validation details."
            }
        
        # Step 2: Process valid files
        logger.info(f"File validation passed for application {application_id}, proceeding with processing")
        
        result = await orchestrator.process_application_documents(
            files=file_tuples,
            application_id=application_id,
            applicant_type="applicant"
        )
        
        # Format response with validation and processing results
        processed_files = []
        for valid_file in validation_result["valid_files"]:
            processed_files.append({
                "file_name": valid_file["filename"],
                "file_size_mb": valid_file["file_size_mb"],
                "file_format": valid_file["file_format"],
                "pages": valid_file.get("pages", 1),
                "status": "processed"
            })
        
        return {
            "application_id": application_id,
            "status": "success",
            "total_files": len(files),
            "valid_files": len(validation_result["valid_files"]),
            "invalid_files": len(validation_result["invalid_files"]),
            "processed_files": processed_files,
            "validation_summary": validation_result["validation_summary"],
            "processing_result": result
        }
    except Exception as e:
        logger.error(f"Error processing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/application/{application_id}")
async def get_application(application_id: str):
    """Get application details"""
    try:
        result = await orchestrator.get_application(application_id)
        if not result:
            raise HTTPException(status_code=404, detail="Application not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting application: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/processing-status/{application_id}")
async def get_processing_status(application_id: str):
    """Get processing status for an application"""
    try:
        status = await orchestrator.get_processing_status(application_id)
        return ProcessingStatusResponse(**status)
    except Exception as e:
        logger.error(f"Error getting processing status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/validate-fields/{application_id}")
async def validate_fields(application_id: str):
    """Validate extracted fields against application form data"""
    try:
        # Get application form data (from mortgage application)
        application_form_data = await orchestrator.db_service.get_application_form_data(application_id)
        if not application_form_data:
            return {
                "application_id": application_id,
                "error": "No application form data found",
                "validation_results": [],
                "golden_data_saved": False
            }
        
        # Get all extracted data from documents
        extracted_data = await orchestrator.db_service.get_extracted_data_by_application(application_id)
        if not extracted_data:
            return {
                "application_id": application_id,
                "error": "No extracted data found",
                "validation_results": [],
                "golden_data_saved": False
            }
        
        # Group extracted data by field name for comparison
        document_fields = {}
        
        # Create a mapping of document_id to document info for better tracking
        document_info = {}
        for data in extracted_data:
            document_info[data.get('document_id')] = {
                'document_type': data.get('document_type'),
                'filename': data.get('filename', 'Unknown'),
                'extraction_method': data.get('extraction_method', 'textract_query')
            }
        
        for data in extracted_data:
            if data.get('extracted_fields'):
                import json
                if isinstance(data['extracted_fields'], str):
                    fields = json.loads(data['extracted_fields'])
                else:
                    fields = data['extracted_fields']
                
                for field in fields:
                    field_name = field.get('field_name')
                    if field_name:
                        if field_name not in document_fields:
                            document_fields[field_name] = []
                        
                        doc_id = data.get('document_id')
                        doc_info = document_info.get(doc_id, {})
                        
                        document_fields[field_name].append({
                            'value': field.get('field_value'),
                            'confidence': field.get('confidence', 0.0),
                            'document_type': doc_info.get('document_type'),
                            'document_id': doc_id,
                            'document_name': doc_info.get('filename', 'Unknown'),
                            'extraction_method': doc_info.get('extraction_method', 'textract_query')
                        })
        
        # Perform validation comparison
        validation_results = []
        validated_count = 0
        mismatch_count = 0
        missing_count = 0
        
        for form_field, form_value in application_form_data.items():
            validation_result = {
                "field_name": form_field,
                "application_value": form_value,
                "document_values": [],
                "validation_status": "missing",
                "confidence_score": 0.0,
                "mismatch_severity": "none",
                "recommended_value": form_value,
                "recommended_source": "application_form"
            }
            
            if form_field in document_fields:
                doc_values = document_fields[form_field]
                validation_result["document_values"] = doc_values
                
                # Find the best matching document value
                best_match = None
                best_confidence = 0.0
                
                for doc_value in doc_values:
                    if _values_match(form_value, doc_value['value']):
                        if doc_value['confidence'] > best_confidence:
                            best_match = doc_value
                            best_confidence = doc_value['confidence']
                
                if best_match:
                    validation_result["validation_status"] = "validated"
                    validation_result["confidence_score"] = best_confidence
                    validation_result["recommended_value"] = best_match['value']
                    validation_result["recommended_source"] = "document_extraction"
                    validated_count += 1
                else:
                    # Values don't match - determine severity
                    validation_result["validation_status"] = "mismatch"
                    validation_result["confidence_score"] = max([v['confidence'] for v in doc_values])
                    validation_result["mismatch_severity"] = _get_mismatch_severity(form_field, form_value, doc_values[0]['value'])
                    mismatch_count += 1
            else:
                missing_count += 1
            
            validation_results.append(validation_result)
        
        # Calculate validation statistics
        total_fields = len(application_form_data)
        validation_percentage = (validated_count / total_fields * 100) if total_fields > 0 else 0
        
        # Prepare validation summary
        validation_summary = {
            "total_fields": total_fields,
            "validated_fields": validated_count,
            "mismatch_fields": mismatch_count,
            "missing_fields": missing_count,
            "validation_percentage": round(validation_percentage, 2)
        }
        
        # Prepare validated fields for golden table (only the BEST validated data)
        validated_fields_for_golden = {}
        for result in validation_results:
            if result["validation_status"] == "validated":
                field_name = result["field_name"]
                
                # Find the best document source (highest confidence)
                best_document = None
                best_confidence = 0.0
                for doc_value in result["document_values"]:
                    if doc_value.get('confidence', 0.0) > best_confidence:
                        best_confidence = doc_value.get('confidence', 0.0)
                        best_document = doc_value
                
                # Store only the best validated data in golden table
                validated_fields_for_golden[field_name] = {
                    "value": result["recommended_value"],
                    "confidence": result["confidence_score"],
                    "source": result["recommended_source"],
                    "best_document": {
                        "document_name": best_document.get('document_name', 'Unknown') if best_document else 'Unknown',
                        "document_type": best_document.get('document_type') if best_document else None,
                        "document_id": str(best_document.get('document_id')) if best_document and best_document.get('document_id') else None,
                        "extraction_method": best_document.get('extraction_method') if best_document else None
                    },
                    "validation_summary": {
                        "total_sources": len(result["document_values"]),
                        "validation_status": result["validation_status"],
                        "mismatch_severity": result["mismatch_severity"]
                    }
                }
        
        # Save to golden table
        golden_data_saved = False
        try:
            success = await orchestrator.db_service.save_golden_data(
                application_id, 
                validated_fields_for_golden, 
                validation_summary
            )
            golden_data_saved = success
        except Exception as e:
            logger.error(f"Error saving golden data: {str(e)}")
            golden_data_saved = False
        
        return {
            "application_id": application_id,
            "validation_summary": validation_summary,
            "validation_results": validation_results,
            "golden_data_saved": golden_data_saved
        }
        
    except Exception as e:
        logger.error(f"Error in field validation: {str(e)}")
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc(), "golden_data_saved": False}

@app.get("/api/v1/validated-fields/{application_id}")
async def get_validated_fields(application_id: str):
    """Get validated fields that are matching between application form and documents"""
    try:
        # Get application form data
        application_form_data = await orchestrator.db_service.get_application_form_data(application_id)
        
        if not application_form_data:
            return {
                "application_id": application_id,
                "validated_fields": [],
                "total_validated": 0,
                "status": "not_found",
                "message": "No application form data found"
            }
        
        # Get extracted data and group by field
        extracted_data = await orchestrator.db_service.get_extracted_data_by_application(application_id)
        
        if not extracted_data:
            return {
                "application_id": application_id,
                "validated_fields": [],
                "total_validated": 0,
                "status": "not_found",
                "message": "No extracted data found"
            }
        
        # Group extracted data by field name for comparison
        document_fields = {}
        
        # Create a mapping of document_id to document info for better tracking
        document_info = {}
        for data in extracted_data:
            document_info[data.get('document_id')] = {
                'document_type': data.get('document_type'),
                'filename': data.get('filename', 'Unknown'),
                'extraction_method': data.get('extraction_method', 'textract_query')
            }
        
        for data in extracted_data:
            if data.get('extracted_fields'):
                import json
                if isinstance(data['extracted_fields'], str):
                    fields = json.loads(data['extracted_fields'])
                else:
                    fields = data['extracted_fields']
                
                for field in fields:
                    field_name = field.get('field_name')
                    if field_name:
                        if field_name not in document_fields:
                            document_fields[field_name] = []
                        
                        doc_id = data.get('document_id')
                        doc_info = document_info.get(doc_id, {})
                        
                        document_fields[field_name].append({
                            'value': field.get('field_value'),
                            'confidence': field.get('confidence', 0.0),
                            'document_type': doc_info.get('document_type'),
                            'document_id': doc_id,
                            'document_name': doc_info.get('filename', 'Unknown'),
                            'extraction_method': doc_info.get('extraction_method', 'textract_query')
                        })
        
        # Find validated fields (matching between application form and documents)
        validated_fields = []
        
        for form_field, form_value in application_form_data.items():
            if form_field in document_fields:
                doc_values = document_fields[form_field]
                
                # Check if any document value matches the application form value
                matching_documents = []
                for doc_value in doc_values:
                    if _values_match(form_value, doc_value['value']):
                        matching_documents.append({
                            'document_name': doc_value.get('document_name', 'Unknown'),
                            'document_type': doc_value.get('document_type'),
                            'document_id': str(doc_value.get('document_id')) if doc_value.get('document_id') else None,
                            'confidence': doc_value.get('confidence', 0.0),
                            'extraction_method': doc_value.get('extraction_method', 'textract_query')
                        })
                
                if matching_documents:
                    # Find the best match (highest confidence)
                    best_match = max(matching_documents, key=lambda x: x['confidence'])
                    
                    validated_fields.append({
                        'field_name': form_field,
                        'application_value': form_value,
                        'validated_value': form_value,  # The validated value is the same as application value when they match
                        'confidence': best_match['confidence'],
                        'best_document': best_match,
                        'total_sources': len(matching_documents),
                        'validation_status': 'validated'
                    })
        
        return {
            "application_id": application_id,
            "validated_fields": validated_fields,
            "total_validated": len(validated_fields),
            "validation_summary": {
                "total_application_fields": len(application_form_data),
                "validated_fields": len(validated_fields),
                "validation_percentage": round((len(validated_fields) / len(application_form_data)) * 100, 2) if application_form_data else 0
            },
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error getting validated fields: {str(e)}")
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}

@app.get("/api/v1/golden-data/{application_id}")
async def get_golden_data(application_id: str):
    """Get golden data for an application"""
    try:
        golden_data = await orchestrator.db_service.get_golden_data(application_id)
        if not golden_data:
            return {
                "application_id": application_id,
                "error": "No golden data found",
                "golden_data": None
            }
        
        return {
            "application_id": application_id,
            "golden_data": golden_data,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error getting golden data: {str(e)}")
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


@app.get("/api/v1/extracted-fields/{application_id}")
async def get_extracted_fields(application_id: str):
    """Get all extracted fields for an application"""
    try:
        extracted_data = await orchestrator.db_service.get_extracted_data_by_application(application_id)
        
        if not extracted_data:
            return {
                "application_id": application_id,
                "extracted_fields": [],
                "total_fields": 0,
                "message": "No extracted data found"
            }
        
        # Combine all extracted fields
        all_fields = []
        for data in extracted_data:
            if data.get('extracted_fields'):
                import json
                if isinstance(data['extracted_fields'], str):
                    fields = json.loads(data['extracted_fields'])
                else:
                    fields = data['extracted_fields']
                
                for field in fields:
                    field['document_id'] = data.get('document_id')
                    field['extracted_at'] = data.get('extracted_at')
                    all_fields.append(field)
        
        return {
            "application_id": application_id,
            "extracted_fields": all_fields,
            "total_fields": len(all_fields),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error getting extracted fields: {str(e)}")
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}

@app.get("/api/v1/simple-missing-fields/{application_id}")
async def simple_missing_fields(application_id: str):
    """Get missing fields from the entire application - fields that should be extracted from all documents combined"""
    try:
        # Get extracted data directly from database
        extracted_data = await orchestrator.db_service.get_extracted_data_by_application(application_id)
        
        if not extracted_data:
            return {
                "application_id": application_id,
                "missing_fields": [],
                "total_missing": 0,
                "message": "No extracted data found"
            }
        
        # Collect ALL extracted field names
        extracted_field_names = set()
        for data in extracted_data:
            if data.get('extracted_fields'):
                import json
                if isinstance(data['extracted_fields'], str):
                    fields = json.loads(data['extracted_fields'])
                else:
                    fields = data['extracted_fields']
                for field in fields:
                    if field.get('field_name'):
                        extracted_field_names.add(field['field_name'])
        
        # Get uploaded documents
        documents = await orchestrator.db_service.get_documents_by_application(application_id)
        uploaded_doc_types = set()
        for doc in documents:
            uploaded_doc_types.add(doc.get('document_type'))
        
        # Build master field list from all document types (like simple-missing-fields)
        master_field_list = set()
        from config.document_config import DocumentConfig
        doc_config = DocumentConfig()
        all_doc_types = doc_config.yaml_loader.get_document_types()
        
        for doc_type in all_doc_types.keys():
            queries = doc_config.get_queries_for_document_type(doc_type)
            for query in queries:
                if isinstance(query, dict) and "Alias" in query:
                    master_field_list.add(query["Alias"])
        
        # Find missing fields
        missing_fields = master_field_list - extracted_field_names
        
        # Convert to list of field objects with priority
        missing_field_objects = []
        for field_name in missing_fields:
            # Determine priority based on field name
            priority = "medium"
            if any(keyword in field_name.lower() for keyword in ['sin', 'date_of_birth', 'first_name', 'last_name']):
                priority = "high"
            elif any(keyword in field_name.lower() for keyword in ['income', 'salary', 'amount', 'balance']):
                priority = "high"
            
            missing_field_objects.append({
                "field_name": field_name,
                "priority": priority,
                "is_critical": priority == "high"
            })
        
        # Sort by priority (high first)
        missing_field_objects.sort(key=lambda x: (x['priority'] == 'high', x['field_name']), reverse=True)
        
        return {
            "application_id": application_id,
            "missing_fields": missing_field_objects,
            "total_missing": len(missing_field_objects),
            "critical_missing_fields": [f for f in missing_field_objects if f['is_critical']],
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error getting missing fields: {str(e)}")
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
