"""
Search Job Service

Handles job lifecycle management, state transitions, and coordination
between different job operations. Extracted from app.py for clean separation.
"""

import uuid
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from agent.domain.repositories.job_repository import JobRepository


class SearchJobService:
    """Service responsible for managing search job lifecycle"""
    
    def __init__(self, job_repository: JobRepository):
        self.job_repository = job_repository
    
    async def start_search_job(self, query: str, effort: str) -> str:
        """
        Start a new product search job
        
        Returns:
            job_id: Unique identifier for the job
        """
        job_id = str(uuid.uuid4())
        
        # Create initial job data
        job_data = {
            "status": "starting",
            "query": query,
            "effort": effort,
            "start_time": datetime.now().isoformat(),
            "html_file_path": None,
            "error": None
        }
        
        await self.job_repository.save_job(job_id, job_data)
        return job_id
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current job status and data"""
        return await self.job_repository.get_job(job_id)
    
    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """
        Cancel a running job
        
        Returns:
            Result dict with cancellation status
        """
        # Check if job exists
        if not await self.job_repository.job_exists(job_id):
            raise ValueError("Job not found")
        
        job_data = await self.job_repository.get_job(job_id)
        
        # Check if already finished
        if job_data["status"] in ["completed", "failed", "cancelled"]:
            return {
                "status": "already_finished", 
                "job_id": job_id, 
                "current_status": job_data["status"]
            }
        
        # Check if job is actively running
        if await self.job_repository.is_job_active(job_id):
            # Get and trigger the cancellation event
            event = await self.job_repository.get_job_event(job_id)
            if event:
                event.set()
            
            # Update job status
            await self.job_repository.update_job_status(
                job_id, 
                "cancelled",
                cancelled_by_user=True
            )
            
            return {
                "status": "cancelling", 
                "job_id": job_id, 
                "message": "Cancellation signal sent"
            }
        else:
            # Job not actively running, just mark as cancelled
            await self.job_repository.update_job_status(
                job_id,
                "cancelled", 
                cancelled_by_user=True
            )
            
            return {
                "status": "cancelled", 
                "job_id": job_id, 
                "message": "Job marked as cancelled"
            }
    
    async def set_job_active(self, job_id: str) -> asyncio.Event:
        """
        Mark job as active with cancellation event
        
        Returns:
            The cancellation event for the job
        """
        stop_event = asyncio.Event()
        await self.job_repository.set_job_event(job_id, stop_event)
        return stop_event
    
    async def set_job_inactive(self, job_id: str) -> None:
        """Remove job from active tracking"""
        await self.job_repository.remove_job_event(job_id)
    
    async def update_job_with_results(self, job_id: str, html_file_path: str) -> None:
        """Update job with final results"""
        import pathlib
        filename = pathlib.Path(html_file_path).name
        
        await self.job_repository.update_job_status(
            job_id,
            "completed",
            html_file_path=filename
        )
    
    async def mark_job_failed(self, job_id: str, error: str) -> None:
        """Mark job as failed with error message"""
        await self.job_repository.update_job_status(
            job_id,
            "failed", 
            error=error
        )
    
    async def set_awaiting_human_input(self, job_id: str, question: str, current_state: Dict) -> None:
        """Set job to await human input"""
        await self.job_repository.update_job_status(
            job_id,
            "awaiting_human_input",
            awaiting_human=True,
            human_question=question,
            current_state=current_state
        )
    
    async def submit_human_response(self, job_id: str, answer: str) -> Dict[str, Any]:
        """Submit human response and prepare for job resumption"""
        if not await self.job_repository.job_exists(job_id):
            raise ValueError("Job not found")
        
        job_data = await self.job_repository.get_job(job_id)
        
        if not job_data.get("awaiting_human"):
            raise ValueError("Job is not awaiting human input")
        
        # Update job with human answer
        await self.job_repository.update_job_status(
            job_id,
            "resuming_after_human_input",
            human_answer=answer,
            awaiting_human=False
        )
        
        return {"status": "response_received", "job_id": job_id}