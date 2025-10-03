"""
Data Formatting Agent
Handles final data formatting and storage in the golden table
"""

import re
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from models.golden_data import GoldenData
from models.validation_result import ValidationResult
from services.database_service import DatabaseService
from config.formatting_config import FormattingConfig
from utils.logger import get_logger

logger = get_logger(__name__)

class DataFormattingAgent:
    """
    Agent responsible for:
    1. Data normalization and formatting
    2. Conflict resolution between sources
    3. Golden table population
    4. Data quality scoring
    5. Final data structure preparation for decision engine
    """
    
    def __init__(self):
        self.db_service = DatabaseService()
        self.formatting_config = FormattingConfig()
        
    async def format_application_data(
        self, 
        application_id: str
    ) -> Dict[str, Any]:
        """
        Format and store final application data in golden table
        
        Args:
            application_id: Application identifier
            
        Returns:
            Dict with formatting results
        """
        start_time = datetime.now()
        
        try:
            # Log start
            await self._log_processing_step(
                application_id, 
                None,
                "data_formatting", 
                "started", 
                "Starting data formatting process"
            )
            
            # Step 1: Get validation results
            validation_results = await self.db_service.get_validation_results_by_application(application_id)
            if not validation_results:
                raise Exception(f"No validation results found for: {application_id}")
            
            # Step 2: Get application form data
            application_data = await self.db_service.get_application_form_data(application_id)
            if not application_data:
                raise Exception(f"No application form data found for: {application_id}")
            
            # Step 3: Process each field for golden table
            golden_records = []
            processed_fields = 0
            skipped_fields = 0
            
            for field_name, app_value in application_data.items():
                # Get validation result for this field
                validation_result = self._find_validation_result(field_name, validation_results)
                
                if not validation_result:
                    # No validation result, skip field
                    skipped_fields += 1
                    continue
                
                # Format and create golden record
                golden_record = await self._create_golden_record(
                    application_id,
                    field_name,
                    app_value,
                    validation_result
                )
                
                if golden_record:
                    golden_records.append(golden_record)
                    processed_fields += 1
                else:
                    skipped_fields += 1
            
            # Step 4: Store golden records
            stored_records = await self._store_golden_records(golden_records)
            
            # Step 5: Calculate data quality metrics
            quality_metrics = self._calculate_data_quality_metrics(stored_records)
            
            # Step 6: Update application status
            await self.db_service.update_application_status(
                application_id, 
                "completed", 
                f"Data formatting completed: {processed_fields} fields processed",
                completion_percentage=100.0
            )
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            await self._log_processing_step(
                application_id, 
                None,
                "data_formatting", 
                "completed", 
                f"Data formatting completed: {processed_fields} fields processed, {skipped_fields} skipped",
                processing_time_ms=int(processing_time)
            )
            
            return {
                "success": True,
                "application_id": application_id,
                "processed_fields": processed_fields,
                "skipped_fields": skipped_fields,
                "golden_records": stored_records,
                "quality_metrics": quality_metrics,
                "processing_time_ms": int(processing_time)
            }
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = f"Data formatting failed: {str(e)}"
            
            await self._log_processing_step(
                application_id, 
                None,
                "data_formatting", 
                "failed", 
                error_msg,
                processing_time_ms=int(processing_time),
                error_details={"exception": str(e)}
            )
            
            logger.error(f"Data formatting error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "application_id": application_id
            }
    
    def _find_validation_result(self, field_name: str, validation_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find validation result for a field"""
        for result in validation_results:
            if result["field_name"] == field_name:
                return result
        return None
    
    async def _create_golden_record(
        self, 
        application_id: str,
        field_name: str, 
        app_value: str, 
        validation_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create golden record for a field"""
        try:
            # Determine best value source
            best_value, data_source, confidence_score = self._determine_best_value(
                field_name, 
                app_value, 
                validation_result
            )
            
            if not best_value:
                return None
            
            # Format the value
            formatted_value = self._format_field_value(field_name, best_value)
            
            # Determine field type
            field_type = self._determine_field_type(field_name, formatted_value)
            
            # Create golden record
            golden_record = {
                "application_id": application_id,
                "field_name": field_name,
                "field_value": formatted_value,
                "field_type": field_type,
                "data_source": data_source,
                "source_document_id": validation_result.get("document_id"),
                "validation_status": validation_result["validation_status"],
                "confidence_score": confidence_score,
                "is_verified": validation_result["validation_status"] == "validated",
                "verification_notes": self._generate_verification_notes(validation_result),
                "agent_version": "1.0"
            }
            
            return golden_record
            
        except Exception as e:
            logger.error(f"Error creating golden record for {field_name}: {str(e)}")
            return None
    
    def _determine_best_value(
        self, 
        field_name: str, 
        app_value: str, 
        validation_result: Dict[str, Any]
    ) -> Tuple[Optional[str], str, float]:
        """Determine the best value source and confidence"""
        try:
            validation_status = validation_result["validation_status"]
            doc_value = validation_result.get("document_value")
            confidence_score = validation_result.get("confidence_score", 0.0)
            
            if validation_status == "validated":
                # Values match, prefer document value if available
                if doc_value:
                    return doc_value, "document_extraction", confidence_score
                else:
                    return app_value, "application_form", 0.9  # High confidence for validated app data
            
            elif validation_status == "mismatch":
                # Values don't match, need to choose best source
                mismatch_severity = validation_result.get("mismatch_severity", "medium")
                
                if mismatch_severity == "critical":
                    # Critical mismatch, prefer application form
                    return app_value, "application_form", 0.7
                elif mismatch_severity == "high":
                    # High severity, prefer application form
                    return app_value, "application_form", 0.6
                elif confidence_score > 0.8:
                    # High confidence document value
                    return doc_value, "document_extraction", confidence_score
                else:
                    # Low confidence, prefer application form
                    return app_value, "application_form", 0.5
            
            elif validation_status == "missing":
                # No document data, use application form
                return app_value, "application_form", 0.8
            
            else:
                # Unknown status, use application form
                return app_value, "application_form", 0.5
                
        except Exception as e:
            logger.error(f"Error determining best value: {str(e)}")
            return app_value, "application_form", 0.5
    
    def _format_field_value(self, field_name: str, value: str) -> str:
        """Format field value according to field type"""
        try:
            if not value:
                return ""
            
            field_type = self._determine_field_type(field_name, value)
            
            if field_type == "currency":
                return self._format_currency(value)
            elif field_type == "date":
                return self._format_date(value)
            elif field_type == "number":
                return self._format_number(value)
            elif field_type == "percentage":
                return self._format_percentage(value)
            elif field_type == "text":
                return self._format_text(value)
            else:
                return str(value).strip()
                
        except Exception as e:
            logger.error(f"Error formatting field value: {str(e)}")
            return str(value).strip()
    
    def _format_currency(self, value: str) -> str:
        """Format currency value"""
        try:
            # Remove currency symbols and commas
            cleaned = re.sub(r'[^\d.-]', '', value)
            if not cleaned:
                return ""
            
            # Parse to float and format
            amount = float(cleaned)
            return f"${amount:,.2f}"
            
        except (ValueError, TypeError):
            return value
    
    def _format_date(self, value: str) -> str:
        """Format date value"""
        try:
            # Try to parse and standardize date
            date_patterns = [
                r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY
                r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
                r'(\d{1,2})-(\d{1,2})-(\d{4})',  # MM-DD-YYYY
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, value)
                if match:
                    groups = match.groups()
                    if len(groups) == 3:
                        if len(groups[0]) == 4:  # YYYY-MM-DD
                            return f"{groups[0]}-{groups[1].zfill(2)}-{groups[2].zfill(2)}"
                        elif int(groups[0]) > 12:  # DD/MM/YYYY
                            return f"{groups[2]}-{groups[1].zfill(2)}-{groups[0].zfill(2)}"
                        else:  # MM/DD/YYYY
                            return f"{groups[2]}-{groups[0].zfill(2)}-{groups[1].zfill(2)}"
            
            return value
            
        except Exception as e:
            logger.error(f"Error formatting date: {str(e)}")
            return value
    
    def _format_number(self, value: str) -> str:
        """Format number value"""
        try:
            # Remove commas and extra spaces
            cleaned = re.sub(r'[^\d.-]', '', value)
            if not cleaned:
                return ""
            
            # Parse to float
            number = float(cleaned)
            
            # Format with appropriate precision
            if number == int(number):
                return str(int(number))
            else:
                return f"{number:.2f}"
                
        except (ValueError, TypeError):
            return value
    
    def _format_percentage(self, value: str) -> str:
        """Format percentage value"""
        try:
            # Remove % symbol
            cleaned = re.sub(r'[^\d.-]', '', value)
            if not cleaned:
                return ""
            
            # Parse to float
            percentage = float(cleaned)
            
            # Ensure it's between 0 and 100
            if percentage > 1:
                percentage = percentage / 100
            
            return f"{percentage:.2%}"
            
        except (ValueError, TypeError):
            return value
    
    def _format_text(self, value: str) -> str:
        """Format text value"""
        try:
            # Clean and normalize text
            cleaned = re.sub(r'\s+', ' ', value.strip())
            
            # Capitalize first letter of each word for names
            if any(keyword in value.lower() for keyword in ['name', 'first', 'last', 'middle']):
                return cleaned.title()
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Error formatting text: {str(e)}")
            return value
    
    def _determine_field_type(self, field_name: str, value: str) -> str:
        """Determine field type based on name and value"""
        try:
            field_name_lower = field_name.lower()
            
            # Currency fields
            if any(keyword in field_name_lower for keyword in ['amount', 'salary', 'income', 'balance', 'price', 'cost']):
                if '$' in value or any(char.isdigit() for char in value):
                    return 'currency'
            
            # Date fields
            if any(keyword in field_name_lower for keyword in ['date', 'dob', 'birth', 'start', 'end']):
                return 'date'
            
            # Number fields
            if any(keyword in field_name_lower for keyword in ['number', 'count', 'quantity', 'rate']):
                if value.replace('.', '').replace(',', '').isdigit():
                    return 'number'
            
            # Percentage fields
            if 'percent' in field_name_lower or '%' in value:
                return 'percentage'
            
            # Boolean fields
            if any(keyword in field_name_lower for keyword in ['is_', 'has_', 'can_', 'will_']):
                if value.lower() in ['true', 'false', 'yes', 'no', '1', '0']:
                    return 'boolean'
            
            # Default to text
            return 'text'
            
        except Exception as e:
            logger.error(f"Error determining field type: {str(e)}")
            return 'text'
    
    def _generate_verification_notes(self, validation_result: Dict[str, Any]) -> str:
        """Generate verification notes for golden record"""
        try:
            validation_status = validation_result["validation_status"]
            mismatch_severity = validation_result.get("mismatch_severity")
            validation_notes = validation_result.get("validation_notes", "")
            
            if validation_status == "validated":
                return "Data validated successfully - application and document values match"
            elif validation_status == "mismatch":
                severity_text = f" ({mismatch_severity} severity)" if mismatch_severity else ""
                return f"Data mismatch detected{severity_text}. {validation_notes}"
            elif validation_status == "missing":
                return f"No document data available for validation. {validation_notes}"
            else:
                return f"Validation status: {validation_status}. {validation_notes}"
                
        except Exception as e:
            logger.error(f"Error generating verification notes: {str(e)}")
            return "Verification notes generation failed"
    
    def _calculate_data_quality_metrics(self, golden_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate data quality metrics"""
        try:
            if not golden_records:
                return {
                    "total_fields": 0,
                    "verified_fields": 0,
                    "high_confidence_fields": 0,
                    "data_source_distribution": {},
                    "field_type_distribution": {},
                    "overall_quality_score": 0.0
                }
            
            total_fields = len(golden_records)
            verified_fields = len([r for r in golden_records if r["is_verified"]])
            high_confidence_fields = len([r for r in golden_records if r["confidence_score"] and r["confidence_score"] >= 0.8])
            
            # Data source distribution
            data_source_distribution = {}
            for record in golden_records:
                source = record["data_source"]
                data_source_distribution[source] = data_source_distribution.get(source, 0) + 1
            
            # Field type distribution
            field_type_distribution = {}
            for record in golden_records:
                field_type = record["field_type"]
                field_type_distribution[field_type] = field_type_distribution.get(field_type, 0) + 1
            
            # Calculate overall quality score
            verification_score = verified_fields / total_fields if total_fields > 0 else 0
            confidence_score = high_confidence_fields / total_fields if total_fields > 0 else 0
            overall_quality_score = (verification_score * 0.6) + (confidence_score * 0.4)
            
            return {
                "total_fields": total_fields,
                "verified_fields": verified_fields,
                "high_confidence_fields": high_confidence_fields,
                "data_source_distribution": data_source_distribution,
                "field_type_distribution": field_type_distribution,
                "overall_quality_score": overall_quality_score,
                "verification_percentage": verification_score * 100,
                "confidence_percentage": confidence_score * 100
            }
            
        except Exception as e:
            logger.error(f"Error calculating data quality metrics: {str(e)}")
            return {
                "total_fields": 0,
                "verified_fields": 0,
                "high_confidence_fields": 0,
                "data_source_distribution": {},
                "field_type_distribution": {},
                "overall_quality_score": 0.0,
                "verification_percentage": 0.0,
                "confidence_percentage": 0.0
            }
    
    async def _store_golden_records(self, golden_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Store golden records in database"""
        stored_records = []
        
        try:
            for record in golden_records:
                stored_record = await self.db_service.create_golden_data(record)
                stored_records.append(stored_record)
            
            return stored_records
            
        except Exception as e:
            logger.error(f"Error storing golden records: {str(e)}")
            return stored_records
    
    async def _log_processing_step(
        self, 
        application_id: str, 
        document_id: Optional[str],
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
                "agent_name": "formatting",
                "step_name": step_name,
                "status": status,
                "message": message,
                "processing_time_ms": processing_time_ms,
                "error_details": error_details
            }
            await self.db_service.create_processing_log(log_data)
        except Exception as e:
            logger.error(f"Failed to log processing step: {str(e)}")
    
    async def get_formatting_status(self, application_id: str) -> Dict[str, Any]:
        """Get formatting status for an application"""
        try:
            golden_data = await self.db_service.get_golden_data_by_application(application_id)
            
            total_fields = len(golden_data)
            verified_fields = len([d for d in golden_data if d["is_verified"]])
            high_confidence_fields = len([d for d in golden_data if d["confidence_score"] and d["confidence_score"] >= 0.8])
            
            # Group by data source
            data_sources = {}
            for data in golden_data:
                source = data["data_source"]
                data_sources[source] = data_sources.get(source, 0) + 1
            
            # Group by field type
            field_types = {}
            for data in golden_data:
                field_type = data["field_type"]
                field_types[field_type] = field_types.get(field_type, 0) + 1
            
            return {
                "application_id": application_id,
                "total_fields": total_fields,
                "verified_fields": verified_fields,
                "high_confidence_fields": high_confidence_fields,
                "data_sources": data_sources,
                "field_types": field_types,
                "formatting_completion_percentage": 100.0 if total_fields > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get formatting status: {str(e)}")
            return {
                "application_id": application_id,
                "error": str(e)
            }
    
    async def get_golden_data_summary(self, application_id: str) -> Dict[str, Any]:
        """Get comprehensive golden data summary for decision engine"""
        try:
            golden_data = await self.db_service.get_golden_data_by_application(application_id)
            
            if not golden_data:
                return {
                    "application_id": application_id,
                    "status": "no_data",
                    "message": "No golden data available"
                }
            
            # Organize data by categories
            personal_info = {}
            financial_info = {}
            employment_info = {}
            property_info = {}
            other_info = {}
            
            for data in golden_data:
                field_name = data["field_name"]
                field_value = data["field_value"]
                field_type = data["field_type"]
                confidence_score = data["confidence_score"]
                is_verified = data["is_verified"]
                
                field_data = {
                    "value": field_value,
                    "type": field_type,
                    "confidence": confidence_score,
                    "verified": is_verified,
                    "source": data["data_source"]
                }
                
                # Categorize fields
                if any(keyword in field_name.lower() for keyword in ['name', 'dob', 'address', 'phone', 'email', 'sin']):
                    personal_info[field_name] = field_data
                elif any(keyword in field_name.lower() for keyword in ['income', 'salary', 'balance', 'amount', 'debt', 'asset']):
                    financial_info[field_name] = field_data
                elif any(keyword in field_name.lower() for keyword in ['employer', 'job', 'work', 'position', 'company']):
                    employment_info[field_name] = field_data
                elif any(keyword in field_name.lower() for keyword in ['property', 'address', 'value', 'assessment']):
                    property_info[field_name] = field_data
                else:
                    other_info[field_name] = field_data
            
            # Calculate overall metrics
            total_fields = len(golden_data)
            verified_fields = len([d for d in golden_data if d["is_verified"]])
            high_confidence_fields = len([d for d in golden_data if d["confidence_score"] and d["confidence_score"] >= 0.8])
            
            return {
                "application_id": application_id,
                "status": "completed",
                "total_fields": total_fields,
                "verified_fields": verified_fields,
                "high_confidence_fields": high_confidence_fields,
                "data_quality_score": (verified_fields / total_fields * 100) if total_fields > 0 else 0,
                "categories": {
                    "personal_info": personal_info,
                    "financial_info": financial_info,
                    "employment_info": employment_info,
                    "property_info": property_info,
                    "other_info": other_info
                },
                "ready_for_decision_engine": verified_fields >= (total_fields * 0.8)  # 80% verified
            }
            
        except Exception as e:
            logger.error(f"Failed to get golden data summary: {str(e)}")
            return {
                "application_id": application_id,
                "status": "error",
                "message": str(e)
            }
