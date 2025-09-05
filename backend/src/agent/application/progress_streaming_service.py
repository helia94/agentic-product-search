"""
Progress Streaming Service

Handles streaming of job progress events to the frontend.
Clean separation from API layer - focuses purely on business logic of streaming.
"""

import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

from agent.domain.repositories.job_repository import JobRepository
from agent.tracing.node_progress import get_progress_events


class StreamEvent(BaseModel):
    """API event model for frontend"""
    event: str
    data: Dict[str, Any]
    timestamp: str


class ProgressStreamingService:
    """Service responsible for streaming job progress to clients"""
    
    def __init__(self, job_repository: JobRepository):
        self.job_repository = job_repository
    
    async def stream_job_progress(self, job_id: str) -> AsyncGenerator[str, None]:
        """
        Stream progress events for a job
        
        Args:
            job_id: Job to stream progress for
            
        Yields:
            Server-sent event strings for the frontend
        """
        # Check if job exists
        if not await self.job_repository.job_exists(job_id):
            return
        
        last_event_timestamp = None
        
        while True:
            job_data = await self.job_repository.get_job(job_id)
            if not job_data:
                break
            
            # Get new progress events
            progress_events = get_progress_events(job_id, last_event_timestamp)
            
            # Stream new node progress events
            for event in progress_events:
                stream_event = StreamEvent(
                    event="node_progress",
                    data={
                        "event_type": event.event_type,
                        "node_name": event.node_name,
                        "duration_ms": event.duration_ms
                    },
                    timestamp=event.timestamp
                )
                yield f"data: {stream_event.model_dump_json()}\n\n"
                last_event_timestamp = event.timestamp
            
            # Handle human input requirement
            if job_data.get("awaiting_human") and job_data.get("human_question"):
                async for human_event in self._handle_human_input_streaming(job_id, job_data):
                    yield human_event
                continue
            
            # Check if job is complete - only send completion event with results
            if job_data["status"] in ["completed", "failed", "cancelled"]:
                final_event = StreamEvent(
                    event="job_complete",
                    data={
                        "status": job_data["status"],
                        "error": job_data.get("error"),
                        "cancelled_by_user": job_data.get("cancelled_by_user", False)
                    },
                    timestamp=datetime.now().isoformat()
                )
                yield f"data: {final_event.model_dump_json()}\n\n"
                break
            
            await asyncio.sleep(0.5)  # Fast polling for responsive UI
    
    async def _handle_human_input_streaming(self, job_id: str, job_data: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """Handle human input requirement streaming"""
        human_event = StreamEvent(
            event="human_input_required",
            data={
                "status": "awaiting_human_input",
                "question": job_data["human_question"],
                "query": job_data["query"]
            },
            timestamp=datetime.now().isoformat()
        )
        yield f"data: {human_event.model_dump_json()}\n\n"
        
        # Wait for human response
        while job_data.get("awaiting_human", False):
            await asyncio.sleep(1)
            job_data = await self.job_repository.get_job(job_id)
            if not job_data:
                break