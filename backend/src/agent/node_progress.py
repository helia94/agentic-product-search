"""
Clean node progress tracking for streaming API.
Completely separated from tracing/debugging concerns.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict, deque
from threading import Lock
import functools


@dataclass
class NodeEvent:
    """Simple node execution event for frontend streaming"""
    job_id: str
    timestamp: str
    event_type: str  # 'node_start', 'node_end'
    node_name: str
    duration_ms: Optional[int] = None


class NodeProgressTracker:
    """Minimal, thread-safe progress tracker for business logic only"""
    
    def __init__(self):
        self._job_events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._node_start_times: Dict[str, float] = {}
        self._lock = Lock()
    
    def track_node_start(self, job_id: str, node_name: str) -> None:
        """Record node start"""
        start_time = time.time()
        node_key = f"{job_id}:{node_name}"
        
        with self._lock:
            self._node_start_times[node_key] = start_time
            event = NodeEvent(
                job_id=job_id,
                timestamp=datetime.now().isoformat(),
                event_type="node_start",
                node_name=node_name
            )
            self._job_events[job_id].append(event)
    
    def track_node_end(self, job_id: str, node_name: str) -> None:
        """Record node completion with timing"""
        node_key = f"{job_id}:{node_name}"
        duration_ms = None
        
        with self._lock:
            if node_key in self._node_start_times:
                start_time = self._node_start_times.pop(node_key)
                duration_ms = int((time.time() - start_time) * 1000)
            
            event = NodeEvent(
                job_id=job_id,
                timestamp=datetime.now().isoformat(),
                event_type="node_end",
                node_name=node_name,
                duration_ms=duration_ms
            )
            self._job_events[job_id].append(event)
    
    def get_new_events(self, job_id: str, since_timestamp: Optional[str] = None) -> List[NodeEvent]:
        """Get events since timestamp"""
        with self._lock:
            events = list(self._job_events[job_id])
        
        if since_timestamp:
            events = [e for e in events if e.timestamp > since_timestamp]
        
        return events
    
    def cleanup_job(self, job_id: str) -> None:
        """Clean up job data"""
        with self._lock:
            if job_id in self._job_events:
                del self._job_events[job_id]
            # Clean up any remaining start times
            keys_to_remove = [k for k in self._node_start_times.keys() if k.startswith(f"{job_id}:")]
            for key in keys_to_remove:
                del self._node_start_times[key]


# Global tracker instance
_progress_tracker = NodeProgressTracker()


def track_node_progress(node_name: str):
    """
    Decorator to track node progress without polluting business logic.
    
    Usage:
        @track_node_progress("pars_query")
        def pars_query(state, config=None):
            # business logic here
            return updated_state
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(state: Dict[str, Any], config: Dict[str, Any] = None):
            # Extract job_id from config
            if config is None:
                config = {"configurable": {"thread_id": "unknown"}}
            
            job_id = config.get("configurable", {}).get("thread_id", "unknown")
            
            # Track start
            _progress_tracker.track_node_start(job_id, node_name)
            
            try:
                # Execute business logic
                result = func(state, config)
                # Track completion
                _progress_tracker.track_node_end(job_id, node_name)
                return result
            except Exception as e:
                # Still track end on error (with timing)
                _progress_tracker.track_node_end(job_id, node_name)
                raise
        
        return wrapper
    return decorator


# Public API functions
def get_progress_events(job_id: str, since_timestamp: Optional[str] = None) -> List[NodeEvent]:
    """Get progress events for streaming"""
    return _progress_tracker.get_new_events(job_id, since_timestamp)


def cleanup_progress(job_id: str) -> None:
    """Cleanup progress data"""
    _progress_tracker.cleanup_job(job_id)