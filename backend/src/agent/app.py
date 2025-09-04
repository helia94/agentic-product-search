# mypy: disable - error - code = "no-untyped-def,misc"
import pathlib
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import fastapi.exceptions
import asyncio
from contextlib import asynccontextmanager

# Import our graph and configuration functions
from agent.graph_v2 import (
    graph
)
from agent.state_V2 import OverallState
from agent.graph_wrapper import create_tracked_executor
from agent.graph_progress_tracker import get_job_progress, cleanup_job_tracking
from agent.web_tracer import get_logs, clear_logs, info, debug, warn, error
from agent.tracing import configure_tracing, get_tracer, add_span_attribute, add_span_event

# Request/Response models
class ProductSearchRequest(BaseModel):
    query: str
    effort: str = "medium"  # "low", "medium", "high"

class HumanResponse(BaseModel):
    job_id: str
    answer: str

class StreamEvent(BaseModel):
    event: str
    data: Dict[str, Any]
    timestamp: str

# Global state to track running jobs
running_jobs: Dict[str, Dict[str, Any]] = {}

# Create tracked executor for progress monitoring
tracked_graph = create_tracked_executor(graph, "product-search-main")

# Define the FastAPI app with lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[API] Product Search API starting up...")
    yield
    # Shutdown
    print("[API] Product Search API shutting down...")

app = FastAPI(lifespan=lifespan)

# Configure OpenTelemetry tracing
tracer = configure_tracing(app, "product-search-api")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add main section for running with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Health check endpoint
@app.get("/api/health")
async def health_check():
    with tracer.start_as_current_span("health_check"):
        add_span_attribute("endpoint", "/api/health")
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Test endpoint to verify web tracer is working
@app.get("/api/debug/test")
async def debug_test():
    """Add test logs to verify web tracer functionality"""
    with tracer.start_as_current_span("debug_test"):
        add_span_attribute("endpoint", "/api/debug/test")
        info("API", "Test endpoint called", "test-endpoint")
        debug("SYSTEM", "Debug level test message", "test-endpoint") 
        warn("WARNING", "Warning level test message", "test-endpoint")
        add_span_event("test_logs_added", {"count": 3})
        return {"status": "Test logs added", "timestamp": datetime.now().isoformat()}


def create_frontend_router(build_dir="../frontend/dist"):
    """Creates a router to serve the React frontend.

    Args:
        build_dir: Path to the React build directory relative to this file.

    Returns:
        A Starlette application serving the frontend.
    """
    build_path = pathlib.Path(__file__).parent.parent.parent / build_dir
    static_files_path = build_path / "assets"  # Vite uses 'assets' subdir

    if not build_path.is_dir() or not (build_path / "index.html").is_file():
        print(
            f"WARN: Frontend build directory not found or incomplete at {build_path}. Serving frontend will likely fail."
        )
        # Return a dummy router if build isn't ready
        from starlette.routing import Route

        async def dummy_frontend(request):
            return Response(
                "Frontend not built. Run 'npm run build' in the frontend directory.",
                media_type="text/plain",
                status_code=503,
            )

        return Route("/{path:path}", endpoint=dummy_frontend)

    build_dir = pathlib.Path(build_dir)

    react = FastAPI(openapi_url="")
    react.mount(
        "/assets", StaticFiles(directory=static_files_path), name="static_assets"
    )

    @react.get("/{path:path}")
    async def handle_catch_all(request: Request, path: str):
        fp = build_path / path
        if not fp.exists() or not fp.is_file():
            fp = build_path / "index.html"
        return fastapi.responses.FileResponse(fp)

    return react


# API Routes

@app.post("/api/search")
async def start_product_search(request: ProductSearchRequest):
    """
    Start a product search and return a job ID for streaming updates.
    """
    with tracer.start_as_current_span("start_product_search"):
        job_id = str(uuid.uuid4())
        
        add_span_attribute("job_id", job_id)
        add_span_attribute("query", request.query)
        add_span_attribute("effort", request.effort)
        
        # Store job info
        running_jobs[job_id] = {
            "status": "starting",
            "query": request.query,
            "start_time": datetime.now().isoformat(),
            "html_file_path": None,
            "error": None
        }
        
        # Start the graph execution in background
        asyncio.create_task(run_graph_async(job_id, request))
        
        add_span_event("job_started", {"job_id": job_id})
        return {"job_id": job_id, "status": "started"}


