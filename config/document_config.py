"""
Document Configuration
Defines document types, queries, and field mappings for AWS Textract
Uses YAML configuration for easy maintenance
"""

from typing import Dict, List, Any
from .yaml_config import YAMLConfigLoader

class DocumentConfig:
    """Configuration for document processing"""
    
    def __init__(self):
        self.yaml_loader = YAMLConfigLoader()
    
    def get_document_type_info(self, document_type: str) -> Dict[str, Any]:
        """Get information about a document type"""
        return self.yaml_loader.get_document_type_info(document_type)
    
    def get_queries_for_document_type(self, document_type: str, page_number: int = None) -> List[Dict[str, str]]:
        """Get Textract queries for a document type, optionally filtered by page (only for mortgage applications)"""
        queries = self.yaml_loader.get_queries_for_document_type(document_type, page_number)
        # Convert to the format expected by Textract
        textract_queries = []
        for query in queries:
            if isinstance(query, dict) and "text" in query and "alias" in query:
                textract_queries.append({
                    "Text": query["text"],
                    "Alias": query["alias"]
                })
        return textract_queries
    
    def get_page_count_for_document_type(self, document_type: str) -> int:
        """Get the number of pages for a document type (only for mortgage applications)"""
        # Page-based processing is only supported for mortgage applications
        if document_type != "mortgage_application":
            return 1
        
        queries = self.yaml_loader.get_queries_for_document_type(document_type)
        pages = set()
        
        for query in queries:
            if isinstance(query, str) and query.startswith("# PAGE"):
                try:
                    page_part = query.split(":")[0].split()[-1]
                    pages.add(int(page_part))
                except (ValueError, IndexError):
                    continue
        
        return len(pages) if pages else 1
    
    def get_field_mappings_for_document_type(self, document_type: str) -> Dict[str, str]:
        """Get field mappings for a document type"""
        queries = self.yaml_loader.get_queries_for_document_type(document_type)
        field_mappings = {}
        for query in queries:
            # Map field_name (from alias) to query_alias (for Textract results)
            field_mappings[query["alias"]] = query["alias"]
        return field_mappings
    
    def get_mandatory_documents_for_applicant(self, applicant_type: str = "applicant") -> List[str]:
        """Get list of mandatory document types for an applicant"""
        return self.yaml_loader.get_mandatory_document_types()
    
    def is_document_type_supported(self, document_type: str) -> bool:
        """Check if document type is supported"""
        return self.yaml_loader.is_document_type_supported(document_type)
    
    def get_all_document_types(self) -> List[str]:
        """Get all supported document types"""
        return self.yaml_loader.get_all_document_types()
    
    def get_document_priority(self, document_type: str) -> int:
        """Get priority for a document type"""
        return self.yaml_loader.get_document_priority(document_type)
    
    def get_supported_formats_for_document_type(self, document_type: str) -> List[str]:
        """Get supported file formats for a document type"""
        return self.yaml_loader.get_supported_formats_for_document_type(document_type)
    
    def get_max_file_size_for_document_type(self, document_type: str) -> int:
        """Get maximum file size for a document type in bytes"""
        return self.yaml_loader.get_max_file_size_for_document_type(document_type)
    
    def is_document_mandatory(self, document_type: str) -> bool:
        """Check if document type is mandatory"""
        return self.yaml_loader.is_document_mandatory(document_type)
    
    def get_field_validation_config(self, field_name: str) -> Dict[str, Any]:
        """Get validation configuration for a field"""
        queries = self.yaml_loader.get_field_extraction_config()
        for doc_type, doc_queries in queries.items():
            for query in doc_queries:
                if query["alias"] == field_name:
                    return {
                        "field_type": query["field_type"],
                        "required": query["required"],
                        "validation_tolerance": query["validation_tolerance"]
                    }
        return {
            "field_type": "text",
            "required": False,
            "validation_tolerance": 0.8
        }
    
    def get_critical_fields(self) -> List[str]:
        """Get list of critical fields"""
        return self.yaml_loader.get_critical_fields()
    
    def get_important_fields(self) -> List[str]:
        """Get list of important fields"""
        return self.yaml_loader.get_important_fields()
    
    def get_field_type_config(self, field_type: str) -> Dict[str, Any]:
        """Get configuration for a field type"""
        return self.yaml_loader.get_field_type_config(field_type)
    
    def reload_config(self):
        """Reload configuration from YAML file"""
        self.yaml_loader.reload_config()