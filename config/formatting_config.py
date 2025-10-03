"""
Formatting Configuration
Defines formatting rules and data transformation configurations
"""

from typing import Dict, List, Any

class FormattingConfig:
    """Configuration for data formatting"""
    
    def __init__(self):
        self.field_formatters = self._initialize_field_formatters()
        self.data_sources = self._initialize_data_sources()
        self.conflict_resolution_rules = self._initialize_conflict_resolution_rules()
    
    def _initialize_field_formatters(self) -> Dict[str, Dict[str, Any]]:
        """Initialize field formatting configurations"""
        return {
            "APPLICANT_FIRST_NAME": {
                "format_type": "text",
                "transform": "title_case",
                "max_length": 50,
                "required": True
            },
            "APPLICANT_LAST_NAME": {
                "format_type": "text",
                "transform": "title_case",
                "max_length": 50,
                "required": True
            },
            "APPLICANT_DOB": {
                "format_type": "date",
                "transform": "iso_date",
                "required": True
            },
            "APPLICANT_SIN": {
                "format_type": "text",
                "transform": "clean_sin",
                "pattern": r"^\d{3}-\d{3}-\d{3}$",
                "required": True
            },
            "APPLICANT_ADDRESS": {
                "format_type": "text",
                "transform": "title_case",
                "max_length": 200,
                "required": True
            },
            "APPLICANT_PHONE": {
                "format_type": "phone",
                "transform": "standard_phone",
                "pattern": r"^\(\d{3}\) \d{3}-\d{4}$",
                "required": False
            },
            "APPLICANT_EMAIL": {
                "format_type": "email",
                "transform": "lowercase",
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                "required": False
            },
            "ANNUAL_INCOME": {
                "format_type": "currency",
                "transform": "currency_format",
                "decimal_places": 2,
                "required": True
            },
            "EMPLOYMENT_STATUS": {
                "format_type": "text",
                "transform": "standardize_employment",
                "allowed_values": ["employed", "self_employed", "unemployed", "retired", "student"],
                "required": True
            },
            "EMPLOYER_NAME": {
                "format_type": "text",
                "transform": "title_case",
                "max_length": 100,
                "required": False
            },
            "COAPP_FIRST_NAME": {
                "format_type": "text",
                "transform": "title_case",
                "max_length": 50,
                "required": False
            },
            "COAPP_LAST_NAME": {
                "format_type": "text",
                "transform": "title_case",
                "max_length": 50,
                "required": False
            },
            "COAPP_DOB": {
                "format_type": "date",
                "transform": "iso_date",
                "required": False
            },
            "COAPP_SIN": {
                "format_type": "text",
                "transform": "clean_sin",
                "pattern": r"^\d{3}-\d{3}-\d{3}$",
                "required": False
            },
            "COAPP_ANNUAL_INCOME": {
                "format_type": "currency",
                "transform": "currency_format",
                "decimal_places": 2,
                "required": False
            },
            "ACCOUNT_HOLDER": {
                "format_type": "text",
                "transform": "title_case",
                "max_length": 100,
                "required": False
            },
            "ACCOUNT_NUMBER": {
                "format_type": "text",
                "transform": "mask_account",
                "required": False
            },
            "BEGINNING_BALANCE": {
                "format_type": "currency",
                "transform": "currency_format",
                "decimal_places": 2,
                "required": False
            },
            "ENDING_BALANCE": {
                "format_type": "currency",
                "transform": "currency_format",
                "decimal_places": 2,
                "required": False
            },
            "CREDIT_SCORE": {
                "format_type": "number",
                "transform": "integer",
                "min_value": 300,
                "max_value": 850,
                "required": False
            },
            "ASSESSED_VALUE": {
                "format_type": "currency",
                "transform": "currency_format",
                "decimal_places": 2,
                "required": False
            }
        }
    
    def _initialize_data_sources(self) -> Dict[str, Dict[str, Any]]:
        """Initialize data source configurations"""
        return {
            "application_form": {
                "priority": 1,
                "description": "Data from application form",
                "reliability": 0.9,
                "use_case": "primary_source"
            },
            "document_extraction": {
                "priority": 2,
                "description": "Data extracted from documents",
                "reliability": 0.8,
                "use_case": "verification"
            },
            "manual_input": {
                "priority": 3,
                "description": "Manually input data",
                "reliability": 0.7,
                "use_case": "correction"
            }
        }
    
    def _initialize_conflict_resolution_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize data comparison and validation rules"""
        return {
            "exact_match_required": {
                "fields": ["APPLICANT_FIRST_NAME", "APPLICANT_LAST_NAME", "APPLICANT_DOB", "APPLICANT_SIN"],
                "rule": "exact_match",
                "reason": "Critical personal information must match exactly",
                "tolerance": "exact"
            },
            "financial_tolerance": {
                "fields": ["ANNUAL_INCOME", "CREDIT_SCORE", "BANK_BALANCE", "PROPERTY_VALUE"],
                "rule": "percentage_tolerance",
                "reason": "Financial data allows small percentage differences",
                "tolerance": 0.05
            },
            "text_similarity": {
                "fields": ["APPLICANT_ADDRESS", "EMPLOYER_NAME", "EMPLOYMENT_STATUS"],
                "rule": "similarity_match",
                "reason": "Text fields allow similarity-based matching",
                "tolerance": 0.8
            },
            "contact_info": {
                "fields": ["APPLICANT_PHONE", "APPLICANT_EMAIL"],
                "rule": "format_match",
                "reason": "Contact information must match format and content",
                "tolerance": 0.9
            }
        }
    
    def get_field_formatter(self, field_name: str) -> Dict[str, Any]:
        """Get field formatter configuration"""
        return self.field_formatters.get(field_name, {
            "format_type": "text",
            "transform": "none",
            "required": False
        })
    
    def get_data_source_config(self, data_source: str) -> Dict[str, Any]:
        """Get data source configuration"""
        return self.data_sources.get(data_source, {
            "priority": 3,
            "description": "Unknown data source",
            "reliability": 0.5,
            "use_case": "unknown"
        })
    
    def get_conflict_resolution_rule(self, field_name: str) -> Dict[str, Any]:
        """Get conflict resolution rule for field"""
        for rule_name, rule_config in self.conflict_resolution_rules.items():
            if field_name in rule_config["fields"]:
                return rule_config
        return {
            "rule": "prefer_higher_confidence",
            "reason": "Default to highest confidence source"
        }
    
    def get_format_type_for_field(self, field_name: str) -> str:
        """Get format type for field"""
        config = self.get_field_formatter(field_name)
        return config.get("format_type", "text")
    
    def get_transform_for_field(self, field_name: str) -> str:
        """Get transform for field"""
        config = self.get_field_formatter(field_name)
        return config.get("transform", "none")
    
    def is_field_required(self, field_name: str) -> bool:
        """Check if field is required"""
        config = self.get_field_formatter(field_name)
        return config.get("required", False)
    
    def get_field_max_length(self, field_name: str) -> int:
        """Get maximum length for field"""
        config = self.get_field_formatter(field_name)
        return config.get("max_length", 255)
    
    def get_field_pattern(self, field_name: str) -> str:
        """Get validation pattern for field"""
        config = self.get_field_formatter(field_name)
        return config.get("pattern", "")
    
    def get_allowed_values(self, field_name: str) -> List[str]:
        """Get allowed values for field"""
        config = self.get_field_formatter(field_name)
        return config.get("allowed_values", [])
    
    def get_field_constraints(self, field_name: str) -> Dict[str, Any]:
        """Get field constraints"""
        config = self.get_field_formatter(field_name)
        constraints = {}
        
        if "min_value" in config:
            constraints["min_value"] = config["min_value"]
        if "max_value" in config:
            constraints["max_value"] = config["max_value"]
        if "decimal_places" in config:
            constraints["decimal_places"] = config["decimal_places"]
        
        return constraints
    
    def get_required_fields(self) -> List[str]:
        """Get list of required fields"""
        required_fields = []
        for field_name, config in self.field_formatters.items():
            if config.get("required", False):
                required_fields.append(field_name)
        return required_fields
    
    def get_critical_fields(self) -> List[str]:
        """Get list of critical fields (required + high priority)"""
        critical_fields = []
        for field_name, config in self.field_formatters.items():
            if config.get("required", False) or config.get("format_type") in ["currency", "date"]:
                critical_fields.append(field_name)
        return critical_fields