@app.get("/api/search/{job_id}/stream")
async def stream_search_progress(job_id: str):
    """
    Stream progress updates for a running search job.
    """
    if job_id not in running_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    async def event_generator():
        last_progress_timestamp = None
        
        while True:
            job_info = running_jobs.get(job_id)
            if not job_info:
                break
            
            # Stream progress events from graph execution
            progress_events = get_job_progress(job_id)
            
            # Filter to only new progress events
            new_progress_events = []
            if progress_events:
                if last_progress_timestamp is None:
                    new_progress_events = progress_events
                else:
                    new_progress_events = [e for e in progress_events if e.timestamp > last_progress_timestamp]
                
                # Update last timestamp
                if new_progress_events:
                    last_progress_timestamp = new_progress_events[-1].timestamp
            
            # Send new progress events
            for progress_event in new_progress_events:
                event = StreamEvent(
                    event="node_progress",
                    data={
                        "event_type": progress_event.event_type,
                        "node_name": progress_event.node_name,
                        "graph_name": progress_event.graph_name,
                        "duration_ms": progress_event.duration_ms,
                        "error": progress_event.error,
                        "metadata": progress_event.metadata
                    },
                    timestamp=progress_event.timestamp
                )
                yield f"data: {event.model_dump_json()}\n\n"
            
            # Check if human input is needed
            if job_info.get("awaiting_human") and job_info.get("human_question"):
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
                
                # Wait for human response (keep streaming status updates)
                while job_info.get("awaiting_human", False):
                    await asyncio.sleep(1)
                    job_info = running_jobs.get(job_id)
                    if not job_info:
                        break
                
                # Human responded, continue with normal status updates
                continue
            
            # Send current status
            event = StreamEvent(
                event="status_update",
                data={
                    "status": job_info["status"],
                    "query": job_info["query"],
                    "html_file_path": job_info.get("html_file_path"),
                    "error": job_info.get("error")
                },
                timestamp=datetime.now().isoformat()
            )
            
            yield f"data: {event.model_dump_json()}\n\n"
            
            # If job is complete, send final event and break
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
                
                # Clean up progress tracking after a delay
                asyncio.create_task(cleanup_progress_after_delay(job_id))
                break
            
            await asyncio.sleep(1)  # Check more frequently for progress updates
    
    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )


@app.get("/api/results/{filename}")
async def serve_html_result(filename: str):
    """
    Serve the generated HTML results file.
    """
    file_path = pathlib.Path("results") / filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Result file not found")
    
    return FileResponse(
        file_path,
        media_type="text/html",
        filename=filename
    )


@app.get("/api/search/{job_id}/status")
async def get_search_status(job_id: str):
    """
    Get the current status of a search job.
    """
    if job_id not in running_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return running_jobs[job_id]


@app.post("/api/human-response")
async def submit_human_response(response: HumanResponse):
    """
    Submit a human response to continue graph execution.
    """
    job_id = response.job_id
    
    if job_id not in running_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_info = running_jobs[job_id]
    
    if not job_info.get("awaiting_human"):
        raise HTTPException(status_code=400, detail="Job is not awaiting human input")
    
    # Store the human answer and clear the awaiting flag
    job_info["human_answer"] = response.answer
    job_info["awaiting_human"] = False
    
    # Resume graph execution by triggering the resume logic
    asyncio.create_task(resume_graph_with_human_input(job_id, response.answer))
    
    return {"status": "response_received", "job_id": job_id}


@app.post("/api/search/{job_id}/stop")
async def stop_search_job(job_id: str):
    """
    Stop a running search job.
    """
    if job_id not in running_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_info = running_jobs[job_id]
    
    # Check if job is already completed or failed
    if job_info["status"] in ["completed", "failed", "cancelled"]:
        return {"status": "already_finished", "job_id": job_id, "current_status": job_info["status"]}
    
    # Mark the job as cancelled
    job_info["status"] = "cancelled"
    job_info["end_time"] = datetime.now().isoformat()
    job_info["cancelled_by_user"] = True
    
    # Note: The actual graph execution can't be easily interrupted mid-execution
    # since it's running synchronously, but we mark it as cancelled so the
    # streaming API knows to stop and the frontend can show the cancelled state
    
    return {"status": "cancelled", "job_id": job_id}


