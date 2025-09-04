"""
In-Memory Job Repository Implementation

Current implementation using dictionaries that mirrors the existing
running_jobs and active_job_events logic from app.py.
"""

from typing import Dict, Any, Optional
import asyncio
from datetime import datetime

from agent.domain.repositories.job_repository import JobRepository


class InMemoryJobRepository(JobRepository):
    """In-memory implementation of job repository using dictionaries"""
    
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._job_events: Dict[str, asyncio.Event] = {}
    
    async def save_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        """Save or update job data"""
        self._jobs[job_id] = job_data
    
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job data by ID"""
        return self._jobs.get(job_id)
    
    async def update_job_status(self, job_id: str, status: str, **kwargs) -> None:
        """Update job status and optional additional fields"""
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = status
            
            # Add timestamp for status changes
            if status in ["completed", "failed", "cancelled"]:
                self._jobs[job_id]["end_time"] = datetime.now().isoformat()
            
            # Add any additional fields
            for key, value in kwargs.items():
                self._jobs[job_id][key] = value
    
    async def job_exists(self, job_id: str) -> bool:
        """Check if job exists"""
        return job_id in self._jobs
    
    async def set_job_event(self, job_id: str, event: asyncio.Event) -> None:
        """Set cancellation event for active job"""
        self._job_events[job_id] = event
    
    async def get_job_event(self, job_id: str) -> Optional[asyncio.Event]:
        """Get cancellation event for job"""
        return self._job_events.get(job_id)
    
    async def remove_job_event(self, job_id: str) -> None:
        """Remove cancellation event for job"""
        if job_id in self._job_events:
            del self._job_events[job_id]
    
    async def is_job_active(self, job_id: str) -> bool:
        """Check if job has active cancellation event"""
        return job_id in self._job_events