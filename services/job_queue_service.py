"""
Job Queue Service
Handles job queue management and processing
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from services.database_service import DatabaseService
from utils.logger import get_logger

logger = get_logger(__name__)

class JobQueueService:
    """Service for managing job queue and processing"""
    
    def __init__(self, ingestion_agent=None, extraction_agent=None, validation_agent=None, formatting_agent=None):
        self.db_service = DatabaseService()
        self.ingestion_agent = ingestion_agent
        self.extraction_agent = extraction_agent
        self.validation_agent = validation_agent
        self.formatting_agent = formatting_agent
        self.is_running = False
        self.processing_tasks = {}
    
    async def start_job_processor(self):
        """Start the job processor"""
        if self.is_running:
            logger.warning("Job processor is already running")
            return
        
        self.is_running = True
        logger.info("Starting job processor")
        
        try:
            while self.is_running:
                try:
                    logger.info("=== LOOP DEBUG: Job processor loop iteration ===")
                    print("=== LOOP DEBUG: Job processor loop iteration ===")
                    await self._process_job_queue()
                    logger.info("=== LOOP DEBUG: Finished processing job queue, sleeping 5 seconds ===")
                    print("=== LOOP DEBUG: Finished processing job queue, sleeping 5 seconds ===")
                    await asyncio.sleep(5)  # Check every 5 seconds
                except Exception as e:
                    logger.error(f"=== LOOP ERROR: Error in job processor loop: {str(e)} ===")
                    print(f"=== LOOP ERROR: Error in job processor loop: {str(e)} ===")
                    import traceback
                    logger.error(f"=== LOOP TRACEBACK: {traceback.format_exc()} ===")
                    print(f"=== LOOP TRACEBACK: {traceback.format_exc()} ===")
                    # Continue the loop even if there's an error
                    await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"=== MAIN ERROR: Job processor main error: {str(e)} ===")
            print(f"=== MAIN ERROR: Job processor main error: {str(e)} ===")
            import traceback
            logger.error(f"=== MAIN TRACEBACK: {traceback.format_exc()} ===")
            print(f"=== MAIN TRACEBACK: {traceback.format_exc()} ===")
        finally:
            self.is_running = False
            logger.info("Job processor stopped")
            print("=== JOB PROCESSOR STOPPED ===")
    
    async def stop_job_processor(self):
        """Stop the job processor"""
        self.is_running = False
        logger.info("Stopping job processor")
    
    async def _process_job_queue(self):
        """Process pending jobs"""
        try:
            # Get pending jobs
            logger.info("=== QUEUE DEBUG: Starting _process_job_queue ===")
            print("=== QUEUE DEBUG: Starting _process_job_queue ===")
            
            try:
                pending_jobs = await self.db_service.get_pending_jobs()
                logger.info(f"=== QUEUE DEBUG: Found {len(pending_jobs)} pending jobs ===")
                print(f"=== QUEUE DEBUG: Found {len(pending_jobs)} pending jobs ===")
            except Exception as db_error:
                logger.error(f"=== QUEUE DEBUG: Database error getting pending jobs: {str(db_error)} ===")
                print(f"=== QUEUE DEBUG: Database error getting pending jobs: {str(db_error)} ===")
                # Continue without processing jobs if database is unavailable
                return
            
            if not pending_jobs:
                logger.info("=== QUEUE DEBUG: No pending jobs, returning ===")
                print("=== QUEUE DEBUG: No pending jobs, returning ===")
                return
            
            logger.info(f"=== QUEUE DEBUG: About to process {len(pending_jobs)} jobs ===")
            print(f"=== QUEUE DEBUG: About to process {len(pending_jobs)} jobs ===")
            
            # Process jobs concurrently (with limit)
            semaphore = asyncio.Semaphore(3)  # Max 3 concurrent jobs
            
            async def process_job(job):
                logger.info(f"=== QUEUE DEBUG: About to process job {job['id']} (type: {job['job_type']}) ===")
                print(f"=== QUEUE DEBUG: About to process job {job['id']} (type: {job['job_type']}) ===")
                async with semaphore:
                    await self._process_single_job(job)
                logger.info(f"=== QUEUE DEBUG: Finished processing job {job['id']} ===")
                print(f"=== QUEUE DEBUG: Finished processing job {job['id']} ===")
            
            tasks = [process_job(job) for job in pending_jobs[:10]]  # Process up to 10 jobs at a time
            logger.info(f"=== QUEUE DEBUG: Created {len(tasks)} tasks, about to gather ===")
            print(f"=== QUEUE DEBUG: Created {len(tasks)} tasks, about to gather ===")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"=== QUEUE DEBUG: Gather completed, results: {results} ===")
            print(f"=== QUEUE DEBUG: Gather completed, results: {results} ===")
            
        except Exception as e:
            logger.error(f"=== QUEUE DEBUG: Error processing job queue: {str(e)} ===")
            print(f"=== QUEUE DEBUG: Error processing job queue: {str(e)} ===")
            import traceback
            logger.error(f"=== QUEUE DEBUG: Traceback: {traceback.format_exc()} ===")
            print(f"=== QUEUE DEBUG: Traceback: {traceback.format_exc()} ===")
    
    async def _process_single_job(self, job: Dict[str, Any]):
        """Process a single job"""
        job_id = job["id"]
        job_type = job["job_type"]
        application_id = job["application_id"]
        document_id = job.get("document_id")
        
        try:
            logger.info(f"Starting job processing: {job_id} (type: {job_type}, document: {document_id})")
            
            # Update job status to processing
            await self.db_service.update_job_status(job_id, "processing")
            
            # Process based on job type
            if job_type == "extraction":
                print(f"=== JOB DEBUG: Processing extraction job for document {document_id} ===")
                logger.info(f"=== JOB DEBUG: Processing extraction job for document {document_id} ===")
                print(f"=== JOB DEBUG: About to call extraction_agent.extract_document_data ===")
                logger.info(f"=== JOB DEBUG: About to call extraction_agent.extract_document_data ===")
                try:
                    print(f"=== JOB DEBUG: Calling extraction_agent.extract_document_data({document_id}, {application_id}) ===")
                    result = await self.extraction_agent.extract_document_data(document_id, application_id)
                    print(f"=== JOB DEBUG: Extraction result: {result} ===")
                    logger.info(f"=== JOB DEBUG: Extraction result: {result} ===")
                    print(f"=== JOB DEBUG: Extraction success: {result.get('success', False)} ===")
                    logger.info(f"=== JOB DEBUG: Extraction success: {result.get('success', False)} ===")
                except Exception as e:
                    print(f"=== JOB DEBUG: Exception in extraction agent: {str(e)} ===")
                    logger.error(f"=== JOB DEBUG: Exception in extraction agent: {str(e)} ===")
                    import traceback
                    print(f"=== JOB DEBUG: Traceback: {traceback.format_exc()} ===")
                    logger.error(f"=== JOB DEBUG: Traceback: {traceback.format_exc()} ===")
                    result = {"success": False, "error": str(e)}
            elif job_type == "validation":
                logger.info(f"Processing validation job for application {application_id}")
                result = await self.validation_agent.validate_application_data(application_id)
            elif job_type == "formatting":
                logger.info(f"Processing formatting job for application {application_id}")
                result = await self.formatting_agent.format_application_data(application_id)
            else:
                raise Exception(f"Unknown job type: {job_type}")
            
            if result.get("success"):
                await self.db_service.update_job_status(job_id, "completed")
                logger.info(f"Job {job_id} completed successfully")
            else:
                await self.db_service.update_job_status(job_id, "failed", result.get("error"))
                logger.error(f"Job {job_id} failed: {result.get('error')}")
                
        except Exception as e:
            error_msg = str(e)
            await self.db_service.update_job_status(job_id, "failed", error_msg)
            logger.error(f"Job {job_id} failed with exception: {error_msg}")
    
    async def add_extraction_job(self, application_id: str, document_id: str, priority: int = 5):
        """Add extraction job to queue"""
        try:
            job_data = {
                "application_id": application_id,
                "document_id": document_id,
                "job_type": "extraction",
                "status": "pending",
                "priority": priority
            }
            
            result = await self.db_service.create_document_job(job_data)
            logger.info(f"Added extraction job for document {document_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error adding extraction job: {str(e)}")
            raise
    
    async def add_validation_job(self, application_id: str, priority: int = 3):
        """Add validation job to queue"""
        try:
            job_data = {
                "application_id": application_id,
                "document_id": None,
                "job_type": "validation",
                "status": "pending",
                "priority": priority
            }
            
            result = await self.db_service.create_document_job(job_data)
            logger.info(f"Added validation job for application {application_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error adding validation job: {str(e)}")
            raise
    
    async def add_formatting_job(self, application_id: str, priority: int = 2):
        """Add formatting job to queue"""
        try:
            job_data = {
                "application_id": application_id,
                "document_id": None,
                "job_type": "formatting",
                "status": "pending",
                "priority": priority
            }
            
            result = await self.db_service.create_document_job(job_data)
            logger.info(f"Added formatting job for application {application_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error adding formatting job: {str(e)}")
            raise
    
    async def get_job_status(self, application_id: str) -> Dict[str, Any]:
        """Get job status for an application"""
        try:
            # Get all jobs for application
            jobs = await self.db_service.get_pending_jobs()
            application_jobs = [job for job in jobs if job["application_id"] == application_id]
            
            # Count by status
            status_counts = {"pending": 0, "processing": 0, "completed": 0, "failed": 0}
            for job in application_jobs:
                status_counts[job["status"]] += 1
            
            return {
                "application_id": application_id,
                "total_jobs": len(application_jobs),
                "status_counts": status_counts,
                "jobs": application_jobs
            }
            
        except Exception as e:
            logger.error(f"Error getting job status: {str(e)}")
            return {
                "application_id": application_id,
                "error": str(e)
            }
    
    async def retry_failed_jobs(self, application_id: str = None):
        """Retry failed jobs"""
        try:
            # Get failed jobs
            failed_jobs = await self.db_service.get_pending_jobs()
            failed_jobs = [job for job in failed_jobs if job["status"] == "failed"]
            
            if application_id:
                failed_jobs = [job for job in failed_jobs if job["application_id"] == application_id]
            
            retry_count = 0
            for job in failed_jobs:
                if job["retry_count"] < job["max_retries"]:
                    # Reset job status to pending
                    await self.db_service.update_job_status(job["id"], "pending")
                    retry_count += 1
            
            logger.info(f"Retried {retry_count} failed jobs")
            return {"retried_jobs": retry_count}
            
        except Exception as e:
            logger.error(f"Error retrying failed jobs: {str(e)}")
            return {"error": str(e)}
