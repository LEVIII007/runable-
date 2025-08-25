from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
from typing import Optional
import os
from pathlib import Path

from src.api.coding_agent.schema import (
    TaskRequest, TaskResponse, JobStatusResponse, JobListResponse, 
    ErrorResponse, HealthResponse, JobStatus
)
from src.api.coding_agent.job_manager import get_job_manager
from src.config.settings import APP_NAME, VERSION
from src.config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.post("/schedule", response_model=TaskResponse)
async def schedule_coding_task(task_request: TaskRequest):
    """
    Schedule a new coding task.
    
    Accepts a plain-text task description and returns a job ID.
    The task will be executed asynchronously by the coding agent.
    """
    try:
        job_manager = get_job_manager()
        job_id = await job_manager.schedule_job(task_request)
        
        estimated_time = min(task_request.max_iterations * 30, task_request.timeout)
        
        return TaskResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message=f"Coding task scheduled successfully. Job ID: {job_id}",
            estimated_completion=estimated_time
        )
        
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to schedule task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to schedule coding task")


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a specific coding job.
    
    Returns detailed information about the job including progress,
    results, and download links for completed jobs.
    """
    try:
        job_manager = get_job_manager()
        job_info = job_manager.get_job_status(job_id)
        
        if not job_info:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return JobStatusResponse(
            job_id=job_info.job_id,
            status=job_info.status,
            progress=job_info.progress,
            current_iteration=job_info.current_iteration,
            max_iterations=job_info.task_request.max_iterations,
            started_at=job_info.started_at.isoformat() if job_info.started_at else None,
            completed_at=job_info.completed_at.isoformat() if job_info.completed_at else None,
            error_message=job_info.error_message,
            final_output=job_info.final_output,
            files_created=job_info.files_created,
            execution_results=job_info.execution_results,
            download_link=job_info.download_link
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job status")


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of jobs per page")
):
    """
    List all coding jobs with pagination.
    
    Returns a paginated list of jobs with their current status.
    """
    try:
        job_manager = get_job_manager()
        offset = (page - 1) * page_size
        jobs, total = job_manager.list_jobs(limit=page_size, offset=offset)
        
        job_responses = []
        for job_info in jobs:
            job_responses.append(JobStatusResponse(
                job_id=job_info.job_id,
                status=job_info.status,
                progress=job_info.progress,
                current_iteration=job_info.current_iteration,
                max_iterations=job_info.task_request.max_iterations,
                started_at=job_info.started_at.isoformat() if job_info.started_at else None,
                completed_at=job_info.completed_at.isoformat() if job_info.completed_at else None,
                error_message=job_info.error_message,
                final_output=job_info.final_output if len(job_info.final_output or "") < 500 else f"{job_info.final_output[:500]}...",
                files_created=job_info.files_created,
                execution_results=job_info.execution_results,
                download_link=job_info.download_link
            ))
        
        return JobListResponse(
            jobs=job_responses,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job list")


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """
    Cancel a running coding job.
    
    Cancels the job if it's currently pending or running.
    """
    try:
        job_manager = get_job_manager()
        success = job_manager.cancel_job(job_id)
        
        if not success:
            raise HTTPException(
                status_code=400, 
                detail="Job cannot be cancelled (not found or already completed)"
            )
        
        return {"message": f"Job {job_id} cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel job")


@router.get("/download/{filename}")
async def download_results(filename: str):
    """
    Download results from a completed coding job.
    
    Returns a zip file containing all generated files and results.
    """
    try:
        job_manager = get_job_manager()
        download_path = job_manager.job_storage_path / "downloads" / filename
        
        if not download_path.exists():
            raise HTTPException(status_code=404, detail="Download file not found")
        
        return FileResponse(
            path=str(download_path),
            filename=filename,
            media_type="application/zip"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to serve download {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to serve download")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Get the health status of the coding agent service.
    
    Returns service information and current job statistics.
    """
    try:
        job_manager = get_job_manager()
        stats = job_manager.get_stats()
        
        return HealthResponse(
            status="healthy",
            version=VERSION,
            uptime=stats["uptime"],
            active_jobs=stats["active_jobs"],
            total_jobs=stats["total_jobs"]
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            version=VERSION,
            uptime=0,
            active_jobs=0,
            total_jobs=0
        )


@router.post("/test")
async def test_coding_agent():
    """
    Test endpoint to verify the coding agent is working.
    
    Schedules a simple test task and returns the job ID.
    """
    test_task = TaskRequest(
        task="Create a simple Python script that prints 'Hello, World!' and calculates 2+2",
        language="python",
        max_iterations=3,
        timeout=60,
        debug_mode=True
    )
    
    try:
        job_manager = get_job_manager()
        job_id = await job_manager.schedule_job(test_task)
        
        return {
            "message": "Test task scheduled successfully",
            "job_id": job_id,
            "test_task": test_task.task
        }
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")


# Background task to clean up old jobs
async def cleanup_old_jobs():
    """Background task to clean up old completed jobs"""
    try:
        job_manager = get_job_manager()
        job_manager.cleanup_old_jobs(max_age_days=7)
        logger.info("Cleaned up old jobs")
    except Exception as e:
        logger.error(f"Failed to cleanup old jobs: {str(e)}")


@router.post("/admin/cleanup")
async def trigger_cleanup(background_tasks: BackgroundTasks):
    """
    Admin endpoint to trigger cleanup of old jobs.
    """
    background_tasks.add_task(cleanup_old_jobs)
    return {"message": "Cleanup task scheduled"} 