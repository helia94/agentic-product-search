"""
Web-based tracing and logging system for FastAPI debugging.
Captures all debug messages and provides a web UI to view them in real-time.
"""

import time
from datetime import datetime
from typing import List, Dict, Any
from collections import deque
from threading import Lock
from dataclasses import dataclass, asdict


@dataclass
class LogEntry:
    timestamp: str
    level: str  # DEBUG, INFO, WARN, ERROR
    category: str  # GRAPH, PROGRESS, WRAPPER, API, etc.
    message: str
    job_id: str = ""
    metadata: Dict[str, Any] = None

    def to_dict(self):
        return asdict(self)


class WebTracer:
    """Thread-safe web tracer that captures logs for real-time viewing"""
    
    def __init__(self, max_logs: int = 1000):
        self._logs: deque = deque(maxlen=max_logs)
        self._lock = Lock()
    
    def log(self, level: str, category: str, message: str, job_id: str = "", **metadata):
        """Add a log entry"""
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level.upper(),
            category=category.upper(),
            message=message,
            job_id=job_id,
            metadata=metadata if metadata else None
        )
        
        with self._lock:
            self._logs.append(entry)
        
        # Also print to console for backup
        prefix = f"[{entry.level}] [{entry.category}]"
        if job_id:
            prefix += f" [Job: {job_id}]"
        print(f"{prefix} {message}")
    
    def get_logs(self, since: str = None, job_id: str = None, category: str = None) -> List[Dict[str, Any]]:
        """Get logs with optional filtering"""
        with self._lock:
            logs = list(self._logs)
        
        # Apply filters
        if since:
            logs = [log for log in logs if log.timestamp > since]
        
        if job_id:
            logs = [log for log in logs if log.job_id == job_id]
        
        if category:
            logs = [log for log in logs if log.category == category.upper()]
        
        return [log.to_dict() for log in logs]
    
    def clear_logs(self):
        """Clear all logs"""
        with self._lock:
            self._logs.clear()
    
    def debug(self, category: str, message: str, job_id: str = "", **metadata):
        """Debug level log"""
        self.log("DEBUG", category, message, job_id, **metadata)
    
    def info(self, category: str, message: str, job_id: str = "", **metadata):
        """Info level log"""
        self.log("INFO", category, message, job_id, **metadata)
    
    def warn(self, category: str, message: str, job_id: str = "", **metadata):
        """Warning level log"""
        self.log("WARN", category, message, job_id, **metadata)
    
    def error(self, category: str, message: str, job_id: str = "", **metadata):
        """Error level log"""
        self.log("ERROR", category, message, job_id, **metadata)


# Global tracer instance
tracer = WebTracer()

# Convenience functions
def debug(category: str, message: str, job_id: str = "", **metadata):
    tracer.debug(category, message, job_id, **metadata)

def info(category: str, message: str, job_id: str = "", **metadata):
    tracer.info(category, message, job_id, **metadata)

def warn(category: str, message: str, job_id: str = "", **metadata):
    tracer.warn(category, message, job_id, **metadata)

def error(category: str, message: str, job_id: str = "", **metadata):
    tracer.error(category, message, job_id, **metadata)

def get_logs(since: str = None, job_id: str = None, category: str = None) -> List[Dict[str, Any]]:
    return tracer.get_logs(since, job_id, category)

def clear_logs():
    tracer.clear_logs()