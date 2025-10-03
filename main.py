"""
Main Application Entry Point
Clean Document Processor with Four Agents
"""

import asyncio
import os
from typing import List, Tuple
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from datetime import datetime

from utils.logger import setup_logging, get_logger

# Setup logging
setup_logging(level="INFO")
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Clean Document Processor",
    description="Four-Agent Document Processing System for Mortgage Applications",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator
orchestrator = None
try:
    print("=== MAIN DEBUG: About to initialize orchestrator ===")
    
    # Test individual imports first
    print("=== MAIN DEBUG: Testing individual imports ===")
    try:
        from agents.document_ingestion_agent import DocumentIngestionAgent
        print("=== MAIN DEBUG: DocumentIngestionAgent imported successfully ===")
    except Exception as e:
        print(f"=== MAIN ERROR: DocumentIngestionAgent import failed: {str(e)} ===")
        import traceback
        print(f"=== MAIN TRACEBACK: {traceback.format_exc()} ===")
        raise
    
    try:
        from agents.data_extraction_agent import DataExtractionAgent
        print("=== MAIN DEBUG: DataExtractionAgent imported successfully ===")
    except Exception as e:
        print(f"=== MAIN ERROR: DataExtractionAgent import failed: {str(e)} ===")
        import traceback
        print(f"=== MAIN TRACEBACK: {traceback.format_exc()} ===")
        raise
    
    try:
        from agents.data_validation_agent import DataValidationAgent
        print("=== MAIN DEBUG: DataValidationAgent imported successfully ===")
    except Exception as e:
        print(f"=== MAIN ERROR: DataValidationAgent import failed: {str(e)} ===")
        import traceback
        print(f"=== MAIN TRACEBACK: {traceback.format_exc()} ===")
        raise
    
    try:
        from agents.data_formatting_agent import DataFormattingAgent
        print("=== MAIN DEBUG: DataFormattingAgent imported successfully ===")
    except Exception as e:
        print(f"=== MAIN ERROR: DataFormattingAgent import failed: {str(e)} ===")
        import traceback
        print(f"=== MAIN TRACEBACK: {traceback.format_exc()} ===")
        raise
    
    try:
        from services.database_service import DatabaseService
        print("=== MAIN DEBUG: DatabaseService imported successfully ===")
    except Exception as e:
        print(f"=== MAIN ERROR: DatabaseService import failed: {str(e)} ===")
        import traceback
        print(f"=== MAIN TRACEBACK: {traceback.format_exc()} ===")
        raise
    
    try:
        from services.job_queue_service import JobQueueService
        print("=== MAIN DEBUG: JobQueueService imported successfully ===")
    except Exception as e:
        print(f"=== MAIN ERROR: JobQueueService import failed: {str(e)} ===")
        import traceback
        print(f"=== MAIN TRACEBACK: {traceback.format_exc()} ===")
        raise
    
    print("=== MAIN DEBUG: All imports successful, importing orchestrator ===")
    try:
        from orchestrator import DocumentProcessingOrchestrator
        print("=== MAIN DEBUG: DocumentProcessingOrchestrator imported successfully ===")
    except Exception as e:
        print(f"=== MAIN ERROR: DocumentProcessingOrchestrator import failed: {str(e)} ===")
        import traceback
        print(f"=== MAIN TRACEBACK: {traceback.format_exc()} ===")
        raise
    
    print("=== MAIN DEBUG: All imports successful, initializing orchestrator ===")
    orchestrator = DocumentProcessingOrchestrator()
    print("=== MAIN DEBUG: Orchestrator initialized successfully ===")
    