# Debug/Tracing Endpoints
@app.get("/api/debug/logs")
async def get_debug_logs(since: Optional[str] = None, job_id: Optional[str] = None, category: Optional[str] = None):
    """
    Get debug logs with optional filtering.
    """
    return {"logs": get_logs(since=since, job_id=job_id, category=category)}


@app.delete("/api/debug/logs")
async def clear_debug_logs():
    """
    Clear all debug logs.
    """
    clear_logs()
    return {"status": "cleared"}


@app.get("/api/debug/ui")
async def debug_ui():
    """
    Serve the debug UI page.
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FastAPI Debug Tracer</title>
        <style>
            body { 
                font-family: 'Courier New', monospace; 
                background: #1a1a1a; 
                color: #e0e0e0; 
                margin: 0; 
                padding: 20px; 
            }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { 
                background: #2d2d2d; 
                padding: 15px; 
                border-radius: 5px; 
                margin-bottom: 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .controls { display: flex; gap: 10px; align-items: center; }
            .controls select, .controls input, .controls button {
                padding: 5px 10px;
                background: #404040;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
            }
            .controls button {
                cursor: pointer;
                background: #0066cc;
            }
            .controls button:hover { background: #0052a3; }
            .controls button.clear { background: #cc0000; }
            .controls button.clear:hover { background: #a30000; }
            .log-container {
                background: #0d1117;
                border: 1px solid #30363d;
                border-radius: 5px;
                height: 600px;
                overflow-y: auto;
                padding: 10px;
            }
            .log-entry {
                margin-bottom: 8px;
                padding: 8px;
                border-radius: 3px;
                font-size: 12px;
                line-height: 1.4;
            }
            .log-entry.DEBUG { background: #1a1a2e; border-left: 3px solid #4dabf7; }
            .log-entry.INFO { background: #1a2e1a; border-left: 3px solid #51cf66; }
            .log-entry.WARN { background: #2e1a1a; border-left: 3px solid #ffd43b; }
            .log-entry.ERROR { background: #2e1a1a; border-left: 3px solid #ff6b6b; }
            .timestamp { color: #8b949e; font-size: 11px; }
            .level { font-weight: bold; }
            .category { 
                background: #373e47; 
                padding: 2px 6px; 
                border-radius: 2px; 
                font-size: 10px; 
                margin: 0 5px;
            }
            .job-id { 
                background: #2d1b69; 
                color: #c9d1d9; 
                padding: 2px 6px; 
                border-radius: 2px; 
                font-size: 10px;
                margin: 0 5px;
            }
            .message { margin-top: 5px; }
            .stats { 
                font-size: 12px; 
                color: #8b949e; 
                display: flex; 
                gap: 15px; 
            }
            .auto-scroll { 
                display: flex; 
                align-items: center; 
                gap: 5px; 
                color: #8b949e; 
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔍 FastAPI Debug Tracer</h1>
                <div class="stats">
                    <span>Total Logs: <span id="totalCount">0</span></span>
                    <span>Filtered: <span id="filteredCount">0</span></span>
                    <span>Last Update: <span id="lastUpdate">-</span></span>
                </div>
            </div>
            
            <div class="controls">
                <select id="categoryFilter">
                    <option value="">All Categories</option>
                    <option value="GRAPH">GRAPH</option>
                    <option value="PROGRESS">PROGRESS</option>
                    <option value="WRAPPER">WRAPPER</option>
                    <option value="API">API</option>
                    <option value="DEBUG">DEBUG</option>
                </select>
                
                <select id="levelFilter">
                    <option value="">All Levels</option>
                    <option value="DEBUG">DEBUG</option>
                    <option value="INFO">INFO</option>
                    <option value="WARN">WARN</option>
                    <option value="ERROR">ERROR</option>
                </select>
                
                <input type="text" id="jobFilter" placeholder="Job ID filter..." />
                
                <button id="refreshBtn">🔄 Refresh</button>
                <button id="clearBtn" class="clear">🗑️ Clear Logs</button>
                
                <div class="auto-scroll">
                    <input type="checkbox" id="autoScroll" checked />
                    <label for="autoScroll">Auto-scroll</label>
                </div>
                
                <div class="auto-scroll">
                    <input type="checkbox" id="autoRefresh" checked />
                    <label for="autoRefresh">Auto-refresh (2s)</label>
                </div>
            </div>
            
            <div class="log-container" id="logContainer">
                <div style="text-align: center; color: #8b949e; padding: 50px;">
                    Loading logs...
                </div>
            </div>
        </div>

        <script>
            let logs = [];
            let lastUpdate = null;
            let autoRefreshInterval = null;

            function formatTimestamp(timestamp) {
                return new Date(timestamp).toLocaleTimeString();
            }

            function renderLogs() {
                const container = document.getElementById('logContainer');
                const categoryFilter = document.getElementById('categoryFilter').value;
                const levelFilter = document.getElementById('levelFilter').value;
                const jobFilter = document.getElementById('jobFilter').value.toLowerCase();

                let filteredLogs = logs.filter(log => {
                    if (categoryFilter && log.category !== categoryFilter) return false;
                    if (levelFilter && log.level !== levelFilter) return false;
                    if (jobFilter && !log.job_id.toLowerCase().includes(jobFilter)) return false;
                    return true;
                });

                document.getElementById('totalCount').textContent = logs.length;
                document.getElementById('filteredCount').textContent = filteredLogs.length;

                if (filteredLogs.length === 0) {
                    container.innerHTML = '<div style="text-align: center; color: #8b949e; padding: 50px;">No logs found</div>';
                    return;
                }

                const html = filteredLogs.map(log => `
                    <div class="log-entry ${log.level}">
                        <div>
                            <span class="timestamp">${formatTimestamp(log.timestamp)}</span>
                            <span class="level ${log.level}">${log.level}</span>
                            <span class="category">${log.category}</span>
                            ${log.job_id ? `<span class="job-id">${log.job_id}</span>` : ''}
                        </div>
                        <div class="message">${log.message}</div>
                    </div>
                `).join('');

                container.innerHTML = html;

                if (document.getElementById('autoScroll').checked) {
                    container.scrollTop = container.scrollHeight;
                }
            }

            async function fetchLogs() {
                try {
                    const params = new URLSearchParams();
                    if (lastUpdate) params.set('since', lastUpdate);
                    
                    const response = await fetch(`/api/debug/logs?${params}`);
                    const data = await response.json();
                    
                    if (lastUpdate) {
                        // Append new logs
                        logs.push(...data.logs);
                        // Keep only last 1000 logs in browser
                        if (logs.length > 1000) {
                            logs = logs.slice(-1000);
                        }
                    } else {
                        // First load
                        logs = data.logs;
                    }
                    
                    if (data.logs.length > 0) {
                        lastUpdate = data.logs[data.logs.length - 1].timestamp;
                    }
                    
                    renderLogs();
                    document.getElementById('lastUpdate').textContent = formatTimestamp(new Date().toISOString());
                } catch (error) {
                    console.error('Failed to fetch logs:', error);
                }
            }

            async function clearLogs() {
                if (confirm('Are you sure you want to clear all logs?')) {
                    try {
                        await fetch('/api/debug/logs', { method: 'DELETE' });
                        logs = [];
                        lastUpdate = null;
                        renderLogs();
                    } catch (error) {
                        console.error('Failed to clear logs:', error);
                    }
                }
            }

            function startAutoRefresh() {
                if (autoRefreshInterval) clearInterval(autoRefreshInterval);
                autoRefreshInterval = setInterval(fetchLogs, 2000);
            }

            function stopAutoRefresh() {
                if (autoRefreshInterval) {
                    clearInterval(autoRefreshInterval);
                    autoRefreshInterval = null;
                }
            }

            // Event listeners
            document.getElementById('refreshBtn').onclick = fetchLogs;
            document.getElementById('clearBtn').onclick = clearLogs;
            document.getElementById('categoryFilter').onchange = renderLogs;
            document.getElementById('levelFilter').onchange = renderLogs;
            document.getElementById('jobFilter').oninput = renderLogs;
            
            document.getElementById('autoRefresh').onchange = function() {
                if (this.checked) {
                    startAutoRefresh();
                } else {
                    stopAutoRefresh();
                }
            };

            // Initial load
            fetchLogs();
            startAutoRefresh();
        </script>
    </body>
    </html>
    """
    
    return Response(content=html_content, media_type="text/html")


