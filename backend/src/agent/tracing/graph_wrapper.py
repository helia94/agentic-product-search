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

from agent.tracing.graph_progress_tracker import (
    start_job_tracking, 
    track_node_start, 
    track_node_end, 
    track_node_error, 
    end_job_tracking
)


class GraphProgressCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler that automatically tracks graph execution progress.
    Integrates seamlessly with LangGraph without requiring code changes to nodes.
    """
    
    def __init__(self, job_id: str, graph_name: str = "main"):
        super().__init__()
        self.job_id = job_id
        self.graph_name = graph_name
        self.current_node = None
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """Called when a tool (node) starts execution"""
        tool_name = serialized.get("name", "unknown_tool")
        
        # LangGraph nodes appear as tools in the callback system
        if self.current_node != tool_name:
            self.current_node = tool_name
            track_node_start(
                job_id=self.job_id,
                node_name=tool_name,
                graph_name=self.graph_name,
                input_preview=input_str[:200] if input_str else ""
            )
    
    def on_tool_end(self, output: str, **kwargs) -> None:
        """Called when a tool (node) completes execution"""
        if self.current_node:
            track_node_end(
                job_id=self.job_id,
                node_name=self.current_node,
                graph_name=self.graph_name,
                output_preview=output[:200] if output else ""
            )
            self.current_node = None
    
    def on_tool_error(self, error: Exception, **kwargs) -> None:
        """Called when a tool (node) encounters an error"""
        if self.current_node:
            track_node_error(
                job_id=self.job_id,
                node_name=self.current_node,
                error=str(error),
                graph_name=self.graph_name
            )
            self.current_node = None
    
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs) -> None:
        """Called when a chain (potentially a sub-graph) starts"""
        chain_name = serialized.get("name", "")
        if "graph" in chain_name.lower() or "agent" in chain_name.lower():
            # This might be a sub-graph
            track_node_start(
                job_id=self.job_id,
                node_name=chain_name,
                graph_name=self.graph_name,
                input_keys=list(inputs.keys()) if inputs else []
            )
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs) -> None:
        """Called when a chain completes"""
        # This is handled by on_tool_end for most cases
        pass
    
    def on_chain_error(self, error: Exception, **kwargs) -> None:
        """Called when a chain encounters an error"""
        if self.current_node:
            track_node_error(
                job_id=self.job_id,
                node_name=self.current_node,
                error=str(error),
                graph_name=self.graph_name
            )


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
        from agent.tracing.web_tracer import info
        info("WRAPPER", f"Starting tracked execution for job {job_id}", job_id)
        
        # Start tracking this job
        start_job_tracking(job_id)
        
        try:
            # Create callback handler for this execution
            callback_handler = GraphProgressCallbackHandler(job_id, self.graph_name)
            info("WRAPPER", f"Created callback handler for {self.graph_name}", job_id)
            
            # Add callback to config
            execution_config = config.copy()
            if "callbacks" not in execution_config:
                execution_config["callbacks"] = []
            execution_config["callbacks"].append(callback_handler)
            
            info("WRAPPER", f"Config callbacks count: {len(execution_config['callbacks'])}", job_id)
            info("WRAPPER", f"Executing graph.invoke() for job {job_id}", job_id)
            
            # Execute the graph with progress tracking
            result_state = self.graph.invoke(initial_state, config=execution_config)
            
            info("WRAPPER", f"Graph.invoke() completed for job {job_id}", job_id)
            
            # Mark successful completion
            end_job_tracking(job_id)
            
            return result_state
            
        except Exception as e:
            # Track the error
            track_node_error(
                job_id=job_id,
                node_name="__GRAPH_ERROR__",
                error=str(e),
                graph_name=self.graph_name
            )
            end_job_tracking(job_id)
            raise
    
    async def ainvoke(self, initial_state: Dict[str, Any], config: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """
        Async version of invoke with progress tracking.
        """
        # Start tracking this job
        start_job_tracking(job_id)
        
        try:
            # Create callback handler for this execution
            callback_handler = GraphProgressCallbackHandler(job_id, self.graph_name)
            
            # Add callback to config
            execution_config = config.copy()
            if "callbacks" not in execution_config:
                execution_config["callbacks"] = []
            execution_config["callbacks"].append(callback_handler)
            
            # Execute the graph with progress tracking
            result_state = await self.graph.ainvoke(initial_state, config=execution_config)
            
            # Mark successful completion
            end_job_tracking(job_id)
            
            return result_state
            
        except Exception as e:
            # Track the error
            track_node_error(
                job_id=job_id,
                node_name="__GRAPH_ERROR__",
                error=str(e),
                graph_name=self.graph_name
            )
            end_job_tracking(job_id)
            raise


def create_tracked_executor(graph: StateGraph, graph_name: str = "main") -> TrackedGraphExecutor:
    """
    Factory function to create a tracked graph executor.
    
    Usage:
        tracked_graph = create_tracked_executor(your_graph, "product-search-main")
        result = tracked_graph.invoke(initial_state, config, job_id)
    """
    return TrackedGraphExecutor(graph, graph_name)