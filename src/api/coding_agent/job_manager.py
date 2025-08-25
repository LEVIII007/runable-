import asyncio
import uuid
import time
import os
import zipfile
import tempfile
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor
import threading
from pathlib import Path

from src.api.coding_agent.schema import JobStatus, TaskRequest
from src.ai.workflows.coding_agent_workflow import run_coding_task
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class JobInfo:
    """Information about a coding job"""
    
    def __init__(self, job_id: str, task_request: TaskRequest):
        self.job_id = job_id
        self.task_request = task_request
        self.status = JobStatus.PENDING
        self.progress = 0
        self.current_iteration = 0
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.final_output: Optional[str] = None
        self.files_created: List[str] = []
        self.execution_results: List[Dict[str, Any]] = []
        self.working_directory: Optional[str] = None
        self.download_link: Optional[str] = None
        self.future: Optional[asyncio.Future] = None


class JobManager:
    """Manages coding agent jobs with async execution and state tracking"""
    
    def __init__(self, max_concurrent_jobs: int = 5, job_storage_path: str = "./jobs"):
        self.jobs: Dict[str, JobInfo] = {}
        self.max_concurrent_jobs = max_concurrent_jobs
        self.job_storage_path = Path(job_storage_path)
        self.job_storage_path.mkdir(parents=True, exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_jobs)
        self.running_jobs = 0
        self.total_jobs_processed = 0
        self.start_time = time.time()
        self._lock = threading.Lock()
        
        # Load existing jobs from storage
        self._load_jobs_from_storage()
    
    def _save_job_to_storage(self, job_info: JobInfo):
        """Save job information to persistent storage"""
        try:
            job_file = self.job_storage_path / f"{job_info.job_id}.json"
            job_data = {
                "job_id": job_info.job_id,
                "task": job_info.task_request.task,
                "language": job_info.task_request.language,
                "max_iterations": job_info.task_request.max_iterations,
                "timeout": job_info.task_request.timeout,
                "debug_mode": job_info.task_request.debug_mode,
                "context": job_info.task_request.context,
                "status": job_info.status.value,
                "progress": job_info.progress,
                "current_iteration": job_info.current_iteration,
                "started_at": job_info.started_at.isoformat() if job_info.started_at else None,
                "completed_at": job_info.completed_at.isoformat() if job_info.completed_at else None,
                "error_message": job_info.error_message,
                "final_output": job_info.final_output,
                "files_created": job_info.files_created,
                "execution_results": job_info.execution_results,
                "working_directory": job_info.working_directory,
                "download_link": job_info.download_link
            }
            
            with open(job_file, 'w') as f:
                json.dump(job_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save job {job_info.job_id} to storage: {str(e)}")
    
    def _load_jobs_from_storage(self):
        """Load jobs from persistent storage"""
        try:
            for job_file in self.job_storage_path.glob("*.json"):
                try:
                    with open(job_file, 'r') as f:
                        job_data = json.load(f)
                    
                    # Recreate TaskRequest
                    task_request = TaskRequest(
                        task=job_data["task"],
                        language=job_data.get("language", "python"),
                        max_iterations=job_data.get("max_iterations", 10),
                        timeout=job_data.get("timeout", 300),
                        debug_mode=job_data.get("debug_mode", True),
                        context=job_data.get("context")
                    )
                    
                    # Recreate JobInfo
                    job_info = JobInfo(job_data["job_id"], task_request)
                    job_info.status = JobStatus(job_data["status"])
                    job_info.progress = job_data["progress"]
                    job_info.current_iteration = job_data["current_iteration"]
                    job_info.started_at = datetime.fromisoformat(job_data["started_at"]) if job_data["started_at"] else None
                    job_info.completed_at = datetime.fromisoformat(job_data["completed_at"]) if job_data["completed_at"] else None
                    job_info.error_message = job_data.get("error_message")
                    job_info.final_output = job_data.get("final_output")
                    job_info.files_created = job_data.get("files_created", [])
                    job_info.execution_results = job_data.get("execution_results", [])
                    job_info.working_directory = job_data.get("working_directory")
                    job_info.download_link = job_data.get("download_link")
                    
                    self.jobs[job_info.job_id] = job_info
                    
                    # Update counters
                    if job_info.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                        self.total_jobs_processed += 1
                    
                except Exception as e:
                    logger.error(f"Failed to load job from {job_file}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Failed to load jobs from storage: {str(e)}")
    
    def _create_download_package(self, job_info: JobInfo) -> Optional[str]:
        """Create a downloadable package of the job results"""
        try:
            if not job_info.working_directory or not os.path.exists(job_info.working_directory):
                return None
            
            # Create a zip file with all created files
            download_dir = self.job_storage_path / "downloads"
            download_dir.mkdir(exist_ok=True)
            
            zip_filename = f"{job_info.job_id}_results.zip"
            zip_path = download_dir / zip_filename
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all files from working directory
                for root, dirs, files in os.walk(job_info.working_directory):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, job_info.working_directory)
                        zipf.write(file_path, arcname)
                
                # Add a results summary
                summary = {
                    "job_id": job_info.job_id,
                    "task": job_info.task_request.task,
                    "status": job_info.status.value,
                    "final_output": job_info.final_output,
                    "files_created": job_info.files_created,
                    "execution_results": job_info.execution_results,  # Already converted to dicts
                    "completed_at": job_info.completed_at.isoformat() if job_info.completed_at else None
                }
                
                zipf.writestr("job_summary.json", json.dumps(summary, indent=2))
            
            # Return relative path for download
            return f"/api/coding-agent/download/{zip_filename}"
            
        except Exception as e:
            logger.error(f"Failed to create download package for job {job_info.job_id}: {str(e)}")
            return None
    
    async def schedule_job(self, task_request: TaskRequest) -> str:
        """Schedule a new coding job"""
        
        with self._lock:
            # Check if we can accept new jobs
            if self.running_jobs >= self.max_concurrent_jobs:
                raise RuntimeError("Maximum concurrent jobs reached. Please try again later.")
            
            # Create job
            job_id = str(uuid.uuid4())
            job_info = JobInfo(job_id, task_request)
            self.jobs[job_id] = job_info
            
            # Save to storage
            self._save_job_to_storage(job_info)
            
            # Start the job asynchronously
            job_info.future = asyncio.create_task(self._execute_job(job_info))
            
            logger.info(f"Scheduled job {job_id}: {task_request.task[:100]}...")
            return job_id
    
    async def _execute_job(self, job_info: JobInfo):
        """Execute a coding job asynchronously"""
        
        with self._lock:
            self.running_jobs += 1
            job_info.status = JobStatus.RUNNING
            job_info.started_at = datetime.now(timezone.utc)
            job_info.progress = 10
        
        self._save_job_to_storage(job_info)
        
        try:
            logger.info(f"Starting execution of job {job_info.job_id}")
            
            # Run the coding task in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                run_coding_task,
                job_info.task_request.task,
                job_info.task_request.max_iterations,
                job_info.task_request.debug_mode,
                job_info.job_id  # Pass job_id for workspace organization
            )
            
            # Update job with results
            with self._lock:
                if result["success"]:
                    job_info.status = JobStatus.COMPLETED
                    job_info.progress = 100
                    job_info.final_output = result.get("final_output")
                    job_info.files_created = result.get("files_created", [])
                    
                    # Set working directory from result if available
                    if "working_directory" in result:
                        job_info.working_directory = result["working_directory"]
                    else:
                        # Fallback to expected workspace structure
                        job_info.working_directory = f"workspace/{job_info.job_id}"
                    
                    # Convert ExecutionResult objects to dictionaries for JSON serialization
                    execution_results = result.get("execution_results", [])
                    job_info.execution_results = []
                    for exec_result in execution_results:
                        if hasattr(exec_result, 'model_dump'):  # Pydantic model
                            job_info.execution_results.append(exec_result.model_dump())
                        elif hasattr(exec_result, 'dict'):  # Older Pydantic versions
                            job_info.execution_results.append(exec_result.dict())
                        elif isinstance(exec_result, dict):  # Already a dict
                            job_info.execution_results.append(exec_result)
                        else:  # Fallback for other types
                            job_info.execution_results.append({
                                "success": getattr(exec_result, 'success', False),
                                "output": str(getattr(exec_result, 'output', '')),
                                "execution_time": getattr(exec_result, 'execution_time', 0.0)
                            })
                    
                    # Create download package
                    job_info.download_link = self._create_download_package(job_info)
                    
                else:
                    job_info.status = JobStatus.FAILED
                    job_info.error_message = result.get("error", "Unknown error")
                    job_info.progress = 100
                
                job_info.completed_at = datetime.now(timezone.utc)
                self.total_jobs_processed += 1
                
        except Exception as e:
            logger.error(f"Job {job_info.job_id} failed with exception: {str(e)}")
            with self._lock:
                job_info.status = JobStatus.FAILED
                job_info.error_message = str(e)
                job_info.progress = 100
                job_info.completed_at = datetime.now(timezone.utc)
                self.total_jobs_processed += 1
        
        finally:
            with self._lock:
                self.running_jobs -= 1
            
            self._save_job_to_storage(job_info)
            logger.info(f"Job {job_info.job_id} completed with status: {job_info.status}")
    
    def get_job_status(self, job_id: str) -> Optional[JobInfo]:
        """Get the status of a specific job"""
        return self.jobs.get(job_id)
    
    def list_jobs(self, limit: int = 50, offset: int = 0) -> tuple[List[JobInfo], int]:
        """List jobs with pagination"""
        all_jobs = list(self.jobs.values())
        # Sort by creation time (most recent first)
        all_jobs.sort(key=lambda x: x.started_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        
        total = len(all_jobs)
        jobs = all_jobs[offset:offset + limit]
        
        return jobs, total
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job"""
        job_info = self.jobs.get(job_id)
        
        if not job_info:
            return False
        
        if job_info.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
            return False
        
        try:
            if job_info.future and not job_info.future.done():
                job_info.future.cancel()
            
            with self._lock:
                job_info.status = JobStatus.CANCELLED
                job_info.completed_at = datetime.now(timezone.utc)
                job_info.progress = 100
                if self.running_jobs > 0:
                    self.running_jobs -= 1
            
            self._save_job_to_storage(job_info)
            logger.info(f"Cancelled job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {str(e)}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get job manager statistics"""
        return {
            "active_jobs": self.running_jobs,
            "total_jobs": len(self.jobs),
            "total_processed": self.total_jobs_processed,
            "uptime": int(time.time() - self.start_time),
            "max_concurrent": self.max_concurrent_jobs
        }
    
    def cleanup_old_jobs(self, max_age_days: int = 7):
        """Clean up old completed jobs"""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_days * 24 * 3600)
        
        jobs_to_remove = []
        for job_id, job_info in self.jobs.items():
            if (job_info.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED] and
                job_info.completed_at and 
                job_info.completed_at.timestamp() < cutoff_time):
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            try:
                # Remove job file
                job_file = self.job_storage_path / f"{job_id}.json"
                if job_file.exists():
                    job_file.unlink()
                
                # Remove from memory
                del self.jobs[job_id]
                
                logger.info(f"Cleaned up old job {job_id}")
                
            except Exception as e:
                logger.error(f"Failed to cleanup job {job_id}: {str(e)}")


# Global job manager instance
_job_manager: Optional[JobManager] = None

def get_job_manager() -> JobManager:
    """Get or create the global job manager instance"""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager 