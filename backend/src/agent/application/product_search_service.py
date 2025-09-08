"""
Product Search Service

Handles the core business logic of executing product searches using the LangGraph.
Extracted from app.py for clean separation of concerns.
"""

import asyncio
from typing import Dict, Any

from agent.domain.repositories.job_repository import JobRepository
from agent.graph.graph_v2 import graph
from agent.graph.state_V2 import OverallState
from agent.tracing.graph_wrapper import create_tracked_executor


class ProductSearchService:
    """Service responsible for executing product search operations"""
    
    def __init__(self, job_repository: JobRepository):
        self.job_repository = job_repository
        self.tracked_graph = create_tracked_executor(graph, "product-search-main")
    
    async def execute_search(self, job_id: str, query: str, effort: str) -> None:
        """
        Execute the product search for a job
        
        Args:
            job_id: Unique job identifier
            query: Search query from user
            effort: Search effort level (low, medium, high)
        """
        try:
            print(f"[SEARCH] Starting graph execution for job {job_id}")
            print(f"[SEARCH] Query: {query}")
            
            # Check if job was cancelled before starting
            job_data = await self.job_repository.get_job(job_id)
            if job_data and job_data["status"] == "cancelled":
                print(f"[SEARCH] Job {job_id} was cancelled before starting")
                return
                
            # Update status to initializing
            await self.job_repository.update_job_status(job_id, "initializing")
            
            # Prepare initial state
            initial_state = OverallState(
                user_query=query,
                effort=effort,
            )
            
            config = {"configurable": {"thread_id": job_id}}
            
            # Check for cancellation before executing graph
            job_data = await self.job_repository.get_job(job_id)
            if job_data and job_data["status"] == "cancelled":
                print(f"[SEARCH] Job {job_id} was cancelled before graph execution")
                return
            
            # Get cancellation event for this job (set by SearchJobService)
            stop_event = await self.job_repository.get_job_event(job_id)
            if not stop_event:
                print(f"[SEARCH] No cancellation event found for job {job_id}")
                return
            
            print(f"[SEARCH] Starting tracked graph execution for job {job_id}")
                        
            result_state = {}
            try:
                async for chunk in self.tracked_graph.astream(
                    initial_state,
                    config=config,
                    job_id=job_id,
                    stream_mode="values",   # <-- full state after each step
                ):
                    if stop_event.is_set():
                        print(f"[SEARCH] Graph execution cancelled for job {job_id}")
                        await self.job_repository.update_job_status(job_id, "cancelled")
                        return
                    if chunk:                      # chunk is the FULL state dict
                        result_state = chunk       # last chunk == final state
                        
                        # Check if human input is needed and interrupt execution
                        if result_state.get("awaiting_human") and result_state.get("human_question"):
                            print(f"[SEARCH] Human input needed for job {job_id}, interrupting execution")
                            await self.job_repository.update_job_status(
                                job_id,
                                "awaiting_human_input",
                                awaiting_human=True,
                                human_question=result_state["human_question"],
                                current_state=result_state
                            )
                            return  # Exit early, wait for human response
            finally:
                await self.job_repository.remove_job_event(job_id)

            print(f"[SEARCH] Graph execution completed for job {job_id}")
            print(f"[SEARCH] Result state keys: {list(result_state.keys()) if result_state else 'None'}")
            
            # Process successful completion
            if result_state:
                # Check if HTML was generated
                html_file_path = result_state.get("html_file_path")
                if html_file_path:
                    import pathlib
                    filename = pathlib.Path(html_file_path).name
                    await self.job_repository.update_job_status(
                        job_id,
                        f"completed",
                        html_file_path=filename
                    )
                else:
                    await self.job_repository.update_job_status(job_id, f"completed")
            else:
                await self.job_repository.update_job_status(
                    job_id, 
                    "failed", 
                    error="No result state returned from graph"
                )
                
        except Exception as e:
            print(f"[SEARCH] Graph execution failed for job {job_id}: {e}")
            await self.job_repository.update_job_status(
                job_id, 
                "failed", 
                error=str(e)
            )
    
    async def resume_search_with_human_input(self, job_id: str, human_answer: str) -> None:
        """
        Resume search execution after receiving human input
        
        Args:
            job_id: Job to resume
            human_answer: User's answer to the human question
        """
        try:
            job_data = await self.job_repository.get_job(job_id)
            if not job_data:
                raise ValueError("Job not found")
            
            current_state = job_data.get("current_state")
            if not current_state:
                raise ValueError("No saved state found for resuming")
            
            # Update state with human answer
            current_state["human_answer"] = human_answer
            current_state["awaiting_human"] = False
            
            config = {"configurable": {"thread_id": job_id}}
            
            # Resume from human_ask_for_use_case node
            await self.job_repository.update_job_status(job_id, "resuming_after_human_input")
            
            # Continue graph execution with progress tracking using astream
            result_state = {}
            async for chunk in self.tracked_graph.astream(
                current_state,
                config=config,
                job_id=job_id,
                stream_mode="values"
            ):
                if chunk:
                    result_state = chunk
            
            # Check if HTML was generated
            html_file_path = result_state.get("html_file_path")
            if html_file_path:
                import pathlib
                filename = pathlib.Path(html_file_path).name
                await self.job_repository.update_job_status(
                    job_id,
                    "completed", 
                    html_file_path=filename
                )
            else:
                await self.job_repository.update_job_status(job_id, "completed")
                
        except Exception as e:
            print(f"[SEARCH] Graph resume failed for job {job_id}: {e}")
            await self.job_repository.update_job_status(
                job_id,
                "failed",
                error=str(e)
            )