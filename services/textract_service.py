"""
Textract Service
Handles AWS Textract operations for document analysis
"""

import os
import boto3
import asyncio
from typing import Dict, Any, List
from botocore.exceptions import ClientError
from utils.logger import get_logger

logger = get_logger(__name__)

class TextractService:
    """Service for AWS Textract operations"""
    
    def __init__(self):
        try:
            self.region = os.getenv("AWS_REGION", "us-east-1")
            self.bucket = os.getenv("AWS_S3_BUCKET")
            
            logger.info(f"Initializing TextractService with region: {self.region}, bucket: {self.bucket}")
            
            if not self.bucket:
                raise Exception("AWS S3 bucket not configured")
            
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            
            if not aws_access_key or not aws_secret_key:
                raise Exception("AWS credentials not configured")
            
            self.session = boto3.Session(
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=self.region
            )
            
            self.s3_client = self.session.client('s3')
            self.textract_client = self.session.client('textract')
            self.executor = None
            
            logger.info("TextractService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize TextractService: {str(e)}")
            raise
    
    async def upload_file_to_s3(self, file_content: bytes, file_name: str) -> str:
        """Upload file to S3 and return the S3 key"""
        try:
            if not self.executor:
                self.executor = asyncio.get_event_loop().run_in_executor
            
            await self.executor(
                None,
                lambda: self.s3_client.put_object(
                    Bucket=self.bucket,
                    Key=file_name,
                    Body=file_content
                )
            )
            
            logger.info(f"File uploaded to S3: {file_name}")
            return file_name
            
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {str(e)}")
            raise Exception(f"Failed to upload file to S3: {str(e)}")
    
    async def start_document_analysis(self, file_name: str, queries_config: dict) -> str:
        """Start document analysis with Textract"""
        try:
            if not self.executor:
                self.executor = asyncio.get_event_loop().run_in_executor
            
            logger.info(f"=== TEXTRACT SERVICE DEBUG: Starting analysis for {file_name} ===")
            logger.info(f"=== TEXTRACT SERVICE DEBUG: Queries config: {queries_config} ===")
            logger.info(f"=== TEXTRACT SERVICE DEBUG: Bucket: {self.bucket} ===")
            
            response = await self.executor(
                None,
                lambda: self.textract_client.start_document_analysis(
                    DocumentLocation={
                        'S3Object': {
                            'Bucket': self.bucket,
                            'Name': file_name
                        }
                    },
                    FeatureTypes=["QUERIES"],
                    QueriesConfig=queries_config
                )
            )
            
            logger.info(f"=== TEXTRACT SERVICE DEBUG: Analysis started, Job ID: {response['JobId']} ===")
            return response['JobId']
            
        except ClientError as e:
            logger.error(f"=== TEXTRACT SERVICE DEBUG: Failed to start document analysis: {str(e)} ===")
            raise Exception(f"Failed to start document analysis: {str(e)}")
    
    async def get_document_analysis_results(self, job_id: str, max_wait_time: int = 300) -> Dict[str, Any]:
        """Get document analysis results from Textract"""
        try:
            if not self.executor:
                self.executor = asyncio.get_event_loop().run_in_executor
            
            logger.info(f"=== TEXTRACT SERVICE DEBUG: Getting results for job {job_id} ===")
            start_time = asyncio.get_event_loop().time()
            
            while True:
                response = await self.executor(
                    None,
                    lambda: self.textract_client.get_document_analysis(JobId=job_id)
                )
                
                status = response['JobStatus']
                logger.info(f"=== TEXTRACT SERVICE DEBUG: Job status: {status} ===")
                
                if status == 'SUCCEEDED':
                    logger.info(f"=== TEXTRACT SERVICE DEBUG: Analysis succeeded, returning results ===")
                    logger.info(f"=== TEXTRACT SERVICE DEBUG: Response keys: {list(response.keys())} ===")
                    if 'Blocks' in response:
                        logger.info(f"=== TEXTRACT SERVICE DEBUG: Found {len(response['Blocks'])} blocks ===")
                    return response
                elif status == 'FAILED':
                    error_message = response.get('StatusMessage', 'Unknown error')
                    logger.error(f"=== TEXTRACT SERVICE DEBUG: Analysis failed: {error_message} ===")
                    raise Exception(f"Document analysis failed: {error_message}")
                
                # Check timeout
                elapsed_time = asyncio.get_event_loop().time() - start_time
                if elapsed_time > max_wait_time:
                    logger.error(f"=== TEXTRACT SERVICE DEBUG: Analysis timed out after {max_wait_time} seconds ===")
                    raise Exception(f"Document analysis timeout after {max_wait_time} seconds")
                
                # Wait before next check
                await asyncio.sleep(5)
                
        except ClientError as e:
            logger.error(f"Failed to get document analysis results: {str(e)}")
            raise Exception(f"Failed to get document analysis results: {str(e)}")
    
    async def analyze_document_with_query(
        self, 
        file_content: bytes, 
        filename: str, 
        query: str
    ) -> str:
        """Analyze document with a single query"""
        try:
            # Upload file to S3
            s3_key = await self.upload_file_to_s3(file_content, filename)
            
            # Start analysis
            queries_config = {
                "Queries": [
                    {
                        "Text": query,
                        "Alias": "document_type"
                    }
                ]
            }
            
            job_id = await self.start_document_analysis(s3_key, queries_config)
            
            # Get results
            results = await self.get_document_analysis_results(job_id)
            
            # Extract answer
            for block in results.get("Blocks", []):
                if block["BlockType"] == "QUERY_RESULT":
                    return block.get("Text", "Unknown document type")
            
            return "Unknown document type"
            
        except Exception as e:
            logger.error(f"Error analyzing document: {str(e)}")
            return "Error analyzing document"
    
    async def analyze_document_for_classification(
        self, 
        file_content: bytes, 
        filename: str
    ) -> Dict[str, Any]:
        """Analyze document to classify its type using Textract"""
        try:
            # Upload file to S3
            s3_key = await self.upload_file_to_s3(file_content, filename)
            
            # Ask Textract "What is this document?"
            queries_config = {
                "Queries": [
                    {
                        "Text": "What is this document?",
                        "Alias": "document_type"
                    }
                ]
            }
            
            job_id = await self.start_document_analysis(s3_key, queries_config)
            
            # Get results
            results = await self.get_document_analysis_results(job_id)
            
            # Extract Textract's answer and map to our document types
            textract_answer = "generic_document"
            for block in results.get("Blocks", []):
                if block["BlockType"] == "QUERY_RESULT":
                    textract_answer = block.get("Text", "generic_document")
                    break
            
            # Map Textract's answer to our standardized document types
            detected_type = self._map_textract_answer_to_document_type(textract_answer)
            
            # Clean up S3 file
            try:
                await self.executor(
                    None,
                    lambda: self.s3_client.delete_object(Bucket=self.bucket, Key=s3_key)
                )
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup S3 file {s3_key}: {cleanup_error}")
            
            return {
                "success": True,
                "document_type": detected_type,
                "textract_answer": textract_answer
            }
            
        except Exception as e:
            logger.error(f"Error classifying document {filename}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "document_type": "generic_document"
            }
    
    def _map_textract_answer_to_document_type(self, textract_answer: str) -> str:
        """Map Textract's answer to our standardized document types"""
        answer_lower = textract_answer.lower()
        
        # Map Textract answers to our document types
        if any(word in answer_lower for word in ["mortgage", "loan", "application"]):
            return "mortgage_application"
        elif any(word in answer_lower for word in ["t4", "tax", "income", "remuneration", "statement of remuneration"]):
            return "t4_form"
        elif any(word in answer_lower for word in ["employment", "job", "work", "salary", "letter"]):
            return "employment_letter"
        elif any(word in answer_lower for word in ["bank", "statement", "account"]) and "remuneration" not in answer_lower:
            return "bank_statement"
        elif any(word in answer_lower for word in ["pay", "stub", "payslip", "wage"]):
            return "pay_stub"
        elif any(word in answer_lower for word in ["credit", "report", "score"]):
            return "credit_report"
        elif any(word in answer_lower for word in ["property", "assessment", "valuation"]):
            return "property_assessment"
        elif any(word in answer_lower for word in ["insurance", "policy", "coverage"]):
            return "insurance_document"
        elif any(word in answer_lower for word in ["drivers", "license", "licence", "dl"]):
            return "drivers_license"
        elif any(word in answer_lower for word in ["passport", "pass"]):
            return "passport"
        elif any(word in answer_lower for word in ["birth", "certificate"]):
            return "birth_certificate"
        elif any(word in answer_lower for word in ["marriage", "certificate", "wedding"]):
            return "marriage_certificate"
        elif any(word in answer_lower for word in ["utility", "bill", "electric", "gas", "water", "phone"]):
            return "utility_bill"
        elif any(word in answer_lower for word in ["rental", "lease", "agreement", "rent"]):
            return "rental_agreement"
        elif any(word in answer_lower for word in ["immigration", "visa", "green", "card", "prcard"]):
            return "immigration_document"
        elif any(word in answer_lower for word in ["financial", "statement", "balance"]):
            return "financial_statement"
        elif any(word in answer_lower for word in ["investment", "portfolio", "mutual", "fund"]):
            return "investment_statement"
        else:
            return "generic_document"
