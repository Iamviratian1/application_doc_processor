"""
Configuration modules for the document processing system
"""

from .document_config import DocumentConfig
from .validation_config import ValidationConfig
from .formatting_config import FormattingConfig

__all__ = [
    "DocumentConfig",
    "ValidationConfig", 
    "FormattingConfig"
]
