"""
YAML Configuration Loader
Loads document processing configuration from YAML files
"""

import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path

class YAMLConfigLoader:
    """Loads configuration from YAML files"""
    
    def __init__(self, config_file: str = "documents.yaml"):
        self.config_file = config_file
        self.config_path = Path(__file__).parent / config_file
        self.field_mapping_path = Path(__file__).parent / "field_mapping.yaml"
        self._config = None
        self._field_mapping_config = None
        self._load_config()
        self._load_field_mapping()
    
    def _load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self._config = yaml.safe_load(file)
        except FileNotFoundError:
            raise Exception(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise Exception(f"Error parsing YAML configuration: {str(e)}")
    
    def _load_field_mapping(self):
        """Load field mapping configuration from YAML file"""
        try:
            with open(self.field_mapping_path, 'r', encoding='utf-8') as file:
                self._field_mapping_config = yaml.safe_load(file)
        except FileNotFoundError:
            # Field mapping is optional, set to empty dict if not found
            self._field_mapping_config = {}
        except yaml.YAMLError as e:
            raise Exception(f"Error parsing field mapping configuration: {str(e)}")
    
    def get_document_types(self) -> Dict[str, Dict[str, Any]]:
        """Get document types configuration"""
        return self._config.get("documents", {})
    
    def get_field_extraction_config(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get field extraction configuration"""
        return self._config.get("documents", {})
    
    def get_field_mapping_config(self) -> Dict[str, Dict[str, Any]]:
        """Get field mapping configuration"""
        return self._field_mapping_config.get("field_mapping", {})
    
    def get_validation_rules(self) -> Dict[str, Any]:
        """Get validation rules"""
        return self._field_mapping_config.get("validation_rules", {})
    
    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing configuration"""
        return self._config.get("processing", {})
    
    def get_document_type_info(self, document_type: str) -> Dict[str, Any]:
        """Get information about a specific document type"""
        document_types = self.get_document_types()
        return document_types.get(document_type, {})
    
    def get_queries_for_document_type(self, document_type: str, page_number: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get Textract queries for a document type, optionally filtered by page"""
        documents = self.get_document_types()
        document_config = documents.get(document_type, {})
        field_extraction = document_config.get("field_extraction", {})
        all_queries = field_extraction.get("queries", [])
        
        # Page-based processing is only supported for mortgage applications
        if page_number is None or document_type != "mortgage_application":
            return all_queries
        
        # Filter queries by page number based on 'page' field (only for mortgage applications)
        page_queries = []
        
        for query in all_queries:
            if isinstance(query, dict):
                # Check if query has a 'page' field matching the requested page
                query_page = query.get("page", 1)  # Default to page 1 if not specified
                if query_page == page_number:
                    page_queries.append(query)
        
        return page_queries
    
    def get_field_mapping_for_field(self, field_name: str) -> Dict[str, Any]:
        """Get field mapping for a specific field"""
        field_mapping = self.get_field_mapping_config()
        return field_mapping.get(field_name, {})
    
    def get_critical_fields(self) -> List[str]:
        """Get list of critical fields"""
        validation_rules = self.get_validation_rules()
        return validation_rules.get("critical_fields", [])
    
    def get_important_fields(self) -> List[str]:
        """Get list of important fields"""
        validation_rules = self.get_validation_rules()
        return validation_rules.get("important_fields", [])
    
    def get_field_type_config(self, field_type: str) -> Dict[str, Any]:
        """Get configuration for a field type"""
        validation_rules = self.get_validation_rules()
        field_types = validation_rules.get("field_types", {})
        return field_types.get(field_type, {})
    
    def get_processing_setting(self, setting_name: str, default_value: Any = None) -> Any:
        """Get a processing setting"""
        processing_config = self.get_processing_config()
        return processing_config.get(setting_name, default_value)
    
    def is_document_type_supported(self, document_type: str) -> bool:
        """Check if document type is supported"""
        document_types = self.get_document_types()
        return document_type in document_types
    
    def get_supported_formats_for_document_type(self, document_type: str) -> List[str]:
        """Get supported file formats for a document type"""
        doc_info = self.get_document_type_info(document_type)
        return doc_info.get("supported_formats", ["pdf", "png", "jpg", "jpeg"])
    
    def get_max_file_size_for_document_type(self, document_type: str) -> int:
        """Get maximum file size for a document type in bytes"""
        doc_info = self.get_document_type_info(document_type)
        max_size_mb = doc_info.get("max_file_size_mb", 10)
        return max_size_mb * 1024 * 1024  # Convert to bytes
    
    def get_document_priority(self, document_type: str) -> int:
        """Get priority for a document type"""
        doc_info = self.get_document_type_info(document_type)
        return doc_info.get("priority", 5)
    
    def is_document_mandatory(self, document_type: str) -> bool:
        """Check if document type is mandatory"""
        doc_info = self.get_document_type_info(document_type)
        return doc_info.get("mandatory", False)
    
    def get_mandatory_document_types(self) -> List[str]:
        """Get list of mandatory document types"""
        document_types = self.get_document_types()
        mandatory_docs = []
        for doc_type, config in document_types.items():
            if config.get("mandatory", False):
                mandatory_docs.append(doc_type)
        return mandatory_docs
    
    def reload_config(self):
        """Reload configuration from file"""
        self._load_config()
    
    def get_all_document_types(self) -> List[str]:
        """Get all supported document types"""
        document_types = self.get_document_types()
        return list(document_types.keys())
