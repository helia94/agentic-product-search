"""
Job Repository Interface

Defines the contract for job persistence, allowing easy switching between
in-memory storage and database implementations later.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import asyncio


class JobRepository(ABC):
    """Abstract repository interface for job persistence"""
    
    @abstractmethod
    async def save_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        """Save or update job data"""
        pass
    
    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job data by ID"""
        pass
    
    @abstractmethod
    async def update_job_status(self, job_id: str, status: str, **kwargs) -> None:
        """Update job status and optional additional fields"""
        pass
    
    @abstractmethod
    async def job_exists(self, job_id: str) -> bool:
        """Check if job exists"""
        pass
    
    @abstractmethod
    async def set_job_event(self, job_id: str, event: asyncio.Event) -> None:
        """Set cancellation event for active job"""
        pass
    
    @abstractmethod
    async def get_job_event(self, job_id: str) -> Optional[asyncio.Event]:
        """Get cancellation event for job"""
        pass
    
    @abstractmethod
    async def remove_job_event(self, job_id: str) -> None:
        """Remove cancellation event for job"""
        pass
    
    @abstractmethod
    async def is_job_active(self, job_id: str) -> bool:
        """Check if job has active cancellation event"""
        pass