except Exception as e:
    print(f"=== MAIN ERROR: Failed to initialize orchestrator: {str(e)} ===")
    import traceback
    print(f"=== MAIN TRACEBACK: {traceback.format_exc()} ===")
    # Don't raise - continue without orchestrator for now
    orchestrator = None

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Start the job processor on startup"""
    try:
        logger.info("Starting Clean Document Processor")
        print("=== STARTUP DEBUG: Starting Clean Document Processor ===")
        
        if orchestrator is None:
            logger.error("=== STARTUP ERROR: Orchestrator is None, cannot start job processor ===")
            print("=== STARTUP ERROR: Orchestrator is None, cannot start job processor ===")
            return
        
        # Start the job processor in the background
        logger.info("=== STARTUP DEBUG: About to start job processor ===")
        print("=== STARTUP DEBUG: About to start job processor ===")
        
        # Create the task and store it to prevent garbage collection
        task = asyncio.create_task(orchestrator.job_queue_service.start_job_processor())
        logger.info("=== STARTUP DEBUG: Job processor task created ===")
        print("=== STARTUP DEBUG: Job processor task created ===")
        
        # Store the task reference to prevent it from being garbage collected
        app.state.job_processor_task = task
        
        logger.info("Clean Document Processor started successfully")
        print("=== STARTUP DEBUG: Clean Document Processor started successfully ===")
        
    except Exception as e:
        logger.error(f"=== STARTUP ERROR: Failed to start job processor: {str(e)} ===")
        print(f"=== STARTUP ERROR: Failed to start job processor: {str(e)} ===")
        import traceback
        logger.error(f"=== STARTUP TRACEBACK: {traceback.format_exc()} ===")
        print(f"=== STARTUP TRACEBACK: {traceback.format_exc()} ===")
        # Don't raise - continue without job processor

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the job processor on shutdown"""
    logger.info("Stopping Clean Document Processor")
    if orchestrator is not None:
        await orchestrator.job_queue_service.stop_job_processor()
    logger.info("Clean Document Processor stopped")

# Pydantic models
class ProcessingStatusResponse(BaseModel):
    application_id: str
    application_status: str
    overall_progress: dict
    agent_statuses: dict
    job_status: dict
    ready_for_decision_engine: bool

class GoldenDataResponse(BaseModel):
    application_id: str
    status: str
    total_fields: int
    verified_fields: int
    high_confidence_fields: int
    data_quality_score: float
    categories: dict
    ready_for_decision_engine: bool

class ProcessingMetricsResponse(BaseModel):
    total_applications: int
    completed_applications: int
    processing_applications: int
    failed_applications: int
    completion_rate: float
    pending_jobs: int
    processing_jobs: int
    failed_jobs: int

# API Endpoints

