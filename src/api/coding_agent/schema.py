from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskRequest(BaseModel):
    """Request model for scheduling a coding task"""
    task: str = Field(..., description="The coding task description", min_length=10)
    language: Optional[str] = Field("python", description="Preferred programming language")
    max_iterations: Optional[int] = Field(10, description="Maximum iterations allowed", ge=1, le=50)
    timeout: Optional[int] = Field(300, description="Timeout in seconds", ge=30, le=3600)
    debug_mode: Optional[bool] = Field(True, description="Enable debug mode")
    context: Optional[str] = Field(None, description="Additional context for the task")


class TaskResponse(BaseModel):
    """Response model for task scheduling"""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Initial job status")
    message: str = Field(..., description="Response message")
    estimated_completion: Optional[int] = Field(None, description="Estimated completion time in seconds")


class JobStatusResponse(BaseModel):
    """Response model for job status queries"""
    job_id: str = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Current job status")
    progress: int = Field(..., description="Progress percentage (0-100)", ge=0, le=100)
    current_iteration: int = Field(..., description="Current iteration number")
    max_iterations: int = Field(..., description="Maximum iterations allowed")
    started_at: Optional[str] = Field(None, description="Job start timestamp")
    completed_at: Optional[str] = Field(None, description="Job completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Results for completed jobs
    final_output: Optional[str] = Field(None, description="Final output for completed jobs")
    files_created: Optional[List[str]] = Field(None, description="List of files created")
    execution_results: Optional[List[Dict[str, Any]]] = Field(None, description="Execution results")
    download_link: Optional[str] = Field(None, description="Download link for completed project")


class JobListResponse(BaseModel):
    """Response model for listing jobs"""
    jobs: List[JobStatusResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    uptime: int = Field(..., description="Uptime in seconds")
    active_jobs: int = Field(..., description="Number of active jobs")
    total_jobs: int = Field(..., description="Total jobs processed") 