async def run_graph_async(job_id: str, request: ProductSearchRequest):
    """
    Run the graph asynchronously and update job status.
    """
    try:
        debug("API", f"Starting graph execution for job {job_id}", job_id)
        info("API", f"Query: {request.query}", job_id)
        
        # Check if job was cancelled before starting
        if running_jobs[job_id]["status"] == "cancelled":
            warn("API", f"Job {job_id} was cancelled before starting", job_id)
            return
            
        # Update status
        running_jobs[job_id]["status"] = "initializing"
        info("API", f"Job {job_id} status: initializing", job_id)
        
        # Prepare initial state with effort parameter - graph will configure limits internally
        initial_state = OverallState(
            user_query=request.query,
            effort=request.effort,
        )
        
        config = {"configurable": {"thread_id": job_id}}
        
        # Track progress through graph nodes
        node_updates = {
            "pars_query": "parsing_query",
            "enrich_query": "enriching_query",
            "find_criteria": "finding_criteria", 
            "query_generator": "generating_queries",
            "call_product_search_graph": "searching_products",
            "select_final_products": "selecting_products",
            "complete_product_info": "completing_product_info",
            "save_results_to_disk": "saving_results",
            "generate_html_results": "generating_html"
        }
        
        # Check for cancellation before executing graph
        if running_jobs[job_id]["status"] == "cancelled":
            warn("API", f"Job {job_id} was cancelled before graph execution", job_id)
            return
            
        info("API", f"Starting tracked graph execution for job {job_id}", job_id)
        # Execute graph with progress tracking
        result_state = tracked_graph.invoke(initial_state, config, job_id)
        info("API", f"Graph execution completed for job {job_id}", job_id)
        debug("API", f"Result state keys: {list(result_state.keys()) if result_state else 'None'}", job_id)
        
        # Check if human input is needed
        if result_state.get("awaiting_human") and result_state.get("human_question"):
            running_jobs[job_id]["status"] = "awaiting_human_input"
            running_jobs[job_id]["awaiting_human"] = True
            running_jobs[job_id]["human_question"] = result_state["human_question"]
            running_jobs[job_id]["current_state"] = result_state
            return  # Wait for human response
        
        # Check if HTML was generated
        html_file_path = result_state.get("html_file_path")
        if html_file_path:
            # Extract just the filename for the API
            filename = pathlib.Path(html_file_path).name
            running_jobs[job_id]["html_file_path"] = filename
        
        running_jobs[job_id]["status"] = "completed"
        running_jobs[job_id]["end_time"] = datetime.now().isoformat()
        
    except Exception as e:
        running_jobs[job_id]["status"] = "failed"
        running_jobs[job_id]["error"] = str(e)
        running_jobs[job_id]["end_time"] = datetime.now().isoformat()
        print(f"❌ Graph execution failed for job {job_id}: {e}")


