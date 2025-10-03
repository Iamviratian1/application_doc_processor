"""
Document Ingestion Agent
Handles document upload, validation, and initial processing setup
"""

import os
import uuid
import mimetypes
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio
from pathlib import Path

from models.document import Document
from models.application import Application
from models.processing_log import ProcessingLog
from models.document_job import DocumentJob
from services.database_service import DatabaseService
from services.storage_service import StorageService
from services.textract_service import TextractService
from config.document_config import DocumentConfig
from utils.logger import get_logger

logger = get_logger(__name__)

class DocumentIngestionAgent:
    """
    Agent responsible for:
    1. Document upload validation
    2. File type detection
    3. Storage management
    4. Initial document classification
    5. Job queue creation
    """
    
    def __init__(self):
        self.db_service = DatabaseService()
        self.storage_service = StorageService()
        self.textract_service = TextractService()
        self.document_config = DocumentConfig()
        self.supported_formats = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif']
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        
    async def process_document_upload(
        self, 
        file_content: bytes, 
        filename: str, 
        application_id: str,
        applicant_type: str = "applicant"
    ) -> Dict[str, Any]:
        """
        Process a single document upload
        
        Args:
            file_content: Raw file content
            filename: Original filename
            application_id: Application identifier
            applicant_type: 'applicant' or 'co_applicant'
            
        Returns:
            Dict with processing results
        """
        start_time = datetime.now()
        
        try:
            # Log start
            await self._log_processing_step(
                application_id, 
                "document_upload", 
                "started", 
                f"Processing upload: {filename}"
            )
            
            # Step 1: Validate file
            validation_result = await self._validate_file(file_content, filename)
            if not validation_result["valid"]:
                await self._log_processing_step(
                    application_id, 
                    "document_upload", 
                    "failed", 
                    f"File validation failed: {validation_result['error']}"
                )
                return {
                    "success": False,
                    "error": validation_result["error"],
                    "document_id": None
                }
            
            # Step 2: Generate document ID and storage path
            document_id = str(uuid.uuid4())
            storage_path = f"applications/{application_id}/documents/{document_id}_{filename}"
            
            # Step 3: Store file locally
            upload_result = await self.storage_service.store_file_locally(
                file_content, 
                storage_path, 
                {"filename": filename, "application_id": application_id}
            )
            
            if not upload_result["success"]:
                await self._log_processing_step(
                    application_id, 
                    "document_upload", 
                    "failed", 
                    f"Storage upload failed: {upload_result['error']}"
                )
                return {
                    "success": False,
                    "error": f"Storage upload failed: {upload_result['error']}",
                    "document_id": None
                }
            
            # Step 4: Detect document type
            document_type = await self._detect_document_type(file_content, filename)
            
            # Step 5: Create document record
            document_data = {
                "application_id": application_id,
                "document_id": document_id,
                "filename": filename,
                "document_type": document_type,
                "applicant_type": applicant_type,
                "file_size": len(file_content),
                "mime_type": mimetypes.guess_type(filename)[0],
                "storage_path": storage_path,
                "upload_status": "uploaded",
                "processing_status": "pending",
                "meta_data": {
                    "upload_timestamp": datetime.now().isoformat(),
                    "file_extension": Path(filename).suffix.lower(),
                    "detected_type": document_type
                }
            }
            
            logger.info(f"About to create document with data: {document_data}")
            document_record_id = await self.db_service.create_document(document_data)
            logger.info(f"Document created successfully with ID: {document_record_id}")
            
            # Step 6: Create extraction job
            job_data = {
                "application_id": application_id,
                "document_id": document_record_id,
                "job_type": "extraction",
                "status": "pending",
                "priority": self._get_job_priority(document_type)
            }
            
            await self.db_service.create_document_job(job_data)
            
            # Step 7: Update application status
            await self.db_service.update_application_status(
                application_id, 
                "processing"
            )
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            await self._log_processing_step(
                application_id, 
                "document_upload", 
                "completed", 
                f"Document uploaded successfully: {filename}",
                processing_time_ms=int(processing_time)
            )
            
            return {
                "success": True,
                "document_id": document_record_id,
                "document_type": document_type,
                "storage_path": storage_path,
                "processing_time_ms": int(processing_time)
            }
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = f"Document ingestion failed: {str(e)}"
            
            await self._log_processing_step(
                application_id, 
                "document_upload", 
                "failed", 
                error_msg,
                processing_time_ms=int(processing_time),
                error_details={"exception": str(e)}
            )
            
            logger.error(f"Document ingestion error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "document_id": None
            }
    
    async def process_multiple_documents(
        self, 
        files: List[Tuple[bytes, str]], 
        application_id: str,
        applicant_type: str = "applicant"
    ) -> Dict[str, Any]:
        """
        Process multiple document uploads
        
        Args:
            files: List of (file_content, filename) tuples
            application_id: Application identifier
            applicant_type: 'applicant' or 'co_applicant'
            
        Returns:
            Dict with batch processing results
        """
        start_time = datetime.now()
        
        try:
            await self._log_processing_step(
                application_id, 
                "batch_upload", 
                "started", 
                f"Processing {len(files)} documents"
            )
            
            results = []
            successful_uploads = 0
            failed_uploads = 0
            
            # Process files concurrently (with limit)
            semaphore = asyncio.Semaphore(5)  # Max 5 concurrent uploads
            
            async def process_single_file(file_data):
                async with semaphore:
                    file_content, filename = file_data
                    logger.info(f"Processing single file: {filename}")
                    result = await self.process_document_upload(
                        file_content, filename, application_id, applicant_type
                    )
                    logger.info(f"File {filename} processing result: {result}")
                    return result
            
            tasks = [process_single_file(file_data) for file_data in files]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, Exception):
                    failed_uploads += 1
                    logger.error(f"Upload task failed: {str(result)}")
                elif result.get("success"):
                    successful_uploads += 1
                else:
                    failed_uploads += 1
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            await self._log_processing_step(
                application_id, 
                "batch_upload", 
                "completed", 
                f"Batch upload completed: {successful_uploads} successful, {failed_uploads} failed",
                processing_time_ms=int(processing_time)
            )
            
            return {
                "success": True,
                "total_files": len(files),
                "successful_uploads": successful_uploads,
                "failed_uploads": failed_uploads,
                "results": results,
                "processing_time_ms": int(processing_time)
            }
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = f"Batch document ingestion failed: {str(e)}"
            
            await self._log_processing_step(
                application_id, 
                "batch_upload", 
                "failed", 
                error_msg,
                processing_time_ms=int(processing_time),
                error_details={"exception": str(e)}
            )
            
            logger.error(f"Batch ingestion error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "total_files": len(files),
                "successful_uploads": 0,
                "failed_uploads": len(files)
            }
    
    async def _validate_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Validate uploaded file"""
        try:
            # Check file size
            if len(file_content) > self.max_file_size:
                return {
                    "valid": False,
                    "error": f"File size {len(file_content)} exceeds maximum {self.max_file_size} bytes"
                }
            
            # Check file extension
            file_ext = Path(filename).suffix.lower()
            if file_ext not in self.supported_formats:
                return {
                    "valid": False,
                    "error": f"Unsupported file format: {file_ext}. Supported: {', '.join(self.supported_formats)}"
                }
            
            # Check if file is empty
            if len(file_content) == 0:
                return {
                    "valid": False,
                    "error": "File is empty"
                }
            
            # Basic file header validation
            if file_ext == '.pdf' and not file_content.startswith(b'%PDF'):
                return {
                    "valid": False,
                    "error": "Invalid PDF file format"
                }
            
            return {"valid": True, "error": None}
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"File validation error: {str(e)}"
            }
    
    async def _detect_document_type(self, file_content: bytes, filename: str) -> str:
        """Detect document type using AWS Textract"""
        try:
            logger.info(f"Starting document type detection for: {filename}")
            
            # Use Textract to analyze the document and ask "What is this document?"
            textract_result = await self.textract_service.analyze_document_for_classification(
                file_content, filename
            )
            
            logger.info(f"Textract result for {filename}: {textract_result}")
            
            if textract_result["success"]:
                detected_type = textract_result.get("document_type", "generic_document")
                textract_answer = textract_result.get("textract_answer", "No answer")
                logger.info(f"Textract detected document type: {detected_type} (answer: '{textract_answer}') for file: {filename}")
                return detected_type
            else:
                logger.warning(f"Textract classification failed for {filename}: {textract_result.get('error', 'Unknown error')}")
                return 'generic_document'
            
        except Exception as e:
            logger.error(f"Document type detection failed for {filename}: {str(e)}")
            return 'generic_document'
    
    def _get_job_priority(self, document_type: str) -> int:
        """Get job priority based on document type"""
        priority_map = {
            'mortgage_application': 1,  # Highest priority
            't4_form': 2,
            'employment_letter': 2,
            'bank_statement': 3,
            'pay_stub': 3,
            'drivers_license': 3,
            'passport': 3,
            'credit_report': 4,
            'property_assessment': 4,
            'marriage_certificate': 4,
            'birth_certificate': 4,
            'utility_bill': 4,
            'rental_agreement': 4,
            'immigration_document': 4,
            'insurance_document': 5,
            'insurance_policy': 5,
            'tax_return': 5,
            'social_security': 5,
            'property_deed': 5,
            'financial_statement': 5,
            'investment_statement': 5,
            'generic_document': 6  # Lowest priority
        }
        return priority_map.get(document_type, 5)
    
    async def _log_processing_step(
        self, 
        application_id: str, 
        step_name: str, 
        status: str, 
        message: str,
        document_id: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
        error_details: Optional[Dict] = None
    ):
        """Log processing step"""
        try:
            log_data = {
                "application_id": application_id,
                "document_id": document_id,
                "agent_name": "ingestion",
                "step_name": step_name,
                "status": status,
                "message": message,
                "processing_time_ms": processing_time_ms,
                "error_details": error_details
            }
            await self.db_service.create_processing_log(log_data)
        except Exception as e:
            logger.error(f"Failed to log processing step: {str(e)}")
    
    async def get_upload_status(self, application_id: str) -> Dict[str, Any]:
        """Get upload status for an application"""
        try:
            documents = await self.db_service.get_documents_by_application(application_id)
            
            total_documents = len(documents)
            uploaded_documents = len([d for d in documents if d["upload_status"] == "uploaded"])
            pending_documents = len([d for d in documents if d["processing_status"] == "pending"])
            processing_documents = len([d for d in documents if d["processing_status"] == "processing"])
            completed_documents = len([d for d in documents if d["processing_status"] == "completed"])
            failed_documents = len([d for d in documents if d["processing_status"] == "failed"])
            
            return {
                "application_id": application_id,
                "total_documents": total_documents,
                "uploaded_documents": uploaded_documents,
                "pending_documents": pending_documents,
                "processing_documents": processing_documents,
                "completed_documents": completed_documents,
                "failed_documents": failed_documents,
                "upload_completion_percentage": (uploaded_documents / total_documents * 100) if total_documents > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get upload status: {str(e)}")
            return {
                "application_id": application_id,
                "error": str(e)
            }
