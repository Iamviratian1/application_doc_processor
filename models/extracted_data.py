"""
Extracted Data Model
Represents data extracted from documents by the Data Extraction Agent
"""

from sqlalchemy import Column, String, DateTime, Numeric, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid
from typing import Optional, Dict, Any

Base = declarative_base()

class ExtractedData(Base):
    __tablename__ = "extracted_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    application_id = Column(String(255), ForeignKey("applications.application_id"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False, index=True)
    field_value = Column(Text)
    field_type = Column(String(50), nullable=False)  # 'text', 'currency', 'date', 'number'
    confidence = Column(Numeric(3, 2), nullable=False)
    extraction_method = Column(String(50), default='textract')
    raw_response = Column(JSONB)
    extracted_at = Column(DateTime(timezone=True), server_default=func.now())
    agent_version = Column(String(20), default='1.0')
    
    def __repr__(self):
        return f"<ExtractedData(field='{self.field_name}', value='{self.field_value}', confidence={self.confidence})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'document_id': str(self.document_id),
            'application_id': self.application_id,
            'field_name': self.field_name,
            'field_value': self.field_value,
            'field_type': self.field_type,
            'confidence': float(self.confidence),
            'extraction_method': self.extraction_method,
            'raw_response': self.raw_response,
            'extracted_at': self.extracted_at.isoformat() if self.extracted_at else None,
            'agent_version': self.agent_version
        }
    
    def is_high_confidence(self) -> bool:
        """Check if extraction has high confidence"""
        return self.confidence >= 0.8
    
    def is_medium_confidence(self) -> bool:
        """Check if extraction has medium confidence"""
        return 0.5 <= self.confidence < 0.8
    
    def is_low_confidence(self) -> bool:
        """Check if extraction has low confidence"""
        return self.confidence < 0.5
    
    def get_confidence_level(self) -> str:
        """Get confidence level as string"""
        if self.is_high_confidence():
            return 'high'
        elif self.is_medium_confidence():
            return 'medium'
        else:
            return 'low'
    
    def get_field_type_display(self) -> str:
        """Get human-readable field type"""
        type_map = {
            'text': 'Text',
            'currency': 'Currency',
            'date': 'Date',
            'number': 'Number',
            'percentage': 'Percentage'
        }
        return type_map.get(self.field_type, 'Unknown')