async def resume_graph_with_human_input(job_id: str, human_answer: str):
    """
    Resume graph execution after receiving human input.
    """
    try:
        job_info = running_jobs[job_id]
        current_state = job_info.get("current_state")
        
        if not current_state:
            raise ValueError("No saved state found for resuming")
        
        # Update state with human answer
        current_state["human_answer"] = human_answer
        current_state["awaiting_human"] = False
        
        config = {"configurable": {"thread_id": job_id}}
        
        # Resume from human_ask_for_use_case node
        job_info["status"] = "resuming_after_human_input"
        
        # Continue graph execution with progress tracking
        result_state = tracked_graph.invoke(current_state, config, job_id)
        
        # Check if HTML was generated
        html_file_path = result_state.get("html_file_path")
        if html_file_path:
            # Extract just the filename for the API
            filename = pathlib.Path(html_file_path).name
            job_info["html_file_path"] = filename
        
        job_info["status"] = "completed"
        job_info["end_time"] = datetime.now().isoformat()
        
    except Exception as e:
        running_jobs[job_id]["status"] = "failed"
        running_jobs[job_id]["error"] = str(e)
        running_jobs[job_id]["end_time"] = datetime.now().isoformat()
        print(f"❌ Graph resume failed for job {job_id}: {e}")


async def cleanup_progress_after_delay(job_id: str):
    """Clean up progress tracking data after a delay to allow frontend to fetch final events"""
    await asyncio.sleep(30)  # Wait 30 seconds before cleanup
    cleanup_job_tracking(job_id)


# Mount the frontend under /app to not conflict with the LangGraph API routes
app.mount(
    "/app",
    create_frontend_router(),
    name="frontend",
)
