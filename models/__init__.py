"""
Document Processor Models
Clean data models for the four-agent document processing system
"""

from .application import Application
from .document import Document
from .extracted_data import ExtractedData
from .validation_result import ValidationResult
from .golden_data import GoldenData
from .processing_log import ProcessingLog
from .document_job import DocumentJob

__all__ = [
    "Application",
    "Document", 
    "ExtractedData",
    "ValidationResult",
    "GoldenData",
    "ProcessingLog",
    "DocumentJob"
]
