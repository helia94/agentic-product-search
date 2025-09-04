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
from agent.graph.graph_v2 import (
    graph
)
from agent.graph.state_V2 import OverallState
from agent.tracing.graph_wrapper import create_tracked_executor
from agent.tracing.node_progress import cleanup_progress
from agent.api.streaming_api import JobProgressStreamer
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

# Global state to track active job cancellation events
active_job_events: Dict[str, asyncio.Event] = {}

# Create tracked executor for progress monitoring  
tracked_graph = create_tracked_executor(graph, "product-search-main")

# Initialize progress streamer
progress_streamer = JobProgressStreamer(running_jobs)

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
    """Stream progress updates for a running search job. Clean business logic only."""
    if job_id not in running_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return StreamingResponse(
        progress_streamer.stream_job_progress(job_id),
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
    
    # Trigger cancellation event if graph is actively running
    if job_id in active_job_events:
        print(f"[CANCELLATION] Triggering stop event for job {job_id}")
        active_job_events[job_id].set()  # This will stop the graph execution
        
        # The graph will update the status to cancelled when it detects the event
        # But we also update it here for immediate feedback
        job_info["status"] = "cancelled"
        job_info["end_time"] = datetime.now().isoformat()
        job_info["cancelled_by_user"] = True
        
        return {"status": "cancelling", "job_id": job_id, "message": "Cancellation signal sent"}
    else:
        # Job is not actively running, just mark as cancelled
        job_info["status"] = "cancelled"
        job_info["end_time"] = datetime.now().isoformat()
        job_info["cancelled_by_user"] = True
        
        return {"status": "cancelled", "job_id": job_id, "message": "Job marked as cancelled"}


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
    cleanup_progress(job_id)



async def run_graph_async(job_id: str, request: ProductSearchRequest):
    """
    Run the graph asynchronously and update job status.
    """
    try:
        print("API", f"Starting graph execution for job {job_id}", job_id)
        print("API", f"Query: {request.query}", job_id)
        
        # Check if job was cancelled before starting
        if running_jobs[job_id]["status"] == "cancelled":
            print("API", f"Job {job_id} was cancelled before starting", job_id)
            return
            
        # Update status
        running_jobs[job_id]["status"] = "initializing"
        
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
            print("API", f"Job {job_id} was cancelled before graph execution", job_id)
            return
            
        # Create cancellation event for this job
        stop_event = asyncio.Event()
        active_job_events[job_id] = stop_event
        
        print("API", f"Starting tracked graph execution for job {job_id}", job_id)
        
        # Execute graph with cancellation support
        result_state = None
        try:
            # Use astream to get chunks and check for cancellation
            last_chunk = None
            async for chunk in tracked_graph.astream(initial_state, config, job_id):
                # Check if cancellation was requested
                if stop_event.is_set():
                    print("API", f"Graph execution cancelled for job {job_id}", job_id)
                    running_jobs[job_id]["status"] = "cancelled"
                    running_jobs[job_id]["end_time"] = datetime.now().isoformat()
                    return
                
                last_chunk = chunk
            
            result_state = last_chunk
        finally:
            # Clean up the stop event
            if job_id in active_job_events:
                del active_job_events[job_id]
        
        print("API", f"Graph execution completed for job {job_id}", job_id)
        print("API", f"Result state keys: {list(result_state.keys()) if result_state else 'None'}", job_id)
        
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
