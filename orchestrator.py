"""
Document Processing Orchestrator
Main orchestrator that coordinates all four agents in the document processing pipeline
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from agents.document_ingestion_agent import DocumentIngestionAgent
from agents.data_extraction_agent import DataExtractionAgent
from agents.data_validation_agent import DataValidationAgent
from services.database_service import DatabaseService
from services.job_queue_service import JobQueueService
from utils.logger import get_logger

logger = get_logger(__name__)

class DocumentProcessingOrchestrator:
    """
    Main orchestrator that coordinates the four-agent document processing pipeline:
    1. Document Ingestion Agent - Handles document upload and validation
    2. Data Extraction Agent - Extracts data using AWS Textract
    3. Data Validation Agent - Validates extracted data against application form
    """
    
    def __init__(self):
        try:
            logger.info("=== ORCHESTRATOR DEBUG: Initializing orchestrator ===")
            print("=== ORCHESTRATOR DEBUG: Initializing orchestrator ===")
            
            logger.info("=== ORCHESTRATOR DEBUG: Initializing database service ===")
            print("=== ORCHESTRATOR DEBUG: Initializing database service ===")
            self.db_service = DatabaseService()
            
            logger.info("=== ORCHESTRATOR DEBUG: Initializing ingestion agent ===")
            print("=== ORCHESTRATOR DEBUG: Initializing ingestion agent ===")
            self.ingestion_agent = DocumentIngestionAgent()
            
            logger.info("=== ORCHESTRATOR DEBUG: Initializing extraction agent ===")
            print("=== ORCHESTRATOR DEBUG: Initializing extraction agent ===")
            self.extraction_agent = DataExtractionAgent()
            
            logger.info("=== ORCHESTRATOR DEBUG: Initializing validation agent ===")
            print("=== ORCHESTRATOR DEBUG: Initializing validation agent ===")
            self.validation_agent = DataValidationAgent()
            
            
            logger.info("=== ORCHESTRATOR DEBUG: Initializing job queue service ===")
            print("=== ORCHESTRATOR DEBUG: Initializing job queue service ===")
            self.job_queue_service = JobQueueService(
                ingestion_agent=self.ingestion_agent,
                extraction_agent=self.extraction_agent,
                validation_agent=self.validation_agent
            )
            
            logger.info("=== ORCHESTRATOR DEBUG: Orchestrator initialized successfully ===")
            print("=== ORCHESTRATOR DEBUG: Orchestrator initialized successfully ===")
            
        except Exception as e:
            logger.error(f"=== ORCHESTRATOR ERROR: Failed to initialize orchestrator: {str(e)} ===")
            print(f"=== ORCHESTRATOR ERROR: Failed to initialize orchestrator: {str(e)} ===")
            import traceback
            logger.error(f"=== ORCHESTRATOR TRACEBACK: {traceback.format_exc()} ===")
            print(f"=== ORCHESTRATOR TRACEBACK: {traceback.format_exc()} ===")
            raise
    
    async def create_application(self, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new application
        
        Args:
            application_data: Application data including application_id, applicant_name, etc.
            
        Returns:
            Dict with creation result
        """
        try:
            logger.info(f"Creating application: {application_data['application_id']}")
            
            # Create application record in database
            app_id = await self.db_service.create_application(application_data)
            
            # Log the creation
            await self.ingestion_agent._log_processing_step(
                application_data['application_id'],
                "application_creation",
                "completed",
                f"Application created for {application_data['applicant_name']}"
            )
            
            return {
                "success": True,
                "application_id": application_data['application_id'],
                "database_id": app_id,
                "message": "Application created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating application: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "application_id": application_data.get('application_id')
            }
    
    async def get_application(self, application_id: str) -> Optional[Dict[str, Any]]:
        """
        Get application information
        
        Args:
            application_id: Application identifier
            
        Returns:
            Application data or None if not found
        """
        try:
            return await self.db_service.get_application(application_id)
        except Exception as e:
            logger.error(f"Error getting application: {str(e)}")
            return None
        
    async def process_application_documents(
        self, 
        files: List[Tuple[bytes, str]], 
        application_id: str,
        applicant_type: str = "applicant"
    ) -> Dict[str, Any]:
        """
        Process multiple documents for an application through the complete pipeline
        
        Args:
            files: List of (file_content, filename) tuples
            application_id: Application identifier
            applicant_type: 'applicant' or 'co_applicant'
            
        Returns:
            Dict with complete processing results
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting document processing for application {application_id}")
            
            # Step 0: Create application if it doesn't exist
            existing_app = await self.db_service.get_application(application_id)
            if not existing_app:
                logger.info(f"Creating new application: {application_id}")
                app_data = {
                    "application_id": application_id,
                    "applicant_name": "Unknown",  # Will be updated when we extract data
                    "application_type": "mortgage",
                    "status": "document_upload",
                    "meta_data": {"created_via": "document_upload"}
                }
                await self.db_service.create_application(app_data)
                logger.info(f"Application {application_id} created successfully")
            
            # Step 1: Document Ingestion
            logger.info(f"Calling ingestion agent with {len(files)} files for application {application_id}")
            ingestion_result = await self.ingestion_agent.process_multiple_documents(
                files, application_id, applicant_type
            )
            logger.info(f"Ingestion result: {ingestion_result}")
            
            if not ingestion_result["success"]:
                return {
                    "success": False,
                    "error": f"Ingestion failed: {ingestion_result['error']}",
                    "stage": "ingestion"
                }
            
            # Step 2: Start background processing
            await self._start_background_processing(application_id)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "success": True,
                "application_id": application_id,
                "ingestion_result": ingestion_result,
                "processing_time_ms": int(processing_time),
                "message": "Documents uploaded successfully. Processing started in background."
            }
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = f"Document processing failed: {str(e)}"
            
            logger.error(f"Orchestrator error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "application_id": application_id,
                "processing_time_ms": int(processing_time)
            }
    
    async def _start_background_processing(self, application_id: str):
        """Start background processing for an application"""
        try:
            # Get documents for the application
            documents = await self.db_service.get_documents_by_application(application_id)
            
            # Create extraction jobs for each document
            for document in documents:
                if document["processing_status"] == "pending":
                    await self.job_queue_service.add_extraction_job(
                        application_id, 
                        document["id"], 
                        priority=self._get_document_priority(document["document_type"])
                    )
            
            logger.info(f"Started background processing for application {application_id}")
            
        except Exception as e:
            logger.error(f"Error starting background processing: {str(e)}")
    
    def _get_document_priority(self, document_type: str) -> int:
        """Get priority for document processing"""
        priority_map = {
            'mortgage_application': 1,  # Highest priority
            't4_form': 2,
            'employment_letter': 2,
            'bank_statement': 3,
            'pay_stub': 3,
            'credit_report': 4,
            'property_assessment': 4,
            'insurance_document': 5,
            'generic_document': 6  # Lowest priority
        }
        return priority_map.get(document_type, 5)
    
    async def get_processing_status(self, application_id: str) -> Dict[str, Any]:
        """Get comprehensive processing status for an application"""
        try:
            # Get application status
            application = await self.db_service.get_application(application_id)
            if not application:
                return {"error": "Application not found"}
            
            # Get status from each agent
            ingestion_status = await self.ingestion_agent.get_upload_status(application_id)
            extraction_status = await self.extraction_agent.get_extraction_status(application_id)
            validation_status = await self.validation_agent.get_validation_status(application_id)
            
            # Get job status
            job_status = await self.job_queue_service.get_job_status(application_id)
            
            # Calculate overall progress
            overall_progress = self._calculate_overall_progress(
                ingestion_status, extraction_status, validation_status
            )
            
            return {
                "application_id": application_id,
                "application_status": application["status"],
                "overall_progress": overall_progress,
                "agent_statuses": {
                    "ingestion": ingestion_status,
                    "extraction": extraction_status,
                "validation": validation_status
                },
                "job_status": job_status,
                "ready_for_decision_engine": overall_progress["completion_percentage"] >= 80
            }
            
        except Exception as e:
            logger.error(f"Error getting processing status: {str(e)}")
            return {
                "application_id": application_id,
                "error": str(e)
            }
    
    def _calculate_overall_progress(
        self, 
        ingestion_status: Dict[str, Any], 
        extraction_status: Dict[str, Any], 
        validation_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate overall processing progress"""
        try:
            # Get completion percentages from each stage
            ingestion_pct = ingestion_status.get("upload_completion_percentage", 0)
            extraction_pct = extraction_status.get("extraction_completion_percentage", 0)
            validation_pct = validation_status.get("validation_completion_percentage", 0)
            
            # Calculate weighted overall progress
            # Ingestion: 25%, Extraction: 35%, Validation: 40%
            overall_pct = (
                ingestion_pct * 0.25 + 
                extraction_pct * 0.35 + 
                validation_pct * 0.40
            )
            
            # Determine current stage
            current_stage = "ingestion"
            if ingestion_pct >= 100:
                current_stage = "extraction"
            if extraction_pct >= 100:
                current_stage = "validation"
            if validation_pct >= 100:
                current_stage = "completed"
            
            return {
                "completion_percentage": overall_pct,
                "current_stage": current_stage,
                "stage_progress": {
                    "ingestion": ingestion_pct,
                    "extraction": extraction_pct,
                    "validation": validation_pct
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating overall progress: {str(e)}")
            return {
                "completion_percentage": 0,
                "current_stage": "error",
                "stage_progress": {
                    "ingestion": 0,
                    "extraction": 0,
                    "validation": 0
                }
            }
    
    
    async def get_field_status(self, application_id: str) -> Dict[str, Any]:
        """Get detailed field extraction and validation status"""
        print(f"DEBUG: get_field_status called for application_id: {application_id}")
        try:
            print(f"DEBUG: Starting get_field_status for {application_id}")
            # Get all extracted data for the application
            print(f"DEBUG: Getting extracted data for {application_id}")
            extracted_data = await self.db_service.get_extracted_data_by_application(application_id)
            print(f"DEBUG: Extracted data count: {len(extracted_data) if extracted_data else 0}")
            
            # Skip golden data for now - focus on extracted fields
            print(f"DEBUG: Skipping golden data for now")
            golden_data = None
            
            # Get validation results
            validation_query = """
            SELECT * FROM validation_results 
            WHERE application_id = :application_id 
            ORDER BY validated_at DESC LIMIT 1
            """
            validation_results = await self.db_service.execute_query(validation_query, {"application_id": application_id})
            
            # Aggregate all extracted fields
            all_extracted_fields = {}
            field_sources = {}
            
            for data in extracted_data:
                if data.get('extracted_fields'):
                    # Parse extracted_fields JSON string
                    import json
                    if isinstance(data['extracted_fields'], str):
                        fields_list = json.loads(data['extracted_fields'])
                    else:
                        fields_list = data['extracted_fields']
                    
                    # extracted_fields is stored as a list of field objects
                    for field_data in fields_list:
                        field_name = field_data.get('field_name')
                        if field_name:
                            all_extracted_fields[field_name] = field_data
                            field_sources[field_name] = {
                                'document_type': data['document_type'],
                                'document_id': data['document_id'],
                                'confidence': field_data.get('confidence', 0),
                                'extraction_method': data['extraction_method']
                            }
            
            # Skip golden fields for now
            golden_fields = {}
            
            # Skip validation summary for now - focus on extracted fields
            validation_summary = {}
            
            # Calculate field statistics
            total_extracted = len(all_extracted_fields)
            total_golden = 0  # Skip golden fields for now
            
            # Skip validation for now - focus on extracted fields
            total_validated = 0
            
            return {
                "application_id": application_id,
                "field_statistics": {
                    "total_extracted_fields": total_extracted,
                    "total_golden_fields": 0,  # Skip for now
                    "total_validated_fields": 0,  # Skip for now
                    "extraction_completion_percentage": (total_extracted / 50) * 100 if total_extracted > 0 else 0,  # Assuming ~50 total fields
                    "validation_completion_percentage": 0  # Skip for now
                },
                "extracted_fields": all_extracted_fields,
                "golden_fields": {},  # Skip for now
                "field_sources": field_sources,
                "validation_summary": {},  # Skip for now
                "is_complete": total_extracted >= 30  # Simplified threshold
            }
            
        except Exception as e:
            logger.error(f"Error getting field status: {str(e)}")
            return {
                "application_id": application_id,
                "error": str(e)
            }
    
    async def get_required_documents(self, application_id: str) -> Dict[str, Any]:
        """Get list of required documents and their status"""
        try:
            # Get uploaded documents
            uploaded_docs = await self.db_service.get_documents_by_application(application_id)
            uploaded_types = {doc['document_type'] for doc in uploaded_docs}
            
            # Get required document types from config
            from config.document_config import DocumentConfig
            doc_config = DocumentConfig()
            
            required_docs = []
            document_types = doc_config.yaml_loader.get_document_types()
            for doc_type, config in document_types.items():
                if config.get('mandatory_for_applicant', False):
                    status = "uploaded" if doc_type in uploaded_types else "missing"
                    
                    # Get fields that this document type can provide
                    queries = config.get('field_extraction', {}).get('queries', [])
                    available_fields = [query.get('alias') for query in queries if query.get('alias')]
                    
                    required_docs.append({
                        "document_type": doc_type,
                        "display_name": config.get('display_name', doc_type),
                        "status": status,
                        "uploaded_at": next((doc['uploaded_at'] for doc in uploaded_docs if doc['document_type'] == doc_type), None),
                        "available_fields": available_fields,
                        "description": config.get('description', ''),
                        "file_types": config.get('accepted_file_types', ['.pdf', '.jpg', '.png'])
                    })
            
            return {
                "application_id": application_id,
                "required_documents": required_docs,
                "summary": {
                    "total_required": len(required_docs),
                    "uploaded": len([doc for doc in required_docs if doc['status'] == 'uploaded']),
                    "missing": len([doc for doc in required_docs if doc['status'] == 'missing'])
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting required documents: {str(e)}")
            return {
                "application_id": application_id,
                "error": str(e)
            }
    
    async def get_missing_fields(self, application_id: str) -> Dict[str, Any]:
        """Get list of missing fields and which documents can provide them"""
        try:
            # Get current field status
            field_status = await self.get_field_status(application_id)
            if "error" in field_status:
                return field_status
            
            # Get all possible fields from config
            from config.document_config import DocumentConfig
            doc_config = DocumentConfig()
            
            all_possible_fields = set()
            field_to_documents = {}
            document_types = doc_config.yaml_loader.get_document_types()
            
            for doc_type, config in document_types.items():
                queries = config.get('field_extraction', {}).get('queries', [])
                for query in queries:
                    field_name = query.get('alias')
                    if field_name:
                        all_possible_fields.add(field_name)
                        if field_name not in field_to_documents:
                            field_to_documents[field_name] = []
                        field_to_documents[field_name].append({
                            'document_type': doc_type,
                            'display_name': config.get('display_name', doc_type),
                            'priority': 'high' if config.get('mandatory_for_applicant', False) else 'medium'
                        })
            
            # Find missing fields
            extracted_fields = field_status.get('extracted_fields', {})
            missing_fields = []
            
            for field_name in all_possible_fields:
                if field_name not in extracted_fields:
                    # Get documents that can provide this field
                    available_documents = field_to_documents.get(field_name, [])
                    
                    missing_fields.append({
                        "field_name": field_name,
                        "field_display_name": field_name.replace('_', ' ').title(),
                        "field_type": "text",  # Could be enhanced to get from config
                        "available_documents": available_documents,
                        "priority": "high" if any(doc['priority'] == 'high' for doc in available_documents) else "medium",
                        "is_critical": any(doc['priority'] == 'high' for doc in available_documents)
                    })
            
            # Sort by priority
            missing_fields.sort(key=lambda x: (x['priority'] == 'high', x['is_critical']), reverse=True)
            
            return {
                "application_id": application_id,
                "missing_fields": missing_fields,
                "summary": {
                    "total_missing_fields": len(missing_fields),
                    "critical_missing_fields": len([f for f in missing_fields if f['is_critical']]),
                    "completion_percentage": ((len(all_possible_fields) - len(missing_fields)) / len(all_possible_fields)) * 100
                },
                "recommended_documents": self._get_recommended_documents(missing_fields)
            }
            
        except Exception as e:
            logger.error(f"Error getting missing fields: {str(e)}")
            return {
                "application_id": application_id,
                "error": str(e)
            }
    
    def _get_recommended_documents(self, missing_fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get recommended documents based on missing fields"""
        doc_priority = {}
        
        for field in missing_fields:
            for doc in field['available_documents']:
                doc_type = doc['document_type']
                if doc_type not in doc_priority:
                    doc_priority[doc_type] = {
                        'document_type': doc_type,
                        'display_name': doc['display_name'],
                        'missing_fields_count': 0,
                        'priority': doc['priority'],
                        'missing_fields': []
                    }
                
                doc_priority[doc_type]['missing_fields_count'] += 1
                doc_priority[doc_type]['missing_fields'].append(field['field_name'])
        
        # Sort by priority and field count
        recommended = list(doc_priority.values())
        recommended.sort(key=lambda x: (x['priority'] == 'high', x['missing_fields_count']), reverse=True)
        
        return recommended[:5]  # Top 5 recommendations
    
    async def retry_processing(self, application_id: str) -> Dict[str, Any]:
        """Retry processing for an application"""
        try:
            # Retry failed jobs
            retry_result = await self.job_queue_service.retry_failed_jobs(application_id)
            
            # Update application status
            await self.db_service.update_application_status(
                application_id, 
                "processing", 
                "Retrying failed processing steps"
            )
            
            return {
                "success": True,
                "application_id": application_id,
                "retry_result": retry_result,
                "message": "Processing retry initiated"
            }
            
        except Exception as e:
            logger.error(f"Error retrying processing: {str(e)}")
            return {
                "success": False,
                "application_id": application_id,
                "error": str(e)
            }
    
    async def start_job_processor(self):
        """Start the background job processor"""
        try:
            await self.job_queue_service.start_job_processor()
        except Exception as e:
            logger.error(f"Error starting job processor: {str(e)}")
    
    async def stop_job_processor(self):
        """Stop the background job processor"""
        try:
            await self.job_queue_service.stop_job_processor()
        except Exception as e:
            logger.error(f"Error stopping job processor: {str(e)}")
    
    async def get_processing_metrics(self) -> Dict[str, Any]:
        """Get system-wide processing metrics"""
        try:
            # Get all applications
            applications = await self.db_service.get_all_applications()
            
            # Calculate metrics
            total_applications = len(applications)
            completed_applications = len([app for app in applications if app["status"] == "completed"])
            processing_applications = len([app for app in applications if app["status"] == "processing"])
            failed_applications = len([app for app in applications if app["status"] == "failed"])
            
            # Get job metrics
            pending_jobs = await self.db_service.get_pending_jobs()
            processing_jobs = len([job for job in pending_jobs if job["status"] == "processing"])
            failed_jobs = len([job for job in pending_jobs if job["status"] == "failed"])
            
            return {
                "total_applications": total_applications,
                "completed_applications": completed_applications,
                "processing_applications": processing_applications,
                "failed_applications": failed_applications,
                "completion_rate": (completed_applications / total_applications * 100) if total_applications > 0 else 0,
                "pending_jobs": len(pending_jobs),
                "processing_jobs": processing_jobs,
                "failed_jobs": failed_jobs
            }
            
        except Exception as e:
            logger.error(f"Error getting processing metrics: {str(e)}")
            return {"error": str(e)}
