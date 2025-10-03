"""
Document Job Model
Represents jobs in the processing queue
"""

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid
from typing import Optional, Dict, Any

Base = declarative_base()

class DocumentJob(Base):
    __tablename__ = "document_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(String(255), ForeignKey("applications.application_id"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    job_type = Column(String(50), nullable=False)  # 'ingestion', 'extraction', 'validation', 'formatting'
    status = Column(String(20), default='pending', index=True)  # 'pending', 'processing', 'completed', 'failed'
    priority = Column(Integer, default=5)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(String(500))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<DocumentJob(type='{self.job_type}', status='{self.status}', priority={self.priority})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'application_id': self.application_id,
            'document_id': str(self.document_id),
            'job_type': self.job_type,
            'status': self.status,
            'priority': self.priority,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def is_pending(self) -> bool:
        """Check if job is pending"""
        return self.status == 'pending'
    
    def is_processing(self) -> bool:
        """Check if job is processing"""
        return self.status == 'processing'
    
    def is_completed(self) -> bool:
        """Check if job is completed"""
        return self.status == 'completed'
    
    def is_failed(self) -> bool:
        """Check if job is failed"""
        return self.status == 'failed'
    
    def can_retry(self) -> bool:
        """Check if job can be retried"""
        return self.status == 'failed' and self.retry_count < self.max_retries
    
    def is_high_priority(self) -> bool:
        """Check if job is high priority"""
        return self.priority <= 3
    
    def is_medium_priority(self) -> bool:
        """Check if job is medium priority"""
        return 3 < self.priority <= 7
    
    def is_low_priority(self) -> bool:
        """Check if job is low priority"""
        return self.priority > 7
    
    def get_status_color(self) -> str:
        """Get color code for status display"""
        color_map = {
            'pending': 'yellow',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red'
        }
        return color_map.get(self.status, 'gray')
    
    def get_job_type_display(self) -> str:
        """Get human-readable job type"""
        type_map = {
            'ingestion': 'Document Ingestion',
            'extraction': 'Data Extraction',
            'validation': 'Data Validation',
            'formatting': 'Data Formatting'
        }
        return type_map.get(self.job_type, self.job_type.title())
    
    def get_status_display(self) -> str:
        """Get human-readable status"""
        status_map = {
            'pending': 'Pending',
            'processing': 'Processing',
            'completed': 'Completed',
            'failed': 'Failed'
        }
        return status_map.get(self.status, 'Unknown')
    
    def get_priority_display(self) -> str:
        """Get human-readable priority"""
        if self.is_high_priority():
            return 'High'
        elif self.is_medium_priority():
            return 'Medium'
        else:
            return 'Low'
