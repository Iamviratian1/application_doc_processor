"""
Processing Log Model
Represents audit trail logs from all agents
"""

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid
from typing import Optional, Dict, Any

Base = declarative_base()

class ProcessingLog(Base):
    __tablename__ = "processing_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(String(255), ForeignKey("applications.application_id"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"))
    agent_name = Column(String(50), nullable=False, index=True)  # 'ingestion', 'extraction', 'validation', 'formatting'
    step_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)  # 'started', 'completed', 'failed', 'skipped'
    message = Column(Text)
    error_details = Column(JSONB)
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<ProcessingLog(agent='{self.agent_name}', step='{self.step_name}', status='{self.status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'application_id': self.application_id,
            'document_id': str(self.document_id) if self.document_id else None,
            'agent_name': self.agent_name,
            'step_name': self.step_name,
            'status': self.status,
            'message': self.message,
            'error_details': self.error_details,
            'processing_time_ms': self.processing_time_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def is_successful(self) -> bool:
        """Check if log represents successful operation"""
        return self.status == 'completed'
    
    def is_failed(self) -> bool:
        """Check if log represents failed operation"""
        return self.status == 'failed'
    
    def is_started(self) -> bool:
        """Check if log represents started operation"""
        return self.status == 'started'
    
    def get_status_color(self) -> str:
        """Get color code for status display"""
        color_map = {
            'started': 'blue',
            'completed': 'green',
            'failed': 'red',
            'skipped': 'yellow'
        }
        return color_map.get(self.status, 'gray')
    
    def get_agent_display_name(self) -> str:
        """Get human-readable agent name"""
        agent_map = {
            'ingestion': 'Document Ingestion Agent',
            'extraction': 'Data Extraction Agent',
            'validation': 'Data Validation Agent',
            'formatting': 'Data Formatting Agent'
        }
        return agent_map.get(self.agent_name, self.agent_name.title())
    
    def get_status_display(self) -> str:
        """Get human-readable status"""
        status_map = {
            'started': 'Started',
            'completed': 'Completed',
            'failed': 'Failed',
            'skipped': 'Skipped'
        }
        return status_map.get(self.status, 'Unknown')
    
    def get_processing_time_display(self) -> str:
        """Get human-readable processing time"""
        if not self.processing_time_ms:
            return 'N/A'
        
        if self.processing_time_ms < 1000:
            return f"{self.processing_time_ms}ms"
        elif self.processing_time_ms < 60000:
            return f"{self.processing_time_ms / 1000:.1f}s"
        else:
            minutes = self.processing_time_ms // 60000
            seconds = (self.processing_time_ms % 60000) / 1000
            return f"{minutes}m {seconds:.1f}s"
