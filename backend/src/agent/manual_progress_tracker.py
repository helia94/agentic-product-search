"""
Manual Progress Tracking for LangGraph

Since LangGraph nodes don't trigger LangChain callbacks reliably,
this module provides direct progress tracking by wrapping node functions.
"""

import functools
from typing import Dict, Any, Callable
from agent.graph_progress_tracker import track_node_start, track_node_end, track_node_error
from agent.tracing import get_tracer, add_span_attribute, add_span_event


def track_progress(node_name: str, graph_name: str = "main"):
    """
    Decorator to track progress of individual graph nodes.
    
    Usage:
        @track_progress("pars_query", "product-search-main")
        def pars_query(state, config):
            # ... node logic
            return result
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(state: Dict[str, Any], config: Dict[str, Any]):
            # Extract job_id from config
            job_id = config.get("configurable", {}).get("thread_id", "unknown")
            
            print(f"🔄 [MANUAL_TRACK] Starting {node_name} for job {job_id}")
            track_node_start(job_id, node_name, graph_name)
            
            try:
                # Check function signature to determine if it accepts config
                import inspect
                sig = inspect.signature(func)
                
                if len(sig.parameters) > 1:
                    # Function accepts both state and config
                    result = func(state, config)
                else:
                    # Function only accepts state
                    result = func(state)
                print(f"✅ [MANUAL_TRACK] Completed {node_name} for job {job_id}")
                track_node_end(job_id, node_name, graph_name)
                return result
            except Exception as e:
                print(f"❌ [MANUAL_TRACK] Error in {node_name} for job {job_id}: {str(e)}")
                track_node_error(job_id, node_name, str(e), graph_name)
                raise
        
        return wrapper
    return decorator


def create_tracked_node_wrapper(original_func: Callable, node_name: str, graph_name: str = "main") -> Callable:
    """
    Create a wrapped version of a node function that tracks progress.
    
    Args:
        original_func: The original node function
        node_name: Name of the node for tracking
        graph_name: Name of the graph
    
    Returns:
        Wrapped function with progress tracking
    """
    @functools.wraps(original_func)
    def wrapper(state: Dict[str, Any], config: Dict[str, Any] = None):
        # Handle both LangGraph and direct calls
        if config is None:
            config = {"configurable": {"thread_id": "direct_call"}}
        
        # Extract job_id from config
        job_id = config.get("configurable", {}).get("thread_id", "unknown")
        
        from agent.web_tracer import info, error as log_error
        
        # Start OpenTelemetry span for this node
        tracer = get_tracer()
        with tracer.start_as_current_span(f"{graph_name}:{node_name}"):
            add_span_attribute("node_name", node_name)
            add_span_attribute("graph_name", graph_name)
            add_span_attribute("job_id", job_id)
            
            info("GRAPH", f"Starting {node_name}", job_id)
            track_node_start(job_id, node_name, graph_name)
            add_span_event("node_started", {"node": node_name})
            
            try:
                # Call original function with appropriate arguments
                # Check function signature to determine if it accepts config
                import inspect
                sig = inspect.signature(original_func)
                
                if len(sig.parameters) > 1:
                    # Function accepts both state and config
                    result = original_func(state, config)
                else:
                    # Function only accepts state
                    result = original_func(state)
                
                info("GRAPH", f"Completed {node_name}", job_id)
                track_node_end(job_id, node_name, graph_name)
                add_span_event("node_completed", {"node": node_name})
                return result
            except Exception as e:
                log_error("GRAPH", f"Error in {node_name}: {str(e)}", job_id)
                track_node_error(job_id, node_name, str(e), graph_name)
                add_span_event("node_error", {"node": node_name, "error": str(e)})
                raise
    
    return wrapper