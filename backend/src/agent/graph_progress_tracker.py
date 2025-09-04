"""
Graph Progress Tracking System

A clean abstraction layer that monitors LangGraph execution progress without
polluting the graph code. Works like a logging system but for node transitions.

Features:
- Non-invasive monitoring via LangGraph callbacks
- Tracks main graph + sub-graph node execution  
- Job-specific event queues for concurrent executions
- Clean separation of concerns (monitoring vs business logic)
"""

import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, deque
from threading import Lock


@dataclass
class NodeProgressEvent:
    """Represents a single node execution event"""
    job_id: str
    timestamp: str
    event_type: str  # 'node_start', 'node_end', 'node_error', 'graph_start', 'graph_end'
    node_name: str
    graph_name: str  # 'main' or sub-graph name like 'product-search-subgraph'
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class GraphProgressTracker:
    """
    Thread-safe progress tracker that monitors graph execution without
    modifying the graph code. Uses LangGraph's callback system.
    """
    
    def __init__(self):
        self._job_events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._active_nodes: Dict[str, Dict[str, float]] = defaultdict(dict)  # job_id -> {node_name: start_time}
        self._lock = Lock()
    
    def start_tracking(self, job_id: str) -> None:
        """Initialize tracking for a new job"""
        from agent.web_tracer import info
        info("PROGRESS", f"Starting tracking for job {job_id}", job_id)
        with self._lock:
            self._job_events[job_id].clear()
            self._active_nodes[job_id].clear()
            
        self._add_event(NodeProgressEvent(
            job_id=job_id,
            timestamp=datetime.now().isoformat(),
            event_type="graph_start",
            node_name="__GRAPH_START__",
            graph_name="main"
        ))
        info("PROGRESS", f"Added graph_start event for job {job_id}", job_id)
    
    def on_node_start(self, job_id: str, node_name: str, graph_name: str = "main", **metadata) -> None:
        """Called when a node begins execution"""
        from agent.web_tracer import debug
        debug("PROGRESS", f"Node START: {node_name} in {graph_name}", job_id)
        start_time = time.time()
        
        with self._lock:
            self._active_nodes[job_id][f"{graph_name}:{node_name}"] = start_time
        
        self._add_event(NodeProgressEvent(
            job_id=job_id,
            timestamp=datetime.now().isoformat(),
            event_type="node_start",
            node_name=node_name,
            graph_name=graph_name,
            metadata=metadata
        ))
    
    def on_node_end(self, job_id: str, node_name: str, graph_name: str = "main", **metadata) -> None:
        """Called when a node completes successfully"""
        duration_ms = None
        node_key = f"{graph_name}:{node_name}"
        
        with self._lock:
            if node_key in self._active_nodes[job_id]:
                start_time = self._active_nodes[job_id].pop(node_key)
                duration_ms = int((time.time() - start_time) * 1000)
        
        self._add_event(NodeProgressEvent(
            job_id=job_id,
            timestamp=datetime.now().isoformat(),
            event_type="node_end",
            node_name=node_name,
            graph_name=graph_name,
            duration_ms=duration_ms,
            metadata=metadata
        ))
    
    def on_node_error(self, job_id: str, node_name: str, error: str, graph_name: str = "main", **metadata) -> None:
        """Called when a node encounters an error"""
        duration_ms = None
        node_key = f"{graph_name}:{node_name}"
        
        with self._lock:
            if node_key in self._active_nodes[job_id]:
                start_time = self._active_nodes[job_id].pop(node_key)
                duration_ms = int((time.time() - start_time) * 1000)
        
        self._add_event(NodeProgressEvent(
            job_id=job_id,
            timestamp=datetime.now().isoformat(),
            event_type="node_error",
            node_name=node_name,
            graph_name=graph_name,
            duration_ms=duration_ms,
            error=error,
            metadata=metadata
        ))
    
    def end_tracking(self, job_id: str) -> None:
        """Mark graph execution as complete"""
        self._add_event(NodeProgressEvent(
            job_id=job_id,
            timestamp=datetime.now().isoformat(),
            event_type="graph_end",
            node_name="__GRAPH_END__",
            graph_name="main"
        ))
    
    def get_events(self, job_id: str, since_timestamp: Optional[str] = None) -> List[NodeProgressEvent]:
        """Get all events for a job, optionally filtered by timestamp"""
        with self._lock:
            events = list(self._job_events[job_id])
        
        if since_timestamp:
            # Filter events after the given timestamp
            events = [e for e in events if e.timestamp > since_timestamp]
        
        return events
    
    def get_latest_event(self, job_id: str) -> Optional[NodeProgressEvent]:
        """Get the most recent event for a job"""
        with self._lock:
            events = self._job_events[job_id]
            return events[-1] if events else None
    
    def is_node_active(self, job_id: str, node_name: str, graph_name: str = "main") -> bool:
        """Check if a specific node is currently executing"""
        node_key = f"{graph_name}:{node_name}"
        with self._lock:
            return node_key in self._active_nodes[job_id]
    
    def get_active_nodes(self, job_id: str) -> List[str]:
        """Get list of currently executing nodes"""
        with self._lock:
            return list(self._active_nodes[job_id].keys())
    
    def cleanup_job(self, job_id: str) -> None:
        """Clean up tracking data for a completed job"""
        with self._lock:
            if job_id in self._job_events:
                del self._job_events[job_id]
            if job_id in self._active_nodes:
                del self._active_nodes[job_id]
    
    def _add_event(self, event: NodeProgressEvent) -> None:
        """Thread-safe event addition"""
        with self._lock:
            self._job_events[event.job_id].append(event)


# Global singleton instance
progress_tracker = GraphProgressTracker()


# Convenience functions for easy integration
def start_job_tracking(job_id: str) -> None:
    """Start tracking a new job"""
    progress_tracker.start_tracking(job_id)

def track_node_start(job_id: str, node_name: str, graph_name: str = "main", **metadata) -> None:
    """Track node start event"""
    progress_tracker.on_node_start(job_id, node_name, graph_name, **metadata)

def track_node_end(job_id: str, node_name: str, graph_name: str = "main", **metadata) -> None:
    """Track node completion event"""
    progress_tracker.on_node_end(job_id, node_name, graph_name, **metadata)

def track_node_error(job_id: str, node_name: str, error: str, graph_name: str = "main", **metadata) -> None:
    """Track node error event"""
    progress_tracker.on_node_error(job_id, node_name, error, graph_name, **metadata)

def end_job_tracking(job_id: str) -> None:
    """End tracking for a job"""
    progress_tracker.end_tracking(job_id)

def get_job_progress(job_id: str) -> List[NodeProgressEvent]:
    """Get all progress events for a job"""
    return progress_tracker.get_events(job_id)

def cleanup_job_tracking(job_id: str) -> None:
    """Clean up tracking data for a job"""
    progress_tracker.cleanup_job(job_id)