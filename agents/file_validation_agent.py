"""
File Validation Agent
Validates file types, sizes, and other constraints before processing
"""

import logging
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    print("Warning: python-magic not available, using fallback file detection")

from PIL import Image
import PyPDF2
import io

logger = logging.getLogger(__name__)

class FileValidationAgent:
    """Agent responsible for validating files before processing"""
    
    def __init__(self, config_loader):
        self.config_loader = config_loader
        
        # AWS Textract limits
        self.TEXTRACT_LIMITS = {
            "max_file_size_mb": 10,
            "max_pages": 3000,
            "supported_formats": ["pdf", "png", "jpg", "jpeg", "tiff"]
        }
        
        # File type validation
        self.FILE_EXTENSIONS = {
            "pdf": [".pdf"],
            "png": [".png"],
            "jpg": [".jpg", ".jpeg"],
            "jpeg": [".jpg", ".jpeg"],
            "tiff": [".tiff", ".tif"]
        }
        
        # MIME type validation
        self.MIME_TYPES = {
            "pdf": ["application/pdf"],
            "png": ["image/png"],
            "jpg": ["image/jpeg"],
            "jpeg": ["image/jpeg"],
            "tiff": ["image/tiff", "image/tif"]
        }
    
    async def validate_files(self, files: List[Tuple[bytes, str]], application_id: str) -> Dict[str, Any]:
        """
        Validate multiple files for processing
        
        Args:
            files: List of (file_content, filename) tuples
            application_id: Application ID
            
        Returns:
            Validation results with success status and details
        """
        logger.info(f"Starting file validation for application {application_id} with {len(files)} files")
        
        validation_results = {
            "application_id": application_id,
            "total_files": len(files),
            "valid_files": [],
            "invalid_files": [],
            "validation_summary": {
                "total": len(files),
                "valid": 0,
                "invalid": 0,
                "errors": []
            }
        }
        
        for file_content, filename in files:
            try:
                # Validate individual file (no document type detection)
                file_validation = await self._validate_single_file(
                    file_content, filename
                )
                
                if file_validation["valid"]:
                    validation_results["valid_files"].append({
                        "filename": filename,
                        "file_size_mb": file_validation["file_size_mb"],
                        "file_format": file_validation["file_format"],
                        "pages": file_validation.get("pages", 1)
                    })
                    validation_results["validation_summary"]["valid"] += 1
                else:
                    validation_results["invalid_files"].append({
                        "filename": filename,
                        "errors": file_validation["errors"]
                    })
                    validation_results["validation_summary"]["invalid"] += 1
                    validation_results["validation_summary"]["errors"].extend(file_validation["errors"])
                    
            except Exception as e:
                logger.error(f"Error validating file {filename}: {str(e)}")
                validation_results["invalid_files"].append({
                    "filename": filename,
                    "errors": [f"Validation error: {str(e)}"]
                })
                validation_results["validation_summary"]["invalid"] += 1
                validation_results["validation_summary"]["errors"].append(f"Error validating {filename}: {str(e)}")
        
        # Overall validation status
        validation_results["overall_valid"] = validation_results["validation_summary"]["invalid"] == 0
        
        logger.info(f"File validation completed for application {application_id}: "
                   f"{validation_results['validation_summary']['valid']} valid, "
                   f"{validation_results['validation_summary']['invalid']} invalid")
        
        return validation_results
    
    async def _validate_single_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Validate a single file for format and size only
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            
        Returns:
            Validation result for the file
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "file_size_mb": 0,
            "file_format": None,
            "pages": 1
        }
        
        # General limits (not document-specific)
        MAX_FILE_SIZE_MB = 10
        SUPPORTED_FORMATS = ["pdf", "png", "jpg", "jpeg", "tiff"]
        MAX_PAGES = 3000  # Textract limit
        
        try:
            # Get file size
            file_size_bytes = len(file_content)
            file_size_mb = file_size_bytes / (1024 * 1024)
            validation_result["file_size_mb"] = round(file_size_mb, 2)
            
            # Validate file size
            if file_size_mb > MAX_FILE_SIZE_MB:
                validation_result["valid"] = False
                validation_result["errors"].append(
                    f"File size {file_size_mb:.2f}MB exceeds maximum allowed {MAX_FILE_SIZE_MB}MB"
                )
            
            # Validate file format
            file_format = self._detect_file_format(file_content, filename)
            validation_result["file_format"] = file_format
            
            if file_format not in SUPPORTED_FORMATS:
                validation_result["valid"] = False
                validation_result["errors"].append(
                    f"File format '{file_format}' not supported. Supported formats: {', '.join(SUPPORTED_FORMATS)}"
                )
            
            
            # Count pages for PDF files
            if file_format == "pdf":
                try:
                    pages = self._count_pdf_pages(file_content)
                    validation_result["pages"] = pages
                    
                    # Check page limit
                    if pages > MAX_PAGES:
                        validation_result["valid"] = False
                        validation_result["errors"].append(
                            f"PDF has {pages} pages, exceeds maximum allowed {MAX_PAGES} pages"
                        )
                except Exception as e:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Error reading PDF: {str(e)}")
            
            # Additional image validation for image files
            elif file_format in ["png", "jpg", "jpeg", "tiff"]:
                try:
                    self._validate_image_file(file_content, file_format)
                except Exception as e:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Invalid image file: {str(e)}")
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    
    def _detect_file_format(self, file_content: bytes, filename: str) -> str:
        """Detect file format from content and filename"""
        try:
            # First try to detect from MIME type if magic is available
            if MAGIC_AVAILABLE:
                mime_type = magic.from_buffer(file_content, mime=True)
                
                for format_name, mime_types in self.MIME_TYPES.items():
                    if mime_type in mime_types:
                        return format_name
            
            # Fallback to file extension
            file_ext = Path(filename).suffix.lower()
            for format_name, extensions in self.FILE_EXTENSIONS.items():
                if file_ext in extensions:
                    return format_name
            
            # Additional content-based detection for common formats
            if self._is_pdf_content(file_content):
                return "pdf"
            elif self._is_image_content(file_content):
                return self._detect_image_format_from_content(file_content)
            
            return "unknown"
            
        except Exception as e:
            logger.warning(f"Error detecting file format: {str(e)}")
            # Fallback to file extension
            file_ext = Path(filename).suffix.lower()
            for format_name, extensions in self.FILE_EXTENSIONS.items():
                if file_ext in extensions:
                    return format_name
            return "unknown"
    
    def _count_pdf_pages(self, file_content: bytes) -> int:
        """Count pages in PDF file"""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            return len(pdf_reader.pages)
        except Exception as e:
            logger.error(f"Error counting PDF pages: {str(e)}")
            raise e
    
    def _validate_image_file(self, file_content: bytes, file_format: str) -> None:
        """Validate image file"""
        try:
            image = Image.open(io.BytesIO(file_content))
            image.verify()  # Verify the image is valid
            
            # Check image dimensions
            width, height = image.size
            if width < 100 or height < 100:
                raise ValueError("Image dimensions too small (minimum 100x100 pixels)")
            
            if width > 10000 or height > 10000:
                raise ValueError("Image dimensions too large (maximum 10000x10000 pixels)")
                
        except Exception as e:
            logger.error(f"Error validating image file: {str(e)}")
            raise e
    
    def _is_pdf_content(self, file_content: bytes) -> bool:
        """Check if content is a PDF by looking at the header"""
        return file_content.startswith(b'%PDF-')
    
    def _is_image_content(self, file_content: bytes) -> bool:
        """Check if content is an image by looking at common image headers"""
        image_signatures = [
            b'\xFF\xD8\xFF',  # JPEG
            b'\x89PNG\r\n\x1a\n',  # PNG
            b'II*\x00',  # TIFF (little endian)
            b'MM\x00*',  # TIFF (big endian)
        ]
        return any(file_content.startswith(sig) for sig in image_signatures)
    
    def _detect_image_format_from_content(self, file_content: bytes) -> str:
        """Detect image format from content headers"""
        if file_content.startswith(b'\xFF\xD8\xFF'):
            return "jpeg"
        elif file_content.startswith(b'\x89PNG\r\n\x1a\n'):
            return "png"
        elif file_content.startswith(b'II*\x00') or file_content.startswith(b'MM\x00*'):
            return "tiff"
        else:
            return "unknown"
    
    def _detect_document_type(self, filename: str) -> str:
        """Detect document type based on filename patterns"""
        filename_lower = filename.lower()
        
        # Bank statements
        if any(keyword in filename_lower for keyword in ['bank', 'statement', 'rbc', 'td', 'scotia', 'bmo', 'cibc']):
            return "bank_statement"
        
        # Driver's license
        if any(keyword in filename_lower for keyword in ['driver', 'license', 'licence', 'dl']):
            return "drivers_license"
        
        # Employment letter
        if any(keyword in filename_lower for keyword in ['employment', 'job', 'work', 'letter', 'offer']):
            return "employment_letter"
        
        # Pay stub
        if any(keyword in filename_lower for keyword in ['pay', 'stub', 'payslip', 'salary', 'wage']):
            return "pay_stub"
        
        # PR Card
        if any(keyword in filename_lower for keyword in ['pr', 'card', 'permanent', 'resident']):
            return "pr_card"
        
        # Passport
        if any(keyword in filename_lower for keyword in ['passport', 'pass']):
            return "passport"
        
        # T4 Form
        if any(keyword in filename_lower for keyword in ['t4', 'tax', 'income']):
            return "t4_form"
        
        # Utility bill
        if any(keyword in filename_lower for keyword in ['utility', 'bill', 'hydro', 'electric', 'gas', 'water']):
            return "utility_bill"
        
        # Mortgage application
        if any(keyword in filename_lower for keyword in ['mortgage', 'application', 'form']):
            return "mortgage_application"
        
        # Birth certificate
        if any(keyword in filename_lower for keyword in ['birth', 'certificate', 'cert']):
            return "birth_certificate"
        
        # Marriage certificate
        if any(keyword in filename_lower for keyword in ['marriage', 'wedding', 'certificate']):
            return "marriage_certificate"
        
        # Default to unknown
        return "unknown"
