"""
FastAPI Application - Thin Controllers Only

Clean separation of concerns following Domain Driven Design.
Controllers handle only HTTP concerns, business logic delegated to services.
"""

import pathlib
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import fastapi.exceptions

# Infrastructure - DI Container
from agent.infrastructure.service_container import ServiceContainer
from agent.tracing import configure_tracing, get_tracer, add_span_attribute, add_span_event


# Request/Response DTOs
class ProductSearchRequest(BaseModel):
    query: str
    effort: str = "medium"  # "low", "medium", "high"


class HumanResponse(BaseModel):
    job_id: str
    answer: str


# Initialize dependency injection container
container = ServiceContainer()


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


# REST Endpoints - Thin Controllers Only
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    with tracer.start_as_current_span("health_check"):
        add_span_attribute("endpoint", "/api/health")
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/api/search")
async def start_product_search(request: ProductSearchRequest):
    """Start a product search and return a job ID for streaming updates."""
    with tracer.start_as_current_span("start_product_search"):
        add_span_attribute("query", request.query)
        add_span_attribute("effort", request.effort)
        
        try:
            # Delegate to service layer
            job_id = await container.search_job_service.start_search_job(
                request.query, 
                request.effort
            )
            
            # Start async search execution  
            asyncio.create_task(
                _execute_search_background(job_id, request.query, request.effort)
            )
            
            add_span_event("job_started", {"job_id": job_id})
            return {"job_id": job_id, "status": "started"}
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to start search: {str(e)}")


@app.get("/api/search/{job_id}/stream")
async def stream_search_progress(job_id: str):
    """Stream progress updates for a running search job."""
    try:
        # Check if job exists
        job_data = await container.search_job_service.get_job_status(job_id)
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Delegate streaming to service layer
        return StreamingResponse(
            container.progress_streaming_service.stream_job_progress(job_id),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Streaming failed: {str(e)}")


@app.get("/api/search/{job_id}/status")
async def get_search_status(job_id: str):
    """Get the current status of a search job."""
    try:
        job_status = await container.search_job_service.get_job_status(job_id)
        if not job_status:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return job_status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@app.post("/api/search/{job_id}/stop") 
async def stop_search_job(job_id: str):
    """Stop a running search job."""
    try:
        # Delegate to service layer
        result = await container.search_job_service.cancel_job(job_id)
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop job: {str(e)}")


@app.post("/api/human-response")
async def submit_human_response(response: HumanResponse):
    """Submit a human response to continue graph execution."""
    try:
        # Delegate to service layer
        result = await container.search_job_service.submit_human_response(
            response.job_id, 
            response.answer
        )
        
        # Start background task to resume search
        asyncio.create_task(
            container.product_search_service.resume_search_with_human_input(
                response.job_id, 
                response.answer
            )
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit response: {str(e)}")


@app.get("/api/results/{filename}")
async def serve_html_result(filename: str):
    """Serve the generated HTML results file."""
    file_path = pathlib.Path("results") / filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Result file not found")
    
    return FileResponse(
        file_path,
        media_type="text/html",
        filename=filename
    )


# Background task helpers
async def _execute_search_background(job_id: str, query: str, effort: str):
    """Execute search in background with proper error handling"""
    try:
        # Set job as active with cancellation support
        await container.search_job_service.set_job_active(job_id)
        
        # Delegate to service layer
        await container.product_search_service.execute_search(job_id, query, effort)
        
    except Exception as e:
        print(f"[API] Background search failed for job {job_id}: {e}")
        await container.search_job_service.mark_job_failed(job_id, str(e))
    finally:
        # Cleanup
        await container.search_job_service.set_job_inactive(job_id)


# Frontend serving logic (unchanged)
def create_frontend_router(build_dir="../frontend/dist"):
    """Creates a router to serve the React frontend."""
    build_path = pathlib.Path(__file__).parent.parent.parent / build_dir
    static_files_path = build_path / "assets"

    if not build_path.is_dir() or not (build_path / "index.html").is_file():
        print(f"WARN: Frontend build directory not found at {build_path}")
        from starlette.routing import Route
        
        async def dummy_frontend(request):
            return Response(
                "Frontend not built. Run 'npm run build' in the frontend directory.",
                media_type="text/plain",
                status_code=503,
            )
        return Route("/{path:path}", endpoint=dummy_frontend)

    react = FastAPI(openapi_url="")
    react.mount("/assets", StaticFiles(directory=static_files_path), name="static_assets")

    @react.get("/{path:path}")
    async def handle_catch_all(request: Request, path: str):
        fp = build_path / path
        if not fp.exists() or not fp.is_file():
            fp = build_path / "index.html"
        return fastapi.responses.FileResponse(fp)

    return react


# Mount the frontend
app.mount("/app", create_frontend_router(), name="frontend")


# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)