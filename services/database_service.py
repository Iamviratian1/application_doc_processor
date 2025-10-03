"""
Database Service
Handles database operations using SQLAlchemy with PostgreSQL
"""

import os
import asyncio
import json
from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from utils.logger import get_logger

logger = get_logger(__name__)

class DatabaseService:
    """Service for database operations"""
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise Exception("DATABASE_URL environment variable not set")
        
        # Convert to async URL if needed
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://")
        
        self.engine = create_async_engine(self.database_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
    
    async def get_session(self):
        """Get database session"""
        async with self.async_session() as session:
            yield session
    
    async def execute_query(self, query: str, params: Dict = None) -> List[Dict]:
        """Execute a raw SQL query"""
        try:
            async with self.async_session() as session:
                result = await session.execute(text(query), params or {})
                rows = result.fetchall()
                return [dict(row._mapping) for row in rows]
        except Exception as e:
            logger.error(f"Database query error: {str(e)}")
            raise
    
    async def execute_insert(self, query: str, params: Dict = None) -> Any:
        """Execute an insert query and return the result"""
        try:
            async with self.async_session() as session:
                result = await session.execute(text(query), params or {})
                await session.commit()
                # For PostgreSQL with RETURNING clause, get the first row
                if result.returns_rows:
                    return result.fetchone()[0]
                return result.rowcount
        except Exception as e:
            logger.error(f"Database insert error: {str(e)}")
            raise
    
    async def execute_update(self, query: str, params: Dict = None) -> int:
        """Execute an update query and return affected rows"""
        try:
            async with self.async_session() as session:
                result = await session.execute(text(query), params or {})
                await session.commit()
                return result.rowcount
        except Exception as e:
            logger.error(f"Database update error: {str(e)}")
            raise
    
    # Application operations
    async def create_application(self, application_data: Dict[str, Any]) -> str:
        """Create a new application"""
        import json
        
        # Convert meta_data dict to JSON string
        params = application_data.copy()
        if 'meta_data' in params and isinstance(params['meta_data'], dict):
            params['meta_data'] = json.dumps(params['meta_data'])
        
        query = """
        INSERT INTO applications (application_id, applicant_name, application_type, status, meta_data)
        VALUES (:application_id, :applicant_name, :application_type, :status, :meta_data)
        RETURNING id
        """
        result = await self.execute_insert(query, params)
        return str(result)
    
    async def get_application(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Get application by ID"""
        query = "SELECT * FROM applications WHERE application_id = :application_id"
        results = await self.execute_query(query, {"application_id": application_id})
        return results[0] if results else None
    
    async def update_application_status(self, application_id: str, status: str, completion_percentage: float = None) -> int:
        """Update application status"""
        query = """
        UPDATE applications 
        SET status = :status
        """
        params = {"application_id": application_id, "status": status}
        
        if completion_percentage is not None:
            query += ", completion_percentage = :completion_percentage"
            params["completion_percentage"] = completion_percentage
        
        query += " WHERE application_id = :application_id"
        return await self.execute_update(query, params)
    
    # Document operations
    async def create_document(self, document_data: Dict[str, Any]) -> str:
        """Create a new document record"""
        import json
        
        logger.info(f"Creating document with data: {document_data}")
        
        # Convert metadata dict to JSON string if needed
        params = document_data.copy()
        if 'meta_data' in params and isinstance(params['meta_data'], dict):
            params['meta_data'] = json.dumps(params['meta_data'])
        elif 'metadata' in params and isinstance(params['metadata'], dict):
            params['meta_data'] = json.dumps(params['metadata'])
            del params['metadata']  # Remove the old key
        
        query = """
        INSERT INTO documents (application_id, document_id, filename, document_type, 
                             applicant_type, file_size, mime_type, storage_path, meta_data)
        VALUES (:application_id, :document_id, :filename, :document_type,
                :applicant_type, :file_size, :mime_type, :storage_path, :meta_data)
        RETURNING id
        """
        
        logger.info(f"Executing document insert query with params: {params}")
        result = await self.execute_insert(query, params)
        logger.info(f"Document created successfully with ID: {result}")
        return str(result)
    
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        logger.info(f"Looking for document with ID: {document_id}")
        query = "SELECT * FROM documents WHERE id = :document_id"
        results = await self.execute_query(query, {"document_id": str(document_id)})
        logger.info(f"Document lookup result: {len(results)} documents found")
        if results:
            logger.info(f"Found document: {results[0]}")
        else:
            logger.warning(f"No document found with ID: {document_id}")
        return results[0] if results else None
    
    async def update_document_status(self, document_id: str, status: str, message: str = None) -> int:
        """Update document processing status"""
        query = """
        UPDATE documents 
        SET processing_status = :status
        """
        params = {"document_id": str(document_id), "status": status}
        
        if message:
            query += ", meta_data = meta_data || :message"
            params["message"] = json.dumps({"status_message": message})
        
        query += " WHERE id = :document_id"
        return await self.execute_update(query, params)
    
    async def get_documents_by_application(self, application_id: str) -> List[Dict[str, Any]]:
        """Get all documents for an application"""
        query = "SELECT * FROM documents WHERE application_id = :application_id ORDER BY uploaded_at"
        return await self.execute_query(query, {"application_id": application_id})
    
    # Extracted data operations
    async def create_extracted_data(self, extracted_data: Dict[str, Any]) -> str:
        """Create extracted data record"""
        import json
        
        # Convert extracted_fields and raw_response to JSON strings
        params = extracted_data.copy()
        print(f"=== DB DEBUG: raw_response type: {type(params.get('raw_response'))}, value: {str(params.get('raw_response'))[:100]}... ===")
        if 'extracted_fields' in params and isinstance(params['extracted_fields'], (list, dict)):
            params['extracted_fields'] = json.dumps(params['extracted_fields'])
        if 'raw_response' in params and isinstance(params['raw_response'], (list, dict)):
            print(f"=== DB DEBUG: Converting raw_response to JSON ===")
            params['raw_response'] = json.dumps(params['raw_response'])
        print(f"=== DB DEBUG: After conversion, raw_response type: {type(params.get('raw_response'))} ===")
        
        query = """
        INSERT INTO extracted_data (document_id, application_id, document_type, 
                                  extracted_fields, field_count, average_confidence,
                                  extraction_method, raw_response, page_number, agent_version)
        VALUES (:document_id, :application_id, :document_type,
                :extracted_fields, :field_count, :average_confidence,
                :extraction_method, :raw_response, :page_number, :agent_version)
        RETURNING id
        """
        result = await self.execute_insert(query, params)
        return str(result)
    
    async def get_extracted_data_by_application(self, application_id: str) -> List[Dict[str, Any]]:
        """Get all extracted data for an application"""
        query = "SELECT * FROM extracted_data WHERE application_id = :application_id ORDER BY extracted_at"
        return await self.execute_query(query, {"application_id": application_id})
    
    # Validation results operations
    async def create_validation_result(self, validation_data: Dict[str, Any]) -> str:
        """Create validation result record"""
        # Convert JSONB fields to JSON strings
        params = validation_data.copy()
        if 'validation_summary' in params and isinstance(params['validation_summary'], (list, dict)):
            params['validation_summary'] = json.dumps(params['validation_summary'])
        if 'validated_fields' in params and isinstance(params['validated_fields'], (list, dict)):
            params['validated_fields'] = json.dumps(params['validated_fields'])
        if 'mismatched_fields' in params and isinstance(params['mismatched_fields'], (list, dict)):
            params['mismatched_fields'] = json.dumps(params['mismatched_fields'])
        if 'missing_fields' in params and isinstance(params['missing_fields'], (list, dict)):
            params['missing_fields'] = json.dumps(params['missing_fields'])
        if 'validation_notes' in params and isinstance(params['validation_notes'], (list, dict)):
            params['validation_notes'] = json.dumps(params['validation_notes'])
        
        query = """
        INSERT INTO validation_results (application_id, validation_summary, total_fields,
                                      validated_fields, mismatched_fields, missing_fields,
                                      critical_mismatches, high_mismatches, medium_mismatches,
                                      low_mismatches, overall_validation_score, flag_for_review,
                                      validation_notes, agent_version)
        VALUES (:application_id, :validation_summary, :total_fields,
                :validated_fields, :mismatched_fields, :missing_fields,
                :critical_mismatches, :high_mismatches, :medium_mismatches,
                :low_mismatches, :overall_validation_score, :flag_for_review,
                :validation_notes, :agent_version)
        RETURNING id
        """
        result = await self.execute_insert(query, params)
        return str(result)
    
    # Golden data operations
    async def create_golden_data(self, golden_data: Dict[str, Any]) -> str:
        """Create golden data record"""
        # Convert JSONB fields to JSON strings
        params = golden_data.copy()
        if 'golden_fields' in params and isinstance(params['golden_fields'], (list, dict)):
            params['golden_fields'] = json.dumps(params['golden_fields'])
        if 'verified_fields' in params and isinstance(params['verified_fields'], (list, dict)):
            params['verified_fields'] = json.dumps(params['verified_fields'])
        if 'high_confidence_fields' in params and isinstance(params['high_confidence_fields'], (list, dict)):
            params['high_confidence_fields'] = json.dumps(params['high_confidence_fields'])
        if 'data_sources' in params and isinstance(params['data_sources'], (list, dict)):
            params['data_sources'] = json.dumps(params['data_sources'])
        if 'validation_summary' in params and isinstance(params['validation_summary'], (list, dict)):
            params['validation_summary'] = json.dumps(params['validation_summary'])
        
        query = """
        INSERT INTO golden_data (application_id, golden_fields, field_count,
                               verified_fields, high_confidence_fields, data_quality_score,
                               ready_for_decision_engine, data_sources, validation_summary,
                               agent_version)
        VALUES (:application_id, :golden_fields, :field_count,
                :verified_fields, :high_confidence_fields, :data_quality_score,
                :ready_for_decision_engine, :data_sources, :validation_summary,
                :agent_version)
        RETURNING id
        """
        result = await self.execute_insert(query, params)
        return str(result)
    
    async def get_golden_data(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Get golden data for an application"""
        query = "SELECT * FROM golden_data WHERE application_id = :application_id ORDER BY created_at DESC LIMIT 1"
        results = await self.execute_query(query, {"application_id": application_id})
        return results[0] if results else None
    
    # Processing logs operations
    async def create_processing_log(self, log_data: Dict[str, Any]) -> str:
        """Create processing log record"""
        # Remove agent_version since the table doesn't have this column
        params = log_data.copy()
        params.pop('agent_version', None)
        
        # Convert error_details to JSON string if it's a dict
        if 'error_details' in params and isinstance(params['error_details'], dict):
            params['error_details'] = json.dumps(params['error_details'])
        
        query = """
        INSERT INTO processing_logs (application_id, document_id, agent_name, step_name,
                                   status, message, processing_time_ms, error_details)
        VALUES (:application_id, :document_id, :agent_name, :step_name,
                :status, :message, :processing_time_ms, :error_details)
        RETURNING id
        """
        result = await self.execute_insert(query, params)
        return str(result)
    
    async def get_pending_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get pending jobs"""
        query = """
        SELECT * FROM document_jobs 
        WHERE status = 'pending' 
        ORDER BY priority ASC, created_at ASC 
        LIMIT :limit
        """
        return await self.execute_query(query, {"limit": limit})
    
    async def update_job_status(self, job_id: str, status: str, result_data: Dict = None) -> int:
        """Update job status"""
        query = """
        UPDATE document_jobs 
        SET status = :status
        """
        params = {"job_id": job_id, "status": status}
        
        if result_data:
            query += ", error_message = :result_data"
            params["result_data"] = json.dumps(result_data)
        
        query += " WHERE id = :job_id"
        return await self.execute_update(query, params)
    
    # Document job operations
    async def create_document_job(self, job_data: Dict[str, Any]) -> str:
        """Create a new document job record"""
        # Remove any metadata fields since the table doesn't have a metadata column
        params = job_data.copy()
        params.pop('metadata', None)
        params.pop('meta_data', None)
        
        query = """
        INSERT INTO document_jobs (application_id, document_id, job_type, status, priority)
        VALUES (:application_id, :document_id, :job_type, :status, :priority)
        RETURNING id
        """
        result = await self.execute_insert(query, params)
        return str(result)
    
    async def get_document_jobs(self, application_id: str) -> List[Dict[str, Any]]:
        """Get all document jobs for an application"""
        query = "SELECT * FROM document_jobs WHERE application_id = :application_id ORDER BY created_at"
        return await self.execute_query(query, {"application_id": application_id})
    
    async def update_document_job_status(self, job_id: str, status: str, result_data: Dict[str, Any] = None) -> int:
        """Update document job status"""
        query = """
        UPDATE document_jobs 
        SET status = :status
        """
        params = {"job_id": job_id, "status": status}
        
        if result_data:
            query += ", error_message = :result_data"
            params["result_data"] = json.dumps(result_data)
        
        query += " WHERE id = :job_id"
        return await self.execute_update(query, params)
    
    # Validation results operations
    async def get_validation_results_by_application(self, application_id: str) -> List[Dict[str, Any]]:
        """Get validation results for an application"""
        query = """
        SELECT * FROM validation_results 
        WHERE application_id = :application_id 
        ORDER BY validated_at DESC
        """
        return await self.execute_query(query, {"application_id": application_id})
    
    # Golden data operations
    async def get_golden_data_by_application(self, application_id: str) -> List[Dict[str, Any]]:
        """Get golden data for an application"""
        query = """
        SELECT * FROM golden_data 
        WHERE application_id = :application_id 
        ORDER BY created_at DESC
        """
        return await self.execute_query(query, {"application_id": application_id})
    
    # Application form data operations
    async def get_application_form_data(self, application_id: str) -> Dict[str, Any]:
        """Get application form data for validation"""
        # Get extracted data from mortgage application form
        query = """
        SELECT ed.extracted_fields 
        FROM extracted_data ed
        JOIN documents d ON ed.document_id = d.id
        WHERE ed.application_id = :application_id 
        AND d.document_type = 'mortgage_application'
        ORDER BY ed.extracted_at DESC
        LIMIT 1
        """
        results = await self.execute_query(query, {"application_id": application_id})
        if results and results[0].get('extracted_fields'):
            # Convert the list of field objects to a dictionary
            extracted_fields = results[0]['extracted_fields']
            form_data = {}
            for field in extracted_fields:
                form_data[field['field_name']] = field['field_value']
            return form_data
        return {}
    
    
    async def close(self):
        """Close database connections"""
        await self.engine.dispose()