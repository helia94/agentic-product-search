"""
Graph Execution Wrapper

Provides a clean interface to execute LangGraph with automatic progress tracking.
Uses LangGraph's built-in callback system to monitor execution without modifying graph code.
"""

from typing import Any, Dict, Optional, Callable
from langgraph.graph import StateGraph
from langgraph.types import PregelTask
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from agent.tracing.node_progress import (
    get_progress_events, 
    cleanup_progress
)


# Simplified - progress tracking now handled by decorators
class GraphProgressCallbackHandler(BaseCallbackHandler):
    """
    Minimal callback handler since progress tracking is handled by decorators.
    """
    
    def __init__(self, job_id: str, graph_name: str = "main"):
        super().__init__()
        self.job_id = job_id
        self.graph_name = graph_name


class TrackedGraphExecutor:
    """
    Wrapper for LangGraph execution with automatic progress tracking.
    Provides the same interface as direct graph.invoke() but with monitoring.
    """
    
    def __init__(self, graph: StateGraph, graph_name: str = "main"):
        self.graph = graph
        self.graph_name = graph_name
    
    def invoke(self, initial_state: Dict[str, Any], config: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """
        Execute the graph with progress tracking.
        
        Args:
            initial_state: Initial state to pass to the graph
            config: LangGraph configuration (thread_id, etc.)
            job_id: Unique identifier for this execution job
        
        Returns:
            Final state after graph execution
        """
        # Execute the graph - progress tracking handled by decorators
        try:
            result_state = self.graph.invoke(initial_state, config=config)
            return result_state
        except Exception as e:
            print(f"Graph execution error for job {job_id}: {e}")
            raise
    
    async def ainvoke(self, initial_state: Dict[str, Any], config: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """
        Async version of invoke with progress tracking.
        """
        try:
            result_state = await self.graph.ainvoke(initial_state, config=config)
            return result_state
        except Exception as e:
            print(f"Async graph execution error for job {job_id}: {e}")
            raise
    
    async def astream(self, initial_state: Dict[str, Any], config: Dict[str, Any], job_id: str):
        """
        Async streaming version with cancellation support.
        """
        try:
            # Stream the graph execution
            async for chunk in self.graph.astream(initial_state, config=config):
                yield chunk
        except Exception as e:
            print(f"Async streaming error for job {job_id}: {e}")
            raise


def create_tracked_executor(graph: StateGraph, graph_name: str = "main") -> TrackedGraphExecutor:
    """
    Factory function to create a tracked graph executor.
    
    Usage:
        tracked_graph = create_tracked_executor(your_graph, "product-search-main")
        result = tracked_graph.invoke(initial_state, config, job_id)
    """
    return TrackedGraphExecutor(graph, graph_name)