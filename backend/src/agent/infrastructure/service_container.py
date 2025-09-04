"""
Service Container for Dependency Injection

Simple DI container that wires up all the application services.
Follows best practices for dependency injection without external libraries.
"""

from agent.domain.repositories.job_repository import JobRepository
from agent.infrastructure.repositories.in_memory_job_repository import InMemoryJobRepository
from agent.application.search_job_service import SearchJobService
from agent.application.product_search_service import ProductSearchService
from agent.application.progress_streaming_service import ProgressStreamingService


class ServiceContainer:
    """
    Dependency injection container for application services
    
    Responsible for creating and wiring all dependencies in the correct order.
    Uses constructor injection pattern for clean testability.
    """
    
    def __init__(self):
        """Initialize container and wire up all dependencies"""
        
        # Infrastructure layer - Repository
        self._job_repository: JobRepository = InMemoryJobRepository()
        
        # Application layer - Services
        self._product_search_service = ProductSearchService(self._job_repository)
        self._search_job_service = SearchJobService(self._job_repository)  
        self._progress_streaming_service = ProgressStreamingService(self._job_repository)
    
    # Public accessors for services
    @property
    def job_repository(self) -> JobRepository:
        """Get the job repository instance"""
        return self._job_repository
    
    @property 
    def search_job_service(self) -> SearchJobService:
        """Get the search job service instance"""
        return self._search_job_service
    
    @property
    def product_search_service(self) -> ProductSearchService:
        """Get the product search service instance"""
        return self._product_search_service
    
    @property
    def progress_streaming_service(self) -> ProgressStreamingService:
        """Get the progress streaming service instance"""
        return self._progress_streaming_service
    
    # Factory method for easy testing/swapping implementations
    @classmethod
    def create_with_custom_repository(cls, job_repository: JobRepository) -> 'ServiceContainer':
        """
        Factory method to create container with custom repository implementation
        
        Useful for testing or switching to database implementation later
        """
        container = cls.__new__(cls)  # Create without calling __init__
        
        # Wire up with custom repository
        container._job_repository = job_repository
        container._product_search_service = ProductSearchService(job_repository)
        container._search_job_service = SearchJobService(job_repository)
        container._progress_streaming_service = ProgressStreamingService(job_repository)
        
        return container