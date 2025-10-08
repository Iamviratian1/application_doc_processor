"""
Golden Data Model
Represents the final validated data from the Data Validation Agent
"""

from sqlalchemy import Column, String, DateTime, Numeric, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid
from typing import Optional, Dict, Any

Base = declarative_base()

class GoldenData(Base):
    __tablename__ = "golden_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(String(255), ForeignKey("applications.application_id"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False, index=True)
    field_value = Column(Text, nullable=False)
    field_type = Column(String(50), nullable=False)
    data_source = Column(String(100), nullable=False)  # 'application_form', 'document_extraction', 'manual_input'
    source_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"))
    validation_status = Column(String(20), nullable=False, index=True)
    confidence_score = Column(Numeric(3, 2))
    is_verified = Column(Boolean, default=False)
    verification_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    agent_version = Column(String(20), default='1.0')
    
    def __repr__(self):
        return f"<GoldenData(field='{self.field_name}', value='{self.field_value}', source='{self.data_source}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'application_id': self.application_id,
            'field_name': self.field_name,
            'field_value': self.field_value,
            'field_type': self.field_type,
            'data_source': self.data_source,
            'source_document_id': str(self.source_document_id) if self.source_document_id else None,
            'validation_status': self.validation_status,
            'confidence_score': float(self.confidence_score) if self.confidence_score else None,
            'is_verified': self.is_verified,
            'verification_notes': self.verification_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'agent_version': self.agent_version
        }
    
    def is_verified(self) -> bool:
        """Check if data is verified"""
        return self.is_verified
    
    def is_high_confidence(self) -> bool:
        """Check if data has high confidence"""
        return self.confidence_score and self.confidence_score >= 0.8
    
    def is_from_application(self) -> bool:
        """Check if data comes from application form"""
        return self.data_source == 'application_form'
    
    def is_from_document(self) -> bool:
        """Check if data comes from document extraction"""
        return self.data_source == 'document_extraction'
    
    def is_manually_input(self) -> bool:
        """Check if data was manually input"""
        return self.data_source == 'manual_input'
    
    def get_data_source_display(self) -> str:
        """Get human-readable data source"""
        source_map = {
            'application_form': 'Application Form',
            'document_extraction': 'Document Extraction',
            'manual_input': 'Manual Input'
        }
        return source_map.get(self.data_source, 'Unknown')
    
    def get_field_type_display(self) -> str:
        """Get human-readable field type"""
        type_map = {
            'text': 'Text',
            'currency': 'Currency',
            'date': 'Date',
            'number': 'Number',
            'percentage': 'Percentage',
            'boolean': 'Boolean'
        }
        return type_map.get(self.field_type, 'Unknown')
    
    def get_validation_status_display(self) -> str:
        """Get human-readable validation status"""
        status_map = {
            'validated': 'Validated',
            'mismatch': 'Mismatch',
            'missing': 'Missing',
            'pending': 'Pending'
        }
        return status_map.get(self.validation_status, 'Unknown')
    
    def get_confidence_level(self) -> str:
        """Get confidence level as string"""
        if not self.confidence_score:
            return 'unknown'
        elif self.confidence_score >= 0.8:
            return 'high'
        elif self.confidence_score >= 0.5:
            return 'medium'
        else:
            return 'low'
