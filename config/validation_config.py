"""
Validation Configuration
Defines validation rules and field configurations for data validation
"""

from typing import Dict, List, Any

class ValidationConfig:
    """Configuration for data validation"""
    
    def __init__(self):
        self.field_configs = self._initialize_field_configs()
        self.validation_rules = self._initialize_validation_rules()
        self.severity_levels = self._initialize_severity_levels()
    
    def _initialize_field_configs(self) -> Dict[str, Dict[str, Any]]:
        """Initialize field validation configurations"""
        return {
            "APPLICANT_FIRST_NAME": {
                "validation_type": "text",
                "tolerance": 0.8,
                "critical_field": False,
                "similarity_threshold": 0.7
            },
            "APPLICANT_LAST_NAME": {
                "validation_type": "text",
                "tolerance": 0.8,
                "critical_field": False,
                "similarity_threshold": 0.7
            },
            "APPLICANT_DOB": {
                "validation_type": "date",
                "tolerance": "exact",
                "critical_field": True,
                "similarity_threshold": 1.0
            },
            "APPLICANT_SIN": {
                "validation_type": "text",
                "tolerance": "exact",
                "critical_field": True,
                "similarity_threshold": 1.0
            },
            "APPLICANT_ADDRESS": {
                "validation_type": "text",
                "tolerance": 0.7,
                "critical_field": False,
                "similarity_threshold": 0.6
            },
            "APPLICANT_PHONE": {
                "validation_type": "text",
                "tolerance": 0.8,
                "critical_field": False,
                "similarity_threshold": 0.7
            },
            "APPLICANT_EMAIL": {
                "validation_type": "text",
                "tolerance": 0.9,
                "critical_field": False,
                "similarity_threshold": 0.8
            },
            "ANNUAL_INCOME": {
                "validation_type": "currency",
                "tolerance": 0.05,  # 5%
                "critical_field": True,
                "similarity_threshold": 0.8
            },
            "EMPLOYMENT_STATUS": {
                "validation_type": "text",
                "tolerance": 0.8,
                "critical_field": False,
                "similarity_threshold": 0.7
            },
            "EMPLOYER_NAME": {
                "validation_type": "text",
                "tolerance": 0.7,
                "critical_field": False,
                "similarity_threshold": 0.6
            },
            "COAPP_FIRST_NAME": {
                "validation_type": "text",
                "tolerance": 0.8,
                "critical_field": False,
                "similarity_threshold": 0.7
            },
            "COAPP_LAST_NAME": {
                "validation_type": "text",
                "tolerance": 0.8,
                "critical_field": False,
                "similarity_threshold": 0.7
            },
            "COAPP_DOB": {
                "validation_type": "date",
                "tolerance": "exact",
                "critical_field": True,
                "similarity_threshold": 1.0
            },
            "COAPP_SIN": {
                "validation_type": "text",
                "tolerance": "exact",
                "critical_field": True,
                "similarity_threshold": 1.0
            },
            "COAPP_ANNUAL_INCOME": {
                "validation_type": "currency",
                "tolerance": 0.05,  # 5%
                "critical_field": True,
                "similarity_threshold": 0.8
            },
            "ACCOUNT_HOLDER": {
                "validation_type": "text",
                "tolerance": 0.8,
                "critical_field": False,
                "similarity_threshold": 0.7
            },
            "ACCOUNT_NUMBER": {
                "validation_type": "text",
                "tolerance": 0.9,
                "critical_field": False,
                "similarity_threshold": 0.8
            },
            "BEGINNING_BALANCE": {
                "validation_type": "currency",
                "tolerance": 0.1,  # 10%
                "critical_field": False,
                "similarity_threshold": 0.7
            },
            "ENDING_BALANCE": {
                "validation_type": "currency",
                "tolerance": 0.1,  # 10%
                "critical_field": False,
                "similarity_threshold": 0.7
            },
            "CREDIT_SCORE": {
                "validation_type": "number",
                "tolerance": 0.05,  # 5%
                "critical_field": True,
                "similarity_threshold": 0.8
            },
            "ASSESSED_VALUE": {
                "validation_type": "currency",
                "tolerance": 0.1,  # 10%
                "critical_field": False,
                "similarity_threshold": 0.7
            }
        }
    
    def _initialize_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize validation rules by type"""
        return {
            "text": {
                "method": "fuzzy_match",
                "default_tolerance": 0.8,
                "critical_fields": ["APPLICANT_SIN", "COAPP_SIN"],
                "critical_tolerance": "exact"
            },
            "currency": {
                "method": "percentage_difference",
                "default_tolerance": 0.05,  # 5%
                "critical_fields": ["ANNUAL_INCOME", "COAPP_ANNUAL_INCOME"],
                "critical_tolerance": 0.02  # 2% for salary
            },
            "date": {
                "method": "exact_match",
                "default_tolerance": "exact",
                "critical_fields": ["APPLICANT_DOB", "COAPP_DOB"],
                "critical_tolerance": "exact"
            },
            "number": {
                "method": "percentage_difference",
                "default_tolerance": 0.05,  # 5%
                "critical_fields": ["CREDIT_SCORE"],
                "critical_tolerance": 0.02  # 2% for critical numbers
            }
        }
    
    def _initialize_severity_levels(self) -> Dict[str, Dict[str, Any]]:
        """Initialize mismatch severity levels"""
        return {
            "critical": {
                "description": "Critical data mismatch - requires immediate attention",
                "color": "red",
                "priority": 1,
                "threshold": 0.0
            },
            "high": {
                "description": "High priority mismatch - significant difference",
                "color": "orange", 
                "priority": 2,
                "threshold": 0.2
            },
            "medium": {
                "description": "Medium priority mismatch - moderate difference",
                "color": "yellow",
                "priority": 3,
                "threshold": 0.5
            },
            "low": {
                "description": "Low priority mismatch - minor difference",
                "color": "blue",
                "priority": 4,
                "threshold": 0.8
            }
        }
    
    def get_field_config(self, field_name: str) -> Dict[str, Any]:
        """Get field configuration"""
        return self.field_configs.get(field_name, {
            "validation_type": "text",
            "tolerance": 0.8,
            "critical_field": False,
            "similarity_threshold": 0.7
        })
    
    def get_validation_rules(self, validation_type: str) -> Dict[str, Any]:
        """Get validation rules for a type"""
        return self.validation_rules.get(validation_type, self.validation_rules["text"])
    
    def get_severity_level(self, severity: str) -> Dict[str, Any]:
        """Get severity level configuration"""
        return self.severity_levels.get(severity, self.severity_levels["medium"])
    
    def is_critical_field(self, field_name: str) -> bool:
        """Check if field is critical"""
        config = self.get_field_config(field_name)
        return config.get("critical_field", False)
    
    def get_tolerance_for_field(self, field_name: str) -> float:
        """Get tolerance for field validation"""
        config = self.get_field_config(field_name)
        tolerance = config.get("tolerance", 0.8)
        
        if tolerance == "exact":
            return 1.0
        elif isinstance(tolerance, (int, float)):
            return tolerance
        else:
            return 0.8
    
    def get_similarity_threshold_for_field(self, field_name: str) -> float:
        """Get similarity threshold for field"""
        config = self.get_field_config(field_name)
        return config.get("similarity_threshold", 0.7)
    
    def get_validation_type_for_field(self, field_name: str) -> str:
        """Get validation type for field"""
        config = self.get_field_config(field_name)
        return config.get("validation_type", "text")
    
    def get_critical_fields(self) -> List[str]:
        """Get list of critical fields"""
        critical_fields = []
        for field_name, config in self.field_configs.items():
            if config.get("critical_field", False):
                critical_fields.append(field_name)
        return critical_fields
    
    def get_important_fields(self) -> List[str]:
        """Get list of important fields (non-critical but significant)"""
        important_fields = []
        for field_name, config in self.field_configs.items():
            if not config.get("critical_field", False) and config.get("validation_type") in ["currency", "date"]:
                important_fields.append(field_name)
        return important_fields
    
    def get_field_priority(self, field_name: str) -> int:
        """Get priority for field validation"""
        config = self.get_field_config(field_name)
        if config.get("critical_field", False):
            return 1
        elif config.get("validation_type") in ["currency", "date"]:
            return 2
        else:
            return 3
