"""
Data Validation Agent
Handles validation of extracted data against application form data
"""

import re
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from difflib import SequenceMatcher

from models.validation_result import ValidationResult
from models.extracted_data import ExtractedData
from services.database_service import DatabaseService
from config.validation_config import ValidationConfig
from utils.logger import get_logger

logger = get_logger(__name__)

class DataValidationAgent:
    """
    Agent responsible for:
    1. Cross-validation of application form vs document data
    2. Data consistency checks
    3. Mismatch detection and severity assessment
    4. Flagging for manual review
    5. Validation confidence scoring
    """
    
    def __init__(self):
        self.db_service = DatabaseService()
        self.validation_config = ValidationConfig()
        
    async def validate_application_data(
        self, 
        application_id: str
    ) -> Dict[str, Any]:
        """
        Validate all application data against extracted document data
        
        Args:
            application_id: Application identifier
            
        Returns:
            Dict with validation results
        """
        start_time = datetime.now()
        
        try:
            # Log start
            await self._log_processing_step(
                application_id, 
                None,
                "data_validation", 
                "started", 
                "Starting data validation process"
            )
            
            # Step 1: Get application form data
            application_data = await self.db_service.get_application_form_data(application_id)
            if not application_data:
                raise Exception(f"No application form data found for: {application_id}")
            
            # Step 2: Get extracted document data
            extracted_data = await self.db_service.get_extracted_data_by_application(application_id)
            if not extracted_data:
                raise Exception(f"No extracted data found for: {application_id}")
            
            # Step 3: Group extracted data by field name
            document_data_by_field = self._group_extracted_data_by_field(extracted_data)
            
            # Step 4: Perform validation for each field
            validation_results = []
            total_fields = len(application_data)
            validated_fields = 0
            mismatch_fields = 0
            missing_fields = 0
            
            # Get document metadata for validation
            document_metadata = {}
            for data in extracted_data:
                if 'document_type' in data and 'document_id' in data:
                    document_metadata[data['document_id']] = {
                        'document_type': data['document_type'],
                        'document_id': data['document_id']
                    }
            
            for field_name, app_value in application_data.items():
                validation_result = await self._validate_single_field(
                    application_id,
                    field_name,
                    app_value,
                    document_data_by_field.get(field_name, []),
                    document_metadata
                )
                
                validation_results.append(validation_result)
                
                # Update counters
                if validation_result["validation_status"] == "validated":
                    validated_fields += 1
                elif validation_result["validation_status"] == "mismatch":
                    mismatch_fields += 1
                elif validation_result["validation_status"] == "missing":
                    missing_fields += 1
            
            # Step 5: Store validation results
            stored_results = await self._store_validation_results(validation_results)
            
            # Step 6: Calculate validation summary
            validation_summary = self._calculate_validation_summary(
                validation_results, 
                total_fields, 
                validated_fields, 
                mismatch_fields, 
                missing_fields
            )
            
            # Step 6.5: Store validation summary result
            summary_result = {
                "application_id": application_id,
                "validation_summary": validation_summary,
                "total_fields": total_fields,
                "validated_fields": validated_fields,
                "mismatched_fields": mismatch_fields,
                "missing_fields": missing_fields,
                "critical_mismatches": sum(1 for r in validation_results if r.get("mismatch_severity") == "critical"),
                "high_mismatches": sum(1 for r in validation_results if r.get("mismatch_severity") == "high"),
                "medium_mismatches": sum(1 for r in validation_results if r.get("mismatch_severity") == "medium"),
                "low_mismatches": sum(1 for r in validation_results if r.get("mismatch_severity") == "low"),
                "overall_validation_score": validation_summary.get("overall_validation_score", 0.0),
                "flag_for_review": validation_summary.get("flag_for_review", False),
                "validation_notes": f"Validation completed: {validated_fields} validated, {mismatch_fields} mismatches, {missing_fields} missing",
                "agent_version": "1.0"
            }
            await self.db_service.create_validation_result(summary_result)
            
            # Step 7: Create formatting job if validation is complete
            if validation_summary["validation_completion_percentage"] >= 80:
                job_data = {
                    "application_id": application_id,
                    "document_id": None,  # Application-level job
                    "job_type": "formatting",
                    "status": "pending",
                    "priority": 2
                }
                await self.db_service.create_document_job(job_data)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            await self._log_processing_step(
                application_id, 
                None,
                "data_validation", 
                "completed", 
                f"Validation completed: {validated_fields} validated, {mismatch_fields} mismatches, {missing_fields} missing",
                processing_time_ms=int(processing_time)
            )
            
            return {
                "success": True,
                "application_id": application_id,
                "validation_summary": validation_summary,
                "validation_results": stored_results,
                "processing_time_ms": int(processing_time)
            }
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = f"Data validation failed: {str(e)}"
            
            await self._log_processing_step(
                application_id, 
                None,
                "data_validation", 
                "failed", 
                error_msg,
                processing_time_ms=int(processing_time),
                error_details={"exception": str(e)}
            )
            
            logger.error(f"Data validation error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "application_id": application_id
            }
    
    def _group_extracted_data_by_field(self, extracted_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group extracted data by field name"""
        grouped_data = {}
        
        for data in extracted_data:
            # Parse the extracted_fields JSON array
            if 'extracted_fields' in data and data['extracted_fields']:
                import json
                if isinstance(data['extracted_fields'], str):
                    fields = json.loads(data['extracted_fields'])
                else:
                    fields = data['extracted_fields']
                
                # Group each field by field_name
                for field in fields:
                    field_name = field["field_name"]
                    if field_name not in grouped_data:
                        grouped_data[field_name] = []
                    grouped_data[field_name].append(field)
        
        return grouped_data
    
    async def _validate_single_field(
        self, 
        application_id: str,
        field_name: str, 
        app_value: str, 
        document_data: List[Dict[str, Any]],
        document_metadata: Dict[str, Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Validate a single field against document data"""
        try:
            # Get field validation configuration
            field_config = self.validation_config.get_field_config(field_name)
            
            if not document_data:
                # No document data found
                return {
                    "application_id": application_id,
                    "field_name": field_name,
                    "application_value": app_value,
                    "document_value": None,
                    "document_type": None,
                    "document_id": None,
                    "validation_status": "missing",
                    "mismatch_type": "missing_document",
                    "mismatch_severity": self._get_missing_severity(field_name, field_config),
                    "discrepancy_percentage": None,
                    "confidence_score": 0.0,
                    "flag_for_review": True,
                    "validation_notes": f"No document data found for field: {field_name}",
                    "agent_version": "1.0"
                }
            
            # Find best matching document data
            best_match = self._find_best_document_match(field_name, app_value, document_data, field_config)
            
            if not best_match:
                # No good match found
                return {
                    "application_id": application_id,
                    "field_name": field_name,
                    "application_value": app_value,
                    "document_value": None,
                    "document_type": None,
                    "document_id": None,
                    "validation_status": "mismatch",
                    "mismatch_type": "value_difference",
                    "mismatch_severity": "high",
                    "discrepancy_percentage": 100.0,
                    "confidence_score": 0.0,
                    "flag_for_review": True,
                    "validation_notes": f"No matching document value found for field: {field_name}",
                    "agent_version": "1.0"
                }
            
            # Perform validation comparison
            validation_result = self._compare_values(
                field_name, 
                app_value, 
                best_match["field_value"], 
                field_config
            )
            
            # Add metadata
            # Get document metadata from the best match
            doc_meta = None
            if document_metadata and best_match.get("document_id"):
                doc_meta = document_metadata.get(best_match["document_id"])
            
            validation_result.update({
                "application_id": application_id,
                "field_name": field_name,
                "application_value": app_value,
                "document_value": best_match["field_value"],
                "document_type": doc_meta["document_type"] if doc_meta else None,
                "document_id": doc_meta["document_id"] if doc_meta else None,
                "confidence_score": best_match["confidence"],
                "agent_version": "1.0"
            })
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating field {field_name}: {str(e)}")
            return {
                "application_id": application_id,
                "field_name": field_name,
                "application_value": app_value,
                "document_value": None,
                "document_type": None,
                "document_id": None,
                "validation_status": "mismatch",
                "mismatch_type": "validation_error",
                "mismatch_severity": "critical",
                "discrepancy_percentage": None,
                "confidence_score": 0.0,
                "flag_for_review": True,
                "validation_notes": f"Validation error: {str(e)}",
                "agent_version": "1.0"
            }
    
    def _find_best_document_match(
        self, 
        field_name: str, 
        app_value: str, 
        document_data: List[Dict[str, Any]], 
        field_config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find the best matching document data for a field"""
        try:
            if not document_data:
                return None
            
            # If only one document data, use it
            if len(document_data) == 1:
                return document_data[0]
            
            # Score each document data based on confidence and similarity
            scored_data = []
            for data in document_data:
                similarity_score = self._calculate_similarity(app_value, data["field_value"])
                confidence_score = data["confidence"]
                
                # Combined score (weighted average)
                combined_score = (similarity_score * 0.7) + (confidence_score * 0.3)
                
                scored_data.append({
                    **data,
                    "similarity_score": similarity_score,
                    "combined_score": combined_score
                })
            
            # Sort by combined score and return best match
            scored_data.sort(key=lambda x: x["combined_score"], reverse=True)
            best_match = scored_data[0]
            
            # Only return if similarity is above threshold
            similarity_threshold = field_config.get("similarity_threshold", 0.5)
            if best_match["similarity_score"] >= similarity_threshold:
                return best_match
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding best document match: {str(e)}")
            return None
    
    def _compare_values(
        self, 
        field_name: str, 
        app_value: str, 
        doc_value: str, 
        field_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare application value with document value"""
        try:
            validation_type = field_config.get("validation_type", "text")
            tolerance = field_config.get("tolerance", 0.8)
            
            # Normalize values
            app_normalized = self._normalize_value(app_value, validation_type)
            doc_normalized = self._normalize_value(doc_value, validation_type)
            
            # Perform comparison based on type
            if validation_type == "text":
                return self._validate_text(app_normalized, doc_normalized, field_name, tolerance)
            elif validation_type == "currency":
                return self._validate_currency(app_normalized, doc_normalized, field_name, tolerance)
            elif validation_type == "date":
                return self._validate_date(app_normalized, doc_normalized, field_name)
            elif validation_type == "number":
                return self._validate_number(app_normalized, doc_normalized, field_name, tolerance)
            else:
                return self._validate_text(app_normalized, doc_normalized, field_name, tolerance)
                
        except Exception as e:
            logger.error(f"Error comparing values: {str(e)}")
            return {
                "validation_status": "mismatch",
                "mismatch_type": "comparison_error",
                "mismatch_severity": "critical",
                "discrepancy_percentage": None,
                "flag_for_review": True,
                "validation_notes": f"Comparison error: {str(e)}"
            }
    
    def _normalize_value(self, value: str, value_type: str) -> str:
        """Normalize value for comparison"""
        try:
            if not value:
                return ""
            
            normalized = str(value).strip()
            
            if value_type == "currency":
                # Remove currency symbols and commas
                normalized = re.sub(r'[^\d.-]', '', normalized)
            elif value_type == "date":
                # Standardize date format
                normalized = self._normalize_date(normalized)
            elif value_type == "number":
                # Remove commas and extra spaces
                normalized = re.sub(r'[^\d.-]', '', normalized)
            else:  # text
                # Convert to lowercase and remove extra spaces
                normalized = re.sub(r'\s+', ' ', normalized.lower())
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing value: {str(e)}")
            return str(value).strip()
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date string to YYYY-MM-DD format"""
        try:
            # Common date formats
            date_patterns = [
                r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY or DD/MM/YYYY
                r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
                r'(\d{1,2})-(\d{1,2})-(\d{4})',  # MM-DD-YYYY or DD-MM-YYYY
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, date_str)
                if match:
                    groups = match.groups()
                    if len(groups) == 3:
                        # Try to determine format based on first number
                        if len(groups[0]) == 4:  # YYYY-MM-DD
                            return f"{groups[0]}-{groups[1].zfill(2)}-{groups[2].zfill(2)}"
                        elif int(groups[0]) > 12:  # DD/MM/YYYY
                            return f"{groups[2]}-{groups[1].zfill(2)}-{groups[0].zfill(2)}"
                        else:  # MM/DD/YYYY
                            return f"{groups[2]}-{groups[0].zfill(2)}-{groups[1].zfill(2)}"
            
            return date_str
            
        except Exception as e:
            logger.error(f"Error normalizing date: {str(e)}")
            return date_str
    
    def _validate_text(self, app_value: str, doc_value: str, field_name: str, tolerance: float) -> Dict[str, Any]:
        """Validate text fields"""
        try:
            similarity = SequenceMatcher(None, app_value, doc_value).ratio()
            
            if similarity >= tolerance:
                return {
                    "validation_status": "validated",
                    "mismatch_type": None,
                    "mismatch_severity": None,
                    "discrepancy_percentage": (1 - similarity) * 100,
                    "flag_for_review": False,
                    "validation_notes": f"Text similarity: {similarity:.2f}"
                }
            else:
                severity = self._get_text_mismatch_severity(similarity, field_name)
                return {
                    "validation_status": "mismatch",
                    "mismatch_type": "value_difference",
                    "mismatch_severity": severity,
                    "discrepancy_percentage": (1 - similarity) * 100,
                    "flag_for_review": severity in ["critical", "high"],
                    "validation_notes": f"Text similarity below threshold: {similarity:.2f} < {tolerance}"
                }
                
        except Exception as e:
            logger.error(f"Error validating text: {str(e)}")
            return {
                "validation_status": "mismatch",
                "mismatch_type": "validation_error",
                "mismatch_severity": "critical",
                "discrepancy_percentage": None,
                "flag_for_review": True,
                "validation_notes": f"Text validation error: {str(e)}"
            }
    
    def _validate_currency(self, app_value: str, doc_value: str, field_name: str, tolerance: float) -> Dict[str, Any]:
        """Validate currency fields"""
        try:
            app_amount = self._parse_currency(app_value)
            doc_amount = self._parse_currency(doc_value)
            
            if app_amount is None or doc_amount is None:
                return {
                    "validation_status": "mismatch",
                    "mismatch_type": "format_difference",
                    "mismatch_severity": "medium",
                    "discrepancy_percentage": None,
                    "flag_for_review": True,
                    "validation_notes": "Unable to parse currency values"
                }
            
            if app_amount == 0 and doc_amount == 0:
                return {
                    "validation_status": "validated",
                    "mismatch_type": None,
                    "mismatch_severity": None,
                    "discrepancy_percentage": 0.0,
                    "flag_for_review": False,
                    "validation_notes": "Both values are zero"
                }
            
            # Calculate percentage difference
            max_amount = max(abs(app_amount), abs(doc_amount))
            percentage_diff = abs(app_amount - doc_amount) / max_amount
            
            if percentage_diff <= tolerance:
                return {
                    "validation_status": "validated",
                    "mismatch_type": None,
                    "mismatch_severity": None,
                    "discrepancy_percentage": percentage_diff * 100,
                    "flag_for_review": False,
                    "validation_notes": f"Currency difference within tolerance: {percentage_diff:.2%}"
                }
            else:
                severity = self._get_currency_mismatch_severity(percentage_diff, field_name)
                return {
                    "validation_status": "mismatch",
                    "mismatch_type": "value_difference",
                    "mismatch_severity": severity,
                    "discrepancy_percentage": percentage_diff * 100,
                    "flag_for_review": severity in ["critical", "high"],
                    "validation_notes": f"Currency difference exceeds tolerance: {percentage_diff:.2%} > {tolerance:.2%}"
                }
                
        except Exception as e:
            logger.error(f"Error validating currency: {str(e)}")
            return {
                "validation_status": "mismatch",
                "mismatch_type": "validation_error",
                "mismatch_severity": "critical",
                "discrepancy_percentage": None,
                "flag_for_review": True,
                "validation_notes": f"Currency validation error: {str(e)}"
            }
    
    def _validate_date(self, app_value: str, doc_value: str, field_name: str) -> Dict[str, Any]:
        """Validate date fields"""
        try:
            if app_value == doc_value:
                return {
                    "validation_status": "validated",
                    "mismatch_type": None,
                    "mismatch_severity": None,
                    "discrepancy_percentage": 0.0,
                    "flag_for_review": False,
                    "validation_notes": "Dates match exactly"
                }
            else:
                return {
                    "validation_status": "mismatch",
                    "mismatch_type": "value_difference",
                    "mismatch_severity": "high",
                    "discrepancy_percentage": 100.0,
                    "flag_for_review": True,
                    "validation_notes": f"Date mismatch: {app_value} vs {doc_value}"
                }
                
        except Exception as e:
            logger.error(f"Error validating date: {str(e)}")
            return {
                "validation_status": "mismatch",
                "mismatch_type": "validation_error",
                "mismatch_severity": "critical",
                "discrepancy_percentage": None,
                "flag_for_review": True,
                "validation_notes": f"Date validation error: {str(e)}"
            }
    
    def _validate_number(self, app_value: str, doc_value: str, field_name: str, tolerance: float) -> Dict[str, Any]:
        """Validate number fields"""
        try:
            app_num = self._parse_number(app_value)
            doc_num = self._parse_number(doc_value)
            
            if app_num is None or doc_num is None:
                return {
                    "validation_status": "mismatch",
                    "mismatch_type": "format_difference",
                    "mismatch_severity": "medium",
                    "discrepancy_percentage": None,
                    "flag_for_review": True,
                    "validation_notes": "Unable to parse number values"
                }
            
            if app_num == doc_num:
                return {
                    "validation_status": "validated",
                    "mismatch_type": None,
                    "mismatch_severity": None,
                    "discrepancy_percentage": 0.0,
                    "flag_for_review": False,
                    "validation_notes": "Numbers match exactly"
                }
            
            # Calculate percentage difference
            max_num = max(abs(app_num), abs(doc_num))
            if max_num == 0:
                return {
                    "validation_status": "validated",
                    "mismatch_type": None,
                    "mismatch_severity": None,
                    "discrepancy_percentage": 0.0,
                    "flag_for_review": False,
                    "validation_notes": "Both values are zero"
                }
            
            percentage_diff = abs(app_num - doc_num) / max_num
            
            if percentage_diff <= tolerance:
                return {
                    "validation_status": "validated",
                    "mismatch_type": None,
                    "mismatch_severity": None,
                    "discrepancy_percentage": percentage_diff * 100,
                    "flag_for_review": False,
                    "validation_notes": f"Number difference within tolerance: {percentage_diff:.2%}"
                }
            else:
                severity = self._get_number_mismatch_severity(percentage_diff, field_name)
                return {
                    "validation_status": "mismatch",
                    "mismatch_type": "value_difference",
                    "mismatch_severity": severity,
                    "discrepancy_percentage": percentage_diff * 100,
                    "flag_for_review": severity in ["critical", "high"],
                    "validation_notes": f"Number difference exceeds tolerance: {percentage_diff:.2%} > {tolerance:.2%}"
                }
                
        except Exception as e:
            logger.error(f"Error validating number: {str(e)}")
            return {
                "validation_status": "mismatch",
                "mismatch_type": "validation_error",
                "mismatch_severity": "critical",
                "discrepancy_percentage": None,
                "flag_for_review": True,
                "validation_notes": f"Number validation error: {str(e)}"
            }
    
    def _parse_currency(self, value: str) -> Optional[float]:
        """Parse currency value to float"""
        try:
            if not value:
                return None
            
            # Remove currency symbols and commas
            cleaned = re.sub(r'[^\d.-]', '', value)
            return float(cleaned) if cleaned else None
            
        except (ValueError, TypeError):
            return None
    
    def _parse_number(self, value: str) -> Optional[float]:
        """Parse number value to float"""
        try:
            if not value:
                return None
            
            # Remove commas and extra spaces
            cleaned = re.sub(r'[^\d.-]', '', value)
            return float(cleaned) if cleaned else None
            
        except (ValueError, TypeError):
            return None
    
    def _calculate_similarity(self, value1: str, value2: str) -> float:
        """Calculate similarity between two values"""
        try:
            if not value1 or not value2:
                return 0.0
            
            return SequenceMatcher(None, value1.lower(), value2.lower()).ratio()
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0
    
    def _get_missing_severity(self, field_name: str, field_config: Dict[str, Any]) -> str:
        """Get severity for missing document data"""
        critical_fields = field_config.get("critical_fields", [])
        if field_name in critical_fields:
            return "critical"
        elif field_name in field_config.get("important_fields", []):
            return "high"
        else:
            return "medium"
    
    def _get_text_mismatch_severity(self, similarity: float, field_name: str) -> str:
        """Get severity for text mismatch"""
        if similarity < 0.3:
            return "critical"
        elif similarity < 0.6:
            return "high"
        elif similarity < 0.8:
            return "medium"
        else:
            return "low"
    
    def _get_currency_mismatch_severity(self, percentage_diff: float, field_name: str) -> str:
        """Get severity for currency mismatch"""
        if percentage_diff > 0.2:  # > 20%
            return "critical"
        elif percentage_diff > 0.1:  # > 10%
            return "high"
        elif percentage_diff > 0.05:  # > 5%
            return "medium"
        else:
            return "low"
    
    def _get_number_mismatch_severity(self, percentage_diff: float, field_name: str) -> str:
        """Get severity for number mismatch"""
        if percentage_diff > 0.15:  # > 15%
            return "critical"
        elif percentage_diff > 0.08:  # > 8%
            return "high"
        elif percentage_diff > 0.03:  # > 3%
            return "medium"
        else:
            return "low"
    
    def _calculate_validation_summary(
        self, 
        validation_results: List[Dict[str, Any]], 
        total_fields: int, 
        validated_fields: int, 
        mismatch_fields: int, 
        missing_fields: int
    ) -> Dict[str, Any]:
        """Calculate validation summary"""
        try:
            # Count by severity
            severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            flagged_count = 0
            
            for result in validation_results:
                if result.get("mismatch_severity"):
                    severity_counts[result["mismatch_severity"]] += 1
                if result.get("flag_for_review"):
                    flagged_count += 1
            
            # Calculate percentages
            validation_percentage = (validated_fields / total_fields * 100) if total_fields > 0 else 0
            mismatch_percentage = (mismatch_fields / total_fields * 100) if total_fields > 0 else 0
            missing_percentage = (missing_fields / total_fields * 100) if total_fields > 0 else 0
            
            return {
                "total_fields": total_fields,
                "validated_fields": validated_fields,
                "mismatch_fields": mismatch_fields,
                "missing_fields": missing_fields,
                "flagged_for_review": flagged_count,
                "validation_percentage": validation_percentage,
                "mismatch_percentage": mismatch_percentage,
                "missing_percentage": missing_percentage,
                "severity_counts": severity_counts,
                "validation_completion_percentage": validation_percentage,
                "overall_status": "completed" if validation_percentage >= 80 else "needs_review"
            }
            
        except Exception as e:
            logger.error(f"Error calculating validation summary: {str(e)}")
            return {
                "total_fields": total_fields,
                "validated_fields": validated_fields,
                "mismatch_fields": mismatch_fields,
                "missing_fields": missing_fields,
                "flagged_for_review": 0,
                "validation_percentage": 0,
                "mismatch_percentage": 0,
                "missing_percentage": 0,
                "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "validation_completion_percentage": 0,
                "overall_status": "error"
            }
    
    async def _store_validation_results(self, validation_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Store validation results in database"""
        stored_results = []
        
        try:
            for result in validation_results:
                stored_result = await self.db_service.create_validation_result(result)
                stored_results.append(stored_result)
            
            return stored_results
            
        except Exception as e:
            logger.error(f"Error storing validation results: {str(e)}")
            return stored_results
    
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
                "agent_name": "validation",
                "step_name": step_name,
                "status": status,
                "message": message,
                "processing_time_ms": processing_time_ms,
                "error_details": error_details
            }
            await self.db_service.create_processing_log(log_data)
        except Exception as e:
            logger.error(f"Failed to log processing step: {str(e)}")
    
    async def get_validation_status(self, application_id: str) -> Dict[str, Any]:
        """Get validation status for an application"""
        try:
            validation_results = await self.db_service.get_validation_results_by_application(application_id)
            
            total_results = len(validation_results)
            validated_count = len([r for r in validation_results if r["validation_status"] == "validated"])
            mismatch_count = len([r for r in validation_results if r["validation_status"] == "mismatch"])
            missing_count = len([r for r in validation_results if r["validation_status"] == "missing"])
            flagged_count = len([r for r in validation_results if r["flag_for_review"]])
            
            # Group by severity
            severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for result in validation_results:
                if result.get("mismatch_severity"):
                    severity_counts[result["mismatch_severity"]] += 1
            
            return {
                "application_id": application_id,
                "total_results": total_results,
                "validated_count": validated_count,
                "mismatch_count": mismatch_count,
                "missing_count": missing_count,
                "flagged_count": flagged_count,
                "severity_counts": severity_counts,
                "validation_completion_percentage": (validated_count / total_results * 100) if total_results > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get validation status: {str(e)}")
            return {
                "application_id": application_id,
                "error": str(e)
            }
