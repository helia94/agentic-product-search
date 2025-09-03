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
    graph, 
    configure_search_limits_for_product_search,
    configure_aggressive_search_limits,
    configure_thorough_search_limits
)
from agent.state_V2 import OverallState

# Request/Response models
class ProductSearchRequest(BaseModel):
    query: str
    effort: str = "medium"  # "low", "medium", "high"

class StreamEvent(BaseModel):
    event: str
    data: Dict[str, Any]
    timestamp: str

# Global state to track running jobs
running_jobs: Dict[str, Dict[str, Any]] = {}

# Define the FastAPI app with lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Product Search API starting up...")
    yield
    # Shutdown
    print("🛑 Product Search API shutting down...")

app = FastAPI(lifespan=lifespan)

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
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


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
    job_id = str(uuid.uuid4())
    
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
    
    return {"job_id": job_id, "status": "started"}


@app.get("/api/search/{job_id}/stream")
async def stream_search_progress(job_id: str):
    """
    Stream progress updates for a running search job.
    """
    if job_id not in running_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    async def event_generator():
        last_event_time = datetime.now()
        
        while True:
            job_info = running_jobs.get(job_id)
            if not job_info:
                break
            
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
            if job_info["status"] in ["completed", "failed"]:
                final_event = StreamEvent(
                    event="job_complete",
                    data={
                        "status": job_info["status"],
                        "html_file_path": job_info.get("html_file_path"),
                        "error": job_info.get("error")
                    },
                    timestamp=datetime.now().isoformat()
                )
                yield f"data: {final_event.model_dump_json()}\n\n"
                break
            
            await asyncio.sleep(2)  # Update every 2 seconds
    
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


async def run_graph_async(job_id: str, request: ProductSearchRequest):
    """
    Run the graph asynchronously and update job status.
    """
    try:
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
        
        # Execute graph synchronously 
        result_state = graph.invoke(initial_state, config=config)
        
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


# Mount the frontend under /app to not conflict with the LangGraph API routes
app.mount(
    "/app",
    create_frontend_router(),
    name="frontend",
)
