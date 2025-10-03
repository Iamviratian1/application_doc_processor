"""
Storage Service
Handles file storage operations - local storage with temporary S3 uploads for Textract
"""

import os
import time
import shutil
import boto3
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)

class StorageService:
    """Service for file storage operations - local storage with temporary S3 uploads"""
    
    def __init__(self):
        # Use local storage path that works both in Docker and locally
        if os.path.exists("/app"):  # Running in Docker
            self.local_storage_path = Path("/app/storage")
        else:  # Running locally
            self.local_storage_path = Path("storage")
        
        self.local_storage_path.mkdir(exist_ok=True)
        
        # AWS credentials for temporary Textract uploads
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.s3_bucket = os.getenv("AWS_S3_BUCKET")
        
        # Initialize S3 client for temporary uploads
        self.s3_client = None
        if all([self.aws_access_key_id, self.aws_secret_access_key, self.s3_bucket]):
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                    region_name=self.aws_region
                )
                logger.info(f"S3 client initialized for temporary uploads to bucket: {self.s3_bucket}")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {str(e)}")
        else:
            logger.warning("AWS credentials not configured. Textract processing will fail.")
    
    async def store_file_locally(self, file_content: bytes, file_path: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Store file locally (primary storage method)
        
        Args:
            file_content: File content as bytes
            file_path: Relative path where file should be stored
            metadata: Additional metadata for the file
            
        Returns:
            Dict with storage result
        """
        try:
            # Create full local path
            full_path = self.local_storage_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file to local storage
            with open(full_path, 'wb') as f:
                f.write(file_content)
            
            # Store metadata
            metadata_file = full_path.with_suffix(full_path.suffix + '.meta')
            if metadata:
                import json
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f)
            
            logger.info(f"File stored locally: {full_path}")
            
            return {
                "success": True,
                "file_path": str(full_path),
                "relative_path": file_path,
                "size": len(file_content),
                "storage_type": "local"
            }
            
        except Exception as e:
            error_msg = f"Local storage failed: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    async def upload_to_s3_temporary(self, file_path: str, s3_key: str = None) -> Dict[str, Any]:
        """
        Upload file to S3 temporarily for Textract processing
        
        Args:
            file_path: Local file path
            s3_key: S3 key (optional, will generate if not provided)
            
        Returns:
            Dict with upload result
        """
        try:
            if not self.s3_client:
                raise Exception("S3 client not initialized")
            
            # Generate S3 key if not provided
            if not s3_key:
                timestamp = int(time.time())
                filename = Path(file_path).name
                s3_key = f"temp/textract/{timestamp}/{filename}"
            
            # Upload to S3
            self.s3_client.upload_file(
                file_path,
                self.s3_bucket,
                s3_key
            )
            
            # Generate S3 URL
            s3_url = f"s3://{self.s3_bucket}/{s3_key}"
            
            logger.info(f"File uploaded to S3 temporarily: {s3_url}")
            
            return {
                "success": True,
                "s3_url": s3_url,
                "s3_key": s3_key,
                "bucket": self.s3_bucket
            }
            
        except ClientError as e:
            error_msg = f"S3 temporary upload failed: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Temporary upload failed: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    async def delete_from_s3_temporary(self, s3_key: str) -> Dict[str, Any]:
        """
        Delete temporary file from S3 after Textract processing
        
        Args:
            s3_key: S3 key of the file to delete
            
        Returns:
            Dict with deletion result
        """
        try:
            if not self.s3_client:
                raise Exception("S3 client not initialized")
            
            # Delete from S3
            self.s3_client.delete_object(
                Bucket=self.s3_bucket,
                Key=s3_key
            )
            
            logger.info(f"Temporary file deleted from S3: {s3_key}")
            
            return {
                "success": True,
                "s3_key": s3_key
            }
            
        except ClientError as e:
            error_msg = f"S3 temporary deletion failed: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Temporary deletion failed: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    async def get_local_file(self, file_path: str) -> Dict[str, Any]:
        """
        Get file from local storage
        
        Args:
            file_path: Relative file path
            
        Returns:
            Dict with file content and metadata
        """
        try:
            full_path = self.local_storage_path / file_path
            
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }
            
            # Read file content
            with open(full_path, 'rb') as f:
                file_content = f.read()
            
            # Read metadata if exists
            metadata = {}
            metadata_file = full_path.with_suffix(full_path.suffix + '.meta')
            if metadata_file.exists():
                import json
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            
            logger.info(f"File retrieved from local storage: {full_path}")
            
            return {
                "success": True,
                "file_content": file_content,
                "metadata": metadata,
                "size": len(file_content),
                "file_path": str(full_path)
            }
            
        except Exception as e:
            error_msg = f"Local file retrieval failed: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    async def delete_local_file(self, file_path: str) -> Dict[str, Any]:
        """
        Delete file from local storage
        
        Args:
            file_path: Relative file path
            
        Returns:
            Dict with deletion result
        """
        try:
            full_path = self.local_storage_path / file_path
            
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }
            
            # Delete file
            full_path.unlink()
            
            # Delete metadata file if exists
            metadata_file = full_path.with_suffix(full_path.suffix + '.meta')
            if metadata_file.exists():
                metadata_file.unlink()
            
            logger.info(f"File deleted from local storage: {full_path}")
            
            return {
                "success": True,
                "file_path": str(full_path)
            }
            
        except Exception as e:
            error_msg = f"Local file deletion failed: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    async def file_exists_locally(self, file_path: str) -> bool:
        """
        Check if file exists in local storage
        
        Args:
            file_path: Relative file path
            
        Returns:
            True if file exists, False otherwise
        """
        full_path = self.local_storage_path / file_path
        return full_path.exists()
    
    async def get_local_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get file information from local storage
        
        Args:
            file_path: Relative file path
            
        Returns:
            Dict with file information
        """
        try:
            full_path = self.local_storage_path / file_path
            
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }
            
            stat = full_path.stat()
            
            # Read metadata if exists
            metadata = {}
            metadata_file = full_path.with_suffix(full_path.suffix + '.meta')
            if metadata_file.exists():
                import json
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            
            return {
                "success": True,
                "file_path": str(full_path),
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "metadata": metadata
            }
            
        except Exception as e:
            error_msg = f"Local file info retrieval failed: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def get_local_storage_path(self) -> str:
        """Get the local storage directory path"""
        return str(self.local_storage_path)
    
    def is_s3_available(self) -> bool:
        """Check if S3 is available for temporary uploads"""
        return self.s3_client is not None