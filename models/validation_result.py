"""
Validation Result Model
Represents validation results from the Data Validation Agent
"""

from sqlalchemy import Column, String, DateTime, Numeric, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid
from typing import Optional, Dict, Any

Base = declarative_base()

class ValidationResult(Base):
    __tablename__ = "validation_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(String(255), ForeignKey("applications.application_id"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False, index=True)
    application_value = Column(Text)
    document_value = Column(Text)
    document_type = Column(String(100))
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"))
    validation_status = Column(String(20), nullable=False, index=True)  # 'validated', 'mismatch', 'missing', 'pending'
    mismatch_type = Column(String(50))  # 'value_difference', 'format_difference', 'missing_document'
    mismatch_severity = Column(String(20), index=True)  # 'low', 'medium', 'high', 'critical'
    discrepancy_percentage = Column(Numeric(5, 2))
    confidence_score = Column(Numeric(3, 2))
    flag_for_review = Column(Boolean, default=False, index=True)
    validation_notes = Column(Text)
    validated_at = Column(DateTime(timezone=True), server_default=func.now())
    agent_version = Column(String(20), default='1.0')
    
    def __repr__(self):
        return f"<ValidationResult(field='{self.field_name}', status='{self.validation_status}', severity='{self.mismatch_severity}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'application_id': self.application_id,
            'field_name': self.field_name,
            'application_value': self.application_value,
            'document_value': self.document_value,
            'document_type': self.document_type,
            'document_id': str(self.document_id) if self.document_id else None,
            'validation_status': self.validation_status,
            'mismatch_type': self.mismatch_type,
            'mismatch_severity': self.mismatch_severity,
            'discrepancy_percentage': float(self.discrepancy_percentage) if self.discrepancy_percentage else None,
            'confidence_score': float(self.confidence_score) if self.confidence_score else None,
            'flag_for_review': self.flag_for_review,
            'validation_notes': self.validation_notes,
            'validated_at': self.validated_at.isoformat() if self.validated_at else None,
            'agent_version': self.agent_version
        }
    
    def is_validated(self) -> bool:
        """Check if validation passed"""
        return self.validation_status == 'validated'
    
    def has_mismatch(self) -> bool:
        """Check if there's a mismatch"""
        return self.validation_status == 'mismatch'
    
    def is_critical_mismatch(self) -> bool:
        """Check if mismatch is critical"""
        return self.mismatch_severity == 'critical'
    
    def is_high_priority_mismatch(self) -> bool:
        """Check if mismatch is high priority"""
        return self.mismatch_severity in ['critical', 'high']
    
    def get_status_color(self) -> str:
        """Get color code for status display"""
        color_map = {
            'validated': 'green',
            'mismatch': 'red',
            'missing': 'orange',
            'pending': 'yellow'
        }
        return color_map.get(self.validation_status, 'gray')
    
    def get_severity_color(self) -> str:
        """Get color code for severity display"""
        color_map = {
            'critical': 'red',
            'high': 'orange',
            'medium': 'yellow',
            'low': 'blue'
        }
        return color_map.get(self.mismatch_severity, 'gray')
    
    def get_status_display(self) -> str:
        """Get human-readable validation status"""
        status_map = {
            'validated': 'Validated',
            'mismatch': 'Mismatch Found',
            'missing': 'Missing Document',
            'pending': 'Pending Validation'
        }
        return status_map.get(self.validation_status, 'Unknown')
    
    def get_severity_display(self) -> str:
        """Get human-readable severity level"""
        severity_map = {
            'critical': 'Critical',
            'high': 'High',
            'medium': 'Medium',
            'low': 'Low'
        }
        return severity_map.get(self.mismatch_severity, 'Unknown')
