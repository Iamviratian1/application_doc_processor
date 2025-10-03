"""
Data Extraction Agent
Handles document analysis and field extraction using AWS Textract
"""

import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import boto3
from botocore.exceptions import ClientError
import trp.trp2 as t2

from models.extracted_data import ExtractedData
from models.document import Document
from services.database_service import DatabaseService
from services.storage_service import StorageService
from services.textract_service import TextractService
from config.document_config import DocumentConfig
from utils.logger import get_logger

logger = get_logger(__name__)

class DataExtractionAgent:
    """
    Agent responsible for:
    1. Document analysis with AWS Textract
    2. Field extraction using queries
    3. Data type detection and normalization
    4. Confidence scoring
    5. Raw response storage
    """
    
    def __init__(self):
        self.db_service = DatabaseService()
        self.storage_service = StorageService()
        self.textract_service = TextractService()
        self.document_config = DocumentConfig()
        
    async def extract_document_data(
        self, 
        document_id: str, 
        application_id: str
    ) -> Dict[str, Any]:
        """
        Extract data from a document using AWS Textract
        
        Args:
            document_id: Document identifier
            application_id: Application identifier
            
        Returns:
            Dict with extraction results
        """
        print(f"=== EXTRACT START: extract_document_data called for document {document_id}, application {application_id} ===")
        start_time = datetime.now()
        
        try:
            # Log start
            await self._log_processing_step(
                application_id, 
                document_id,
                "document_analysis", 
                "started", 
                "Starting document analysis with Textract"
            )
            
            # Step 1: Get document details
            document = await self.db_service.get_document(document_id)
            if not document:
                raise Exception(f"Document not found: {document_id}")
            
            # Step 2: Get document from local storage
            file_result = await self.storage_service.get_local_file(document["storage_path"])
            if not file_result["success"]:
                raise Exception(f"Failed to get document: {file_result['error']}")
            
            file_content = file_result["file_content"]
            
            # Step 3: Update document status
            await self.db_service.update_document_status(
                document_id, 
                "processing", 
                "Starting data extraction"
            )
            
            # Step 4: Analyze document with Textract
            logger.info(f"=== EXTRACTION DEBUG: Starting Textract analysis for {document['filename']} (type: {document['document_type']}) ===")
            extraction_result = await self._analyze_document_with_textract(
                file_content, 
                document["filename"], 
                document["document_type"],
                application_id,
                document_id
            )
            logger.info(f"=== EXTRACTION DEBUG: Textract analysis completed: success={extraction_result['success']} ===")
            logger.info(f"=== EXTRACTION DEBUG: Extraction result keys: {list(extraction_result.keys())} ===")
            if 'extracted_fields' in extraction_result:
                logger.info(f"=== EXTRACTION DEBUG: Number of extracted fields: {len(extraction_result['extracted_fields'])} ===")
                logger.info(f"=== EXTRACTION DEBUG: Extracted fields: {extraction_result['extracted_fields']} ===")
            
            if not extraction_result["success"]:
                logger.error(f"=== EXTRACTION DEBUG: Textract analysis failed: {extraction_result['error']} ===")
                await self._log_processing_step(
                    application_id, 
                    document_id,
                    "document_analysis", 
                    "failed", 
                    f"Textract analysis failed: {extraction_result['error']}"
                )
                await self.db_service.update_document_status(
                    document_id, 
                    "failed", 
                    f"Extraction failed: {extraction_result['error']}"
                )
                return extraction_result
            
            # Step 5: Process and store extracted data
            logger.info(f"=== EXTRACTION DEBUG: About to store {len(extraction_result.get('extracted_fields', []))} extracted fields ===")
            stored_fields = await self._store_extracted_data(
                document_id, 
                application_id, 
                extraction_result["extracted_fields"],
                extraction_result["raw_response"]
            )
            logger.info(f"=== EXTRACTION DEBUG: Stored fields result: {stored_fields} ===")
            
            # Step 6: Update document status
            await self.db_service.update_document_status(
                document_id, 
                "completed", 
                f"Extracted {len(stored_fields)} fields"
            )
            
            # Step 7: Create validation job
            job_data = {
                "application_id": application_id,
                "document_id": document_id,
                "job_type": "validation",
                "status": "pending",
                "priority": 3
            }
            await self.db_service.create_document_job(job_data)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            await self._log_processing_step(
                application_id, 
                document_id,
                "document_analysis", 
                "completed", 
                f"Successfully extracted {len(stored_fields)} fields",
                processing_time_ms=int(processing_time)
            )
            
            return {
                "success": True,
                "document_id": document_id,
                "extracted_fields_count": len(stored_fields),
                "extracted_fields": stored_fields,
                "processing_time_ms": int(processing_time)
            }
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = f"Data extraction failed: {str(e)}"
            
            await self._log_processing_step(
                application_id, 
                document_id,
                "document_analysis", 
                "failed", 
                error_msg,
                processing_time_ms=int(processing_time),
                error_details={"exception": str(e)}
            )
            
            await self.db_service.update_document_status(
                document_id, 
                "failed", 
                error_msg
            )
            
            logger.error(f"Data extraction error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "document_id": document_id
            }
    
    async def _analyze_document_with_textract(
        self, 
        file_content: bytes, 
        filename: str, 
        document_type: str,
        application_id: str,
        document_id: str
    ) -> Dict[str, Any]:
        """Analyze document with AWS Textract using temporary S3 upload"""
        try:
            # Step 1: Create temporary file and upload to S3 for Textract
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            s3_upload_result = await self.storage_service.upload_to_s3_temporary(
                temp_file_path, filename
            )
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            if not s3_upload_result["success"]:
                return {
                    "success": False,
                    "error": f"S3 upload failed: {s3_upload_result['error']}"
                }
            
            s3_key = s3_upload_result["s3_key"]
            
            # Step 2: Choose processing method based on document type
            if document_type == "mortgage_application":
                # Process mortgage application page by page (special handling)
                extraction_result = await self._process_mortgage_application_by_pages(
                    s3_key, document_type, application_id, document_id
                )
                return extraction_result
            else:
                # Process all other documents with basic method (all queries at once)
                queries = self.document_config.get_queries_for_document_type(document_type)
                logger.info(f"=== TEXTRACT DEBUG: Queries for {document_type}: {queries} ===")
                
                # Step 3: Start document analysis
                logger.info(f"=== TEXTRACT DEBUG: Starting document analysis with {len(queries)} queries ===")
                job_id = await self.textract_service.start_document_analysis(
                    s3_key, 
                    {"Queries": queries}
                )
                logger.info(f"=== TEXTRACT DEBUG: Started analysis job: {job_id} ===")
            
            # Step 4: Wait for completion and get results
            logger.info(f"=== TEXTRACT DEBUG: Waiting for analysis results ===")
            results = await self.textract_service.get_document_analysis_results(job_id)
            logger.info(f"=== TEXTRACT DEBUG: Got results, keys: {list(results.keys()) if isinstance(results, dict) else 'Not a dict'} ===")
            
            # Step 5: Process results
            logger.info(f"=== TEXTRACT DEBUG: Processing Textract results for {document_type} ===")
            print(f"=== TEXTRACT DEBUG: Raw Textract response: {json.dumps(results, indent=2)} ===")
            logger.info(f"=== TEXTRACT DEBUG: Raw Textract response: {json.dumps(results, indent=2)} ===")
            extracted_fields = self._process_textract_results(results, document_type)
            print(f"=== TEXTRACT DEBUG: Extracted {len(extracted_fields)} fields from {document_type} ===")
            logger.info(f"=== TEXTRACT DEBUG: Extracted {len(extracted_fields)} fields from {document_type} ===")
            print(f"=== TEXTRACT DEBUG: Extracted fields: {extracted_fields} ===")
            logger.info(f"=== TEXTRACT DEBUG: Extracted fields: {extracted_fields} ===")
            
            # Step 6: Clean up temporary S3 file
            await self.storage_service.delete_from_s3_temporary(s3_key)
            
            return {
                "success": True,
                "extracted_fields": extracted_fields,
                "raw_response": results,
                "job_id": job_id
            }
            
        except Exception as e:
            logger.error(f"Textract analysis error: {str(e)}")
            # Clean up temporary S3 file on error
            try:
                await self.storage_service.delete_from_s3_temporary(s3_key)
            except:
                pass  # Ignore cleanup errors
            return {
                "success": False,
                "error": str(e),
                "extracted_fields": [],
                "raw_response": None
            }
    
    async def _process_mortgage_application_by_pages(
        self, 
        s3_key: str, 
        document_type: str, 
        application_id: str, 
        document_id: str
    ) -> Dict[str, Any]:
        """Process mortgage application page by page"""
        try:
            all_extracted_fields = []
            all_raw_responses = []
            
            # Get total number of pages
            total_pages = self.document_config.get_page_count_for_document_type(document_type)
            
            await self._log_processing_step(
                application_id, 
                document_id,
                "page_based_processing", 
                "started", 
                f"Processing {total_pages} pages for mortgage application"
            )
            
            # Process each page
            for page_number in range(1, total_pages + 1):
                await self._log_processing_step(
                    application_id, 
                    document_id,
                    "page_processing", 
                    "started", 
                    f"Processing page {page_number}"
                )
                
                # Get queries for this page
                page_queries = self.document_config.get_queries_for_document_type(document_type, page_number)
                print(f"=== PAGE QUERY DEBUG: Page {page_number} has {len(page_queries) if page_queries else 0} queries ===")
                print(f"=== PAGE QUERY DEBUG: Queries: {page_queries} ===")
                
                if not page_queries:
                    logger.warning(f"No queries found for page {page_number}")
                    print(f"=== PAGE QUERY DEBUG: No queries found for page {page_number}, skipping ===")
                    continue
                
                # Start analysis for this page
                job_id = await self.textract_service.start_document_analysis(
                    s3_key, 
                    {"Queries": page_queries}
                )
                
                # Get results for this page
                page_results = await self.textract_service.get_document_analysis_results(job_id)
                print(f"=== PAGE TEXTRACT DEBUG: Got page {page_number} results, keys: {list(page_results.keys()) if isinstance(page_results, dict) else 'Not a dict'} ===")
                
                # Process results for this page
                print(f"=== PAGE TEXTRACT DEBUG: Processing page {page_number} results ===")
                page_extracted_fields = self._process_textract_results(page_results, document_type)
                print(f"=== PAGE TEXTRACT DEBUG: Page {page_number} extracted {len(page_extracted_fields)} fields ===")
                print(f"=== PAGE TEXTRACT DEBUG: Page {page_number} fields: {page_extracted_fields} ===")
                
                # Add page information to fields
                for field in page_extracted_fields:
                    field["page_number"] = page_number
                
                all_extracted_fields.extend(page_extracted_fields)
                all_raw_responses.append({
                    "page_number": page_number,
                    "results": page_results
                })
                
                await self._log_processing_step(
                    application_id, 
                    document_id,
                    "page_processing", 
                    "completed", 
                    f"Page {page_number} processed: {len(page_extracted_fields)} fields extracted"
                )
            
            await self._log_processing_step(
                application_id, 
                document_id,
                "page_based_processing", 
                "completed", 
                f"All {total_pages} pages processed: {len(all_extracted_fields)} total fields extracted"
            )
            
            return {
                "success": True,
                "extracted_fields": all_extracted_fields,
                "raw_response": all_raw_responses,
                "total_pages": total_pages,
                "total_fields": len(all_extracted_fields)
            }
            
        except Exception as e:
            logger.error(f"Error in page-based processing: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "extracted_fields": [],
                "raw_response": None
            }
    
    def _process_textract_results(
        self, 
        results: Dict[str, Any], 
        document_type: str
    ) -> List[Dict[str, Any]]:
        """Process Textract results into structured data using amazon-textract-response-parser"""
        extracted_fields = []
        
        try:
            logger.info(f"=== PROCESS DEBUG: Processing Textract results for {document_type} ===")
            logger.info(f"=== PROCESS DEBUG: Textract results keys: {list(results.keys())} ===")
            
            # Use amazon-textract-response-parser like the original system
            logger.info("=== PROCESS DEBUG: Using amazon-textract-response-parser to parse results ===")
            d = t2.TDocumentSchema().load(results)
            
            # Get field mappings for this document type
            field_mappings = self.document_config.get_field_mappings_for_document_type(document_type)
            logger.info(f"=== PROCESS DEBUG: Field mappings for {document_type}: {field_mappings} ===")
            
            # Process each page
            for page in d.pages:
                logger.info(f"=== PROCESS DEBUG: Processing page {page} ===")
                query_answers = d.get_query_answers(page=page)
                logger.info(f"=== PROCESS DEBUG: Found {len(query_answers)} query answers on page {page} ===")
                
                for answer in query_answers:
                    alias = answer[1]  # Query alias
                    text = answer[2]   # Extracted text
                    confidence = answer[3] if len(answer) > 3 else 95.0  # Confidence score
                    
                    logger.info(f"=== PROCESS DEBUG: Query answer - alias: {alias}, text: '{text}', confidence: {confidence} ===")
                    
                    if text and text.strip():
                        # Find the field name for this alias
                        field_name = None
                        for field, query_alias in field_mappings.items():
                            if query_alias == alias:
                                field_name = field
                                break
                        
                        if field_name:
                            field_data = {
                                "field_name": field_name,
                                "field_value": text.strip(),
                                "field_type": self._detect_field_type(field_name, text.strip()),
                                "confidence": confidence / 100.0 if confidence > 1 else confidence,
                                "extraction_method": "textract_query"
                            }
                            extracted_fields.append(field_data)
                            logger.info(f"=== EXTRACTED FIELD: {field_name} = '{text.strip()}' ===")
                        else:
                            logger.warning(f"=== NO FIELD MAPPING for alias: {alias} ===")
                    else:
                        logger.warning(f"=== EMPTY TEXT for alias: {alias} ===")
            
            logger.info(f"=== PROCESS DEBUG: Total extracted fields: {len(extracted_fields)} ===")
            logger.info(f"=== EXTRACTED FIELDS: {extracted_fields} ===")
            return extracted_fields
            
        except Exception as e:
            logger.error(f"=== PROCESS DEBUG: Error processing Textract results: {str(e)} ===")
            logger.error(f"=== PROCESS DEBUG: Falling back to manual parsing ===")
            
            # Fallback to manual parsing if trp2 fails
            try:
                if "Blocks" not in results:
                    logger.warning("=== PROCESS DEBUG: No blocks found in Textract results ===")
                    return extracted_fields
                
                # Manual parsing fallback
                query_results = {}
                for block in results["Blocks"]:
                    if block.get("BlockType") == "QUERY_RESULT":
                        query_alias = block.get("Query", {}).get("Alias", "")
                        if query_alias:
                            query_results[query_alias] = {
                                "text": block.get("Text", ""),
                                "confidence": block.get("Confidence", 0) / 100.0
                            }
                
                # Map query results to field names
                field_mappings = self.document_config.get_field_mappings_for_document_type(document_type)
                for field_name, query_alias in field_mappings.items():
                    if query_alias in query_results:
                        result = query_results[query_alias]
                        field_data = {
                            "field_name": field_name,
                            "field_value": result["text"],
                            "field_type": self._detect_field_type(field_name, result["text"]),
                            "confidence": result["confidence"],
                            "extraction_method": "textract_query_manual"
                        }
                        extracted_fields.append(field_data)
                        logger.info(f"=== MANUAL EXTRACTED FIELD: {field_name} = '{result['text']}' ===")
                
                logger.info(f"=== MANUAL FALLBACK: Total extracted fields: {len(extracted_fields)} ===")
                return extracted_fields
                
            except Exception as fallback_error:
                logger.error(f"=== PROCESS DEBUG: Manual parsing also failed: {str(fallback_error)} ===")
                return extracted_fields
    
    def _extract_from_form_data(self, results: Dict[str, Any], field_name: str) -> Optional[Dict[str, Any]]:
        """Extract field value from form data"""
        try:
            # This is a simplified implementation
            # In practice, you'd have more sophisticated form field detection
            form_fields = {}
            
            for block in results.get("Blocks", []):
                if block["BlockType"] == "KEY_VALUE_SET":
                    if "KEY" in block.get("EntityTypes", []):
                        # This is a key
                        key_text = self._get_text_from_block(block, results)
                        if key_text and field_name.lower() in key_text.lower():
                            # Find corresponding value
                            value_block = self._find_value_block(block, results)
                            if value_block:
                                value_text = self._get_text_from_block(value_block, results)
                                confidence = value_block.get("Confidence", 0) / 100.0
                                return {
                                    "text": value_text,
                                    "confidence": confidence
                                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting from form data: {str(e)}")
            return None
    
    def _get_text_from_block(self, block: Dict[str, Any], results: Dict[str, Any]) -> str:
        """Get text content from a block"""
        try:
            if "Text" in block:
                return block["Text"]
            
            # Get text from child blocks
            text_parts = []
            for relationship in block.get("Relationships", []):
                if relationship["Type"] == "CHILD":
                    for child_id in relationship["Ids"]:
                        child_block = self._find_block_by_id(results, child_id)
                        if child_block and child_block["BlockType"] == "WORD":
                            text_parts.append(child_block.get("Text", ""))
            
            return " ".join(text_parts)
            
        except Exception as e:
            logger.error(f"Error getting text from block: {str(e)}")
            return ""
    
    def _find_block_by_id(self, results: Dict[str, Any], block_id: str) -> Optional[Dict[str, Any]]:
        """Find block by ID"""
        for block in results.get("Blocks", []):
            if block["Id"] == block_id:
                return block
        return None
    
    def _find_value_block(self, key_block: Dict[str, Any], results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find value block for a key block"""
        try:
            for relationship in key_block.get("Relationships", []):
                if relationship["Type"] == "VALUE":
                    for value_id in relationship["Ids"]:
                        value_block = self._find_block_by_id(results, value_id)
                        if value_block:
                            return value_block
            return None
        except Exception as e:
            logger.error(f"Error finding value block: {str(e)}")
            return None
    
    def _detect_field_type(self, field_name: str, field_value: str) -> str:
        """Detect field type based on name and value"""
        try:
            field_name_lower = field_name.lower()
            field_value_clean = field_value.strip()
            
            # Currency fields
            if any(keyword in field_name_lower for keyword in ['amount', 'salary', 'income', 'balance', 'price', 'cost']):
                if '$' in field_value_clean or any(char.isdigit() for char in field_value_clean):
                    return 'currency'
            
            # Date fields
            if any(keyword in field_name_lower for keyword in ['date', 'dob', 'birth', 'start', 'end']):
                return 'date'
            
            # Number fields
            if any(keyword in field_name_lower for keyword in ['number', 'count', 'quantity', 'rate']):
                if field_value_clean.replace('.', '').replace(',', '').isdigit():
                    return 'number'
            
            # Percentage fields
            if 'percent' in field_name_lower or '%' in field_value_clean:
                return 'percentage'
            
            # Default to text
            return 'text'
            
        except Exception as e:
            logger.error(f"Error detecting field type: {str(e)}")
            return 'text'
    
    async def _store_extracted_data(
        self, 
        document_id: str, 
        application_id: str, 
        extracted_fields: List[Dict[str, Any]],
        raw_response: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Store extracted data in database"""
        try:
            logger.info(f"=== STORE DEBUG: Starting _store_extracted_data for document {document_id} ===")
            logger.info(f"=== STORE DEBUG: Extracted fields count: {len(extracted_fields) if extracted_fields else 0} ===")
            logger.info(f"=== STORE DEBUG: Extracted fields: {extracted_fields} ===")
            
            if not extracted_fields:
                logger.warning("=== STORE DEBUG: No extracted fields to store ===")
                return []
            
            # Get document info for document_type
            logger.info(f"=== STORE DEBUG: Getting document info for {document_id} ===")
            document = await self.db_service.get_document(document_id)
            if not document:
                logger.error(f"=== STORE DEBUG: Document {document_id} not found ===")
                return []
            
            logger.info(f"=== STORE DEBUG: Document found: {document} ===")
            
            # Calculate statistics
            field_count = len(extracted_fields)
            confidences = [field.get("confidence", 0.0) for field in extracted_fields]
            average_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Create a single record with all fields stored as JSONB
            extracted_data_record = {
                "document_id": document_id,
                "application_id": application_id,
                "document_type": document["document_type"],
                "extracted_fields": extracted_fields,  # Store as JSONB
                "field_count": field_count,
                "average_confidence": average_confidence,
                "extraction_method": "textract_form",
                "raw_response": raw_response,  # Store as JSONB
                "page_number": 1,  # Default for non-mortgage applications
                "agent_version": "1.0"
            }
            
            logger.info(f"=== STORE DEBUG: About to create extracted data record: {extracted_data_record} ===")
            result = await self.db_service.create_extracted_data(extracted_data_record)
            logger.info(f"=== STORE DEBUG: Stored {field_count} extracted fields for document {document_id}, result: {result} ===")
            return [{"id": result, "field_count": field_count}]
            
        except Exception as e:
            logger.error(f"=== STORE DEBUG: Error storing extracted data: {str(e)} ===")
            import traceback
            logger.error(f"=== STORE DEBUG: Traceback: {traceback.format_exc()} ===")
            return []
    
    async def _log_processing_step(
        self, 
        application_id: str, 
        document_id: str,
        step_name: str, 
        status: str, 
        message: str,
        processing_time_ms: Optional[int] = None,
        error_details: Optional[Dict] = None
    ):
        """Log processing step"""
        try:
            log_data = {
                "application_id": application_id,
                "document_id": document_id,
                "agent_name": "extraction",
                "step_name": step_name,
                "status": status,
                "message": message,
                "processing_time_ms": processing_time_ms,
                "error_details": error_details
            }
            await self.db_service.create_processing_log(log_data)
        except Exception as e:
            logger.error(f"Failed to log processing step: {str(e)}")
    
    async def get_extraction_status(self, application_id: str) -> Dict[str, Any]:
        """Get extraction status for an application"""
        try:
            documents = await self.db_service.get_documents_by_application(application_id)
            extracted_data = await self.db_service.get_extracted_data_by_application(application_id)
            
            total_documents = len(documents)
            processed_documents = len([d for d in documents if d["processing_status"] == "completed"])
            total_extracted_fields = len(extracted_data)
            
            # Group by field type
            field_types = {}
            for data in extracted_data:
                field_type = data["field_type"]
                field_types[field_type] = field_types.get(field_type, 0) + 1
            
            # Calculate average confidence
            avg_confidence = 0
            if extracted_data:
                total_confidence = sum(data["confidence"] for data in extracted_data)
                avg_confidence = total_confidence / len(extracted_data)
            
            return {
                "application_id": application_id,
                "total_documents": total_documents,
                "processed_documents": processed_documents,
                "total_extracted_fields": total_extracted_fields,
                "field_types": field_types,
                "average_confidence": avg_confidence,
                "extraction_completion_percentage": (processed_documents / total_documents * 100) if total_documents > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get extraction status: {str(e)}")
            return {
                "application_id": application_id,
                "error": str(e)
            }
