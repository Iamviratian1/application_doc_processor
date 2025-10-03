"""
Application Model
Represents a mortgage application with its processing status
"""

from sqlalchemy import Column, String, DateTime, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

Base = declarative_base()

class Application(Base):
    __tablename__ = "applications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(String(255), unique=True, nullable=False, index=True)
    applicant_name = Column(String(255))
    co_applicant_name = Column(String(255))
    application_type = Column(String(50), default='mortgage')
    status = Column(String(50), default='document_upload')
    completion_percentage = Column(Numeric(5, 2), default=0.00)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    meta_data = Column(JSONB, default={})
    
    def __repr__(self):
        return f"<Application(application_id='{self.application_id}', status='{self.status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'application_id': self.application_id,
            'applicant_name': self.applicant_name,
            'co_applicant_name': self.co_applicant_name,
            'application_type': self.application_type,
            'status': self.status,
            'completion_percentage': float(self.completion_percentage),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'metadata': self.meta_data
        }
    
    def is_complete(self) -> bool:
        """Check if application processing is complete"""
        return self.status == 'completed' and self.completion_percentage >= 100.0
    
    def get_processing_status(self) -> str:
        """Get human-readable processing status"""
        status_map = {
            'document_upload': 'Document Upload',
            'processing': 'Processing Documents',
            'validation': 'Validating Data',
            'formatting': 'Formatting Data',
            'completed': 'Completed',
            'failed': 'Failed'
        }
        return status_map.get(self.status, 'Unknown')
