"""
Clean streaming API for frontend progress updates.
Pure business logic, no tracing/debugging concerns.
"""

import asyncio
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from pydantic import BaseModel

from agent.node_progress import get_progress_events, NodeEvent


class StreamEvent(BaseModel):
    """API event model for frontend"""
    event: str
    data: Dict[str, Any]
    timestamp: str


class JobProgressStreamer:
    """Clean job progress streaming for frontend"""
    
    def __init__(self, running_jobs: Dict[str, Dict[str, Any]]):
        self.running_jobs = running_jobs
    
    async def stream_job_progress(self, job_id: str) -> AsyncGenerator[str, None]:
        """
        Stream job progress events to frontend.
        Clean business logic only - no debug/trace pollution.
        """
        if job_id not in self.running_jobs:
            return
        
        last_event_timestamp = None
        
        while True:
            job_info = self.running_jobs.get(job_id)
            if not job_info:
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
            if job_info.get("awaiting_human") and job_info.get("human_question"):
                async for human_event in self._handle_human_input_streaming(job_id, job_info):
                    yield human_event
                continue
            
            # Stream job status update
            status_event = StreamEvent(
                event="status_update",
                data={
                    "status": job_info["status"],
                    "query": job_info["query"],
                    "html_file_path": job_info.get("html_file_path"),
                    "error": job_info.get("error")
                },
                timestamp=datetime.now().isoformat()
            )
            yield f"data: {status_event.model_dump_json()}\n\n"
            
            # Check if job is complete
            if job_info["status"] in ["completed", "failed", "cancelled"]:
                final_event = StreamEvent(
                    event="job_complete",
                    data={
                        "status": job_info["status"],
                        "html_file_path": job_info.get("html_file_path"),
                        "error": job_info.get("error"),
                        "cancelled_by_user": job_info.get("cancelled_by_user", False)
                    },
                    timestamp=datetime.now().isoformat()
                )
                yield f"data: {final_event.model_dump_json()}\n\n"
                break
            
            await asyncio.sleep(0.5)  # Fast polling for responsive UI
    
    async def _handle_human_input_streaming(self, job_id: str, job_info: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """Handle human input requirement streaming"""
        human_event = StreamEvent(
            event="human_input_required",
            data={
                "status": "awaiting_human_input",
                "question": job_info["human_question"],
                "query": job_info["query"]
            },
            timestamp=datetime.now().isoformat()
        )
        yield f"data: {human_event.model_dump_json()}\n\n"
        
        # Wait for human response
        while job_info.get("awaiting_human", False):
            await asyncio.sleep(1)
            job_info = self.running_jobs.get(job_id)
            if not job_info:
                break