"""
Document Model
Represents a raw document uploaded for processing
"""

from sqlalchemy import Column, String, DateTime, Numeric, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid
from typing import Optional, Dict, Any

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(String(255), ForeignKey("applications.application_id"), nullable=False, index=True)
    document_id = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    document_type = Column(String(100), nullable=False)
    applicant_type = Column(String(20), nullable=False, default='applicant')
    file_size = Column(BigInteger)
    mime_type = Column(String(100))
    storage_path = Column(String(500))
    upload_status = Column(String(50), default='uploaded')
    processing_status = Column(String(50), default='pending')
    confidence = Column(Numeric(3, 2), default=0.0)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    meta_data = Column(JSONB, default={})
    
    def __repr__(self):
        return f"<Document(document_id='{self.document_id}', type='{self.document_type}', status='{self.processing_status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'application_id': self.application_id,
            'document_id': self.document_id,
            'filename': self.filename,
            'document_type': self.document_type,
            'applicant_type': self.applicant_type,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'storage_path': self.storage_path,
            'upload_status': self.upload_status,
            'processing_status': self.processing_status,
            'confidence': float(self.confidence) if self.confidence else 0.0,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'metadata': self.meta_data
        }
    
    def is_processed(self) -> bool:
        """Check if document has been processed"""
        return self.processing_status == 'completed'
    
    def is_ready_for_processing(self) -> bool:
        """Check if document is ready for processing"""
        return self.upload_status == 'uploaded' and self.processing_status == 'pending'
    
    def get_processing_status_display(self) -> str:
        """Get human-readable processing status"""
        status_map = {
            'pending': 'Pending Processing',
            'processing': 'Processing',
            'completed': 'Completed',
            'failed': 'Failed',
            'skipped': 'Skipped'
        }
        return status_map.get(self.processing_status, 'Unknown')