@app.post("/api/v1/create-application")
async def create_application(
    applicant_name: str = Form(...),
    application_type: str = Form(default="mortgage"),
    applicant_type: str = Form(default="applicant")
):
    """
    Create a new application and return the application ID
    
    Args:
        applicant_name: Name of the applicant
        application_type: Type of application (default: mortgage)
        applicant_type: 'applicant' or 'co_applicant'
    
    Returns:
        Application creation result with application_id
    """
    try:
        import uuid
        application_id = f"APP_{uuid.uuid4().hex[:8].upper()}"
        
        logger.info(f"Creating new application: {application_id} for {applicant_name}")
        
        # Create application record
        application_data = {
            "application_id": application_id,
            "applicant_name": applicant_name,
            "application_type": application_type,
            "status": "document_upload",
            "meta_data": {
                "applicant_type": applicant_type,
                "created_via": "api",
                "created_at": datetime.now().isoformat()
            }
        }
        
        result = await orchestrator.create_application(application_data)
        
        if result["success"]:
            return {
                "success": True,
                "application_id": application_id,
                "message": f"Application created successfully for {applicant_name}",
                "data": result
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        logger.error(f"Error creating application: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/process-documents")
async def process_documents(
    files: List[UploadFile] = File(...),
    application_id: str = Form(default=None),
    applicant_type: str = Form(default="applicant")
):
    """
    Process multiple documents for an application
    
    Args:
        files: List of uploaded files
        application_id: Application identifier (optional - will be generated if not provided)
        applicant_type: 'applicant' or 'co_applicant'
    
    Returns:
        Processing result with generated application_id
    """
    try:
        # Generate application ID if not provided
        if not application_id:
            import uuid
            application_id = f"APP_{uuid.uuid4().hex[:8].upper()}"
            logger.info(f"Generated new application ID: {application_id}")
        
        logger.info(f"Processing {len(files)} documents for application {application_id}")
        
        # Convert UploadFile objects to (content, filename) tuples
        file_data = []
        for file in files:
            content = await file.read()
            logger.info(f"File {file.filename}: size={len(content)} bytes, content_type={file.content_type}")
            file_data.append((content, file.filename))
        
        # Process documents
        result = await orchestrator.process_application_documents(
            file_data, application_id, applicant_type
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Documents processed successfully",
                "data": result
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        logger.error(f"Error processing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/application/{application_id}")
async def get_application(application_id: str):
    """
    Get application information
    
    Args:
        application_id: Application identifier
    
    Returns:
        Application information
    """
    try:
        application = await orchestrator.get_application(application_id)
        
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        return {
            "success": True,
            "application": application
        }
        
    except Exception as e:
        logger.error(f"Error getting application: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/processing-status/{application_id}")
async def get_processing_status(application_id: str):
    """
    Get processing status for an application
    
    Args:
        application_id: Application identifier
    
    Returns:
        Processing status
    """
    try:
        status = await orchestrator.get_processing_status(application_id)
        
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        
        return ProcessingStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Error getting processing status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/golden-data/{application_id}")
async def get_golden_data(application_id: str):
    """
    Get golden data summary for an application
    
    Args:
        application_id: Application identifier
    
    Returns:
        Golden data summary
    """
    try:
        golden_data = await orchestrator.get_golden_data_summary(application_id)
        
        if "error" in golden_data:
            raise HTTPException(status_code=404, detail=golden_data["error"])
        
        return GoldenDataResponse(**golden_data)
        
    except Exception as e:
        logger.error(f"Error getting golden data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/field-status/{application_id}")
async def get_field_status(application_id: str):
    """
    Get detailed field extraction and validation status
    
    Args:
        application_id: Application identifier
    
    Returns:
        Field status including extracted, missing, and pending fields
    """
    try:
        field_status = await orchestrator.get_field_status(application_id)
        
        if "error" in field_status:
            raise HTTPException(status_code=404, detail=field_status["error"])
        
        return field_status
        
    except Exception as e:
        logger.error(f"Error getting field status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/extracted-fields/{application_id}")
async def get_extracted_fields(application_id: str):
    """
    Get all extracted fields for an application
    
    Args:
        application_id: Application identifier
    
    Returns:
        List of all extracted fields with their details
    """
    try:
        # Get extracted data from database
        extracted_data = await orchestrator.db_service.get_extracted_data_by_application(application_id)
        
        if not extracted_data:
            return {
                "application_id": application_id,
                "extracted_fields": [],
                "total_fields": 0,
                "message": "No extracted fields found for this application"
            }
        
        # Combine all extracted fields from all documents
        all_extracted_fields = {}
        total_fields = 0
        
        for data in extracted_data:
            if 'extracted_fields' in data and data['extracted_fields']:
                import json
                if isinstance(data['extracted_fields'], str):
                    fields = json.loads(data['extracted_fields'])
                else:
                    fields = data['extracted_fields']
                
                for field in fields:
                    field_name = field['field_name']
                    all_extracted_fields[field_name] = {
                        **field,
                        'document_type': data.get('document_type'),
                        'document_id': data.get('document_id'),
                        'extracted_at': data.get('extracted_at')
                    }
                    total_fields += 1
        
        return {
            "application_id": application_id,
            "extracted_fields": all_extracted_fields,
            "total_fields": total_fields,
            "document_count": len(extracted_data),
            "message": f"Found {total_fields} extracted fields from {len(extracted_data)} documents"
        }
        
    except Exception as e:
        logger.error(f"Error getting extracted fields: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/required-documents/{application_id}")
async def get_required_documents(application_id: str):
    """
    Get list of required documents and their status
    
    Args:
        application_id: Application identifier
    
    Returns:
        Required documents with upload status and missing fields
    """
    try:
        required_docs = await orchestrator.get_required_documents(application_id)
        
        if "error" in required_docs:
            raise HTTPException(status_code=404, detail=required_docs["error"])
        
        return required_docs
        
    except Exception as e:
        logger.error(f"Error getting required documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/missing-fields/{application_id}")
async def get_missing_fields(application_id: str):
    """
    Get list of missing fields and which documents can provide them
    
    Args:
        application_id: Application identifier
    
    Returns:
        Missing fields with suggested document types
    """
    try:
        missing_fields = await orchestrator.get_missing_fields(application_id)
        
        if "error" in missing_fields:
            raise HTTPException(status_code=404, detail=missing_fields["error"])
        
        return missing_fields
        
    except Exception as e:
        logger.error(f"Error getting missing fields: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/debug/jobs/{application_id}")
async def debug_jobs(application_id: str):
    """Debug endpoint to check job status"""
    try:
        jobs = await orchestrator.db_service.get_document_jobs(application_id)
        pending_jobs = await orchestrator.db_service.get_pending_jobs()
        return {
            "application_jobs": jobs,
            "all_pending_jobs": pending_jobs,
            "job_processor_running": orchestrator.job_queue_service.is_running
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/v1/debug/trigger-extraction/{application_id}")
async def trigger_extraction(application_id: str):
    """Debug endpoint to manually trigger extraction for existing documents"""
    try:
        documents = await orchestrator.db_service.get_documents_by_application(application_id)
        results = []
        
        for document in documents:
            if document["processing_status"] == "pending":
                # Create extraction job
                await orchestrator.job_queue_service.add_extraction_job(
                    application_id, 
                    document["id"], 
                    priority=5
                )
                results.append({
                    "document_id": document["id"],
                    "filename": document["filename"],
                    "status": "job_created"
                })
        
        return {
            "success": True,
            "message": f"Created extraction jobs for {len(results)} documents",
            "results": results
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/v1/debug/documents/{application_id}")
async def debug_documents(application_id: str):
    """Debug endpoint to check documents in database"""
    try:
        documents = await orchestrator.db_service.get_documents_by_application(application_id)
        return {
            "success": True,
            "application_id": application_id,
            "document_count": len(documents),
            "documents": documents
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/v1/debug/document/{document_id}")
async def debug_document(document_id: str):
    """Debug endpoint to check a specific document"""
    try:
        document = await orchestrator.db_service.get_document(document_id)
        return {
            "success": True,
            "document_id": document_id,
            "document": document
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/v1/retry-processing/{application_id}")
async def retry_processing(application_id: str):
    """
    Retry processing for an application
    
    Args:
        application_id: Application identifier
    
    Returns:
        Retry result
    """
    try:
        result = await orchestrator.retry_processing(application_id)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Processing retry initiated",
                "data": result
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        logger.error(f"Error retrying processing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/metrics")
async def get_processing_metrics():
    """
    Get system-wide processing metrics
    
    Returns:
        Processing metrics
    """
    try:
        metrics = await orchestrator.get_processing_metrics()
        
        if "error" in metrics:
            raise HTTPException(status_code=500, detail=metrics["error"])
        
        return ProcessingMetricsResponse(**metrics)
        
    except Exception as e:
        logger.error(f"Error getting processing metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
            "Data Validation Agent",
            "Data Formatting Agent"
        ]
    }

# Startup and shutdown events are already defined above

# Main entry point
if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
