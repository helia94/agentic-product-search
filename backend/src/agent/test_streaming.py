"""
Comprehensive tests for streaming API events.
Tests that events are really generated when API is called.
"""

import pytest
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import Mock, patch

from agent.node_progress import NodeEvent, track_node_progress, get_progress_events, cleanup_progress
from agent.streaming_api import JobProgressStreamer, StreamEvent


class TestNodeProgressTracking:
    """Test the clean node progress tracking system"""
    
    def setup_method(self):
        """Setup for each test"""
        self.job_id = "test-job-123"
        
    def teardown_method(self):
        """Cleanup after each test"""
        cleanup_progress(self.job_id)
    
    def test_decorator_tracks_node_execution(self):
        """Test that decorator properly tracks node start/end"""
        
        @track_node_progress("test_node")
        def test_function(state, config=None):
            return {"result": "success"}
        
        # Execute function
        config = {"configurable": {"thread_id": self.job_id}}
        result = test_function({"input": "test"}, config)
        
        # Verify result
        assert result == {"result": "success"}
        
        # Verify events were tracked
        events = get_progress_events(self.job_id)
        assert len(events) == 2
        
        start_event = events[0]
        assert start_event.job_id == self.job_id
        assert start_event.event_type == "node_start"
        assert start_event.node_name == "test_node"
        assert start_event.duration_ms is None
        
        end_event = events[1]
        assert end_event.job_id == self.job_id
        assert end_event.event_type == "node_end"
        assert end_event.node_name == "test_node"
        assert end_event.duration_ms is not None
        assert end_event.duration_ms >= 0  # Duration can be 0 for very fast functions
    
    def test_decorator_tracks_node_error(self):
        """Test that decorator tracks errors properly"""
        
        @track_node_progress("error_node")
        def error_function(state, config=None):
            raise ValueError("Test error")
        
        config = {"configurable": {"thread_id": self.job_id}}
        
        with pytest.raises(ValueError):
            error_function({"input": "test"}, config)
        
        # Verify events were tracked including error timing
        events = get_progress_events(self.job_id)
        assert len(events) == 2
        
        start_event = events[0]
        assert start_event.event_type == "node_start"
        
        end_event = events[1]
        assert end_event.event_type == "node_end"
        assert end_event.duration_ms is not None
        # Error case still tracks timing
    
    def test_multiple_nodes_different_jobs(self):
        """Test tracking multiple nodes across different jobs"""
        
        job1 = "job-1"
        job2 = "job-2"
        
        @track_node_progress("node_a")
        def node_a(state, config=None):
            return {"step": "a"}
        
        @track_node_progress("node_b")  
        def node_b(state, config=None):
            return {"step": "b"}
        
        # Execute on different jobs
        node_a({"input": "test"}, {"configurable": {"thread_id": job1}})
        node_b({"input": "test"}, {"configurable": {"thread_id": job2}})
        node_a({"input": "test"}, {"configurable": {"thread_id": job1}})
        
        # Verify separate tracking
        job1_events = get_progress_events(job1)
        job2_events = get_progress_events(job2)
        
        assert len(job1_events) == 4  # 2 executions of node_a
        assert len(job2_events) == 2  # 1 execution of node_b
        
        # Cleanup
        cleanup_progress(job1)
        cleanup_progress(job2)
    
    def test_filtered_events_by_timestamp(self):
        """Test filtering events by timestamp"""
        
        @track_node_progress("timed_node")
        def timed_function(state, config=None):
            return {"result": "timed"}
        
        config = {"configurable": {"thread_id": self.job_id}}
        
        # Execute first time
        timed_function({"input": "test1"}, config)
        first_events = get_progress_events(self.job_id)
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        # Execute second time
        timed_function({"input": "test2"}, config)
        
        # Get only new events after first execution
        all_events = get_progress_events(self.job_id)
        new_events = get_progress_events(self.job_id, first_events[-1].timestamp)
        
        assert len(all_events) == 4  # 2 executions = 4 events
        assert len(new_events) == 2  # Only second execution


class TestStreamingAPI:
    """Test the streaming API functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.job_id = "stream-test-job"
        self.running_jobs = {
            self.job_id: {
                "status": "running",
                "query": "test query",
                "html_file_path": None,
                "error": None
            }
        }
        self.streamer = JobProgressStreamer(self.running_jobs)
    
    def teardown_method(self):
        """Cleanup after each test"""
        cleanup_progress(self.job_id)
    
    @pytest.mark.asyncio
    async def test_stream_node_progress_events(self):
        """Test that node progress events are streamed correctly"""
        
        # Simulate node execution by adding events
        @track_node_progress("stream_test_node")
        def test_node(state, config=None):
            return {"streamed": True}
        
        config = {"configurable": {"thread_id": self.job_id}}
        
        # Execute function to generate events
        test_node({"input": "test"}, config)
        
        # Complete job
        self.running_jobs[self.job_id]["status"] = "completed"
        
        # Stream events
        events = []
        async for event_str in self.streamer.stream_job_progress(self.job_id):
            events.append(event_str)
            # Break after getting completion event
            if "job_complete" in event_str:
                break
        
        # Verify we got node progress events
        node_events = [e for e in events if "node_progress" in e]
        assert len(node_events) >= 2  # start and end events
        
        # Parse and verify event structure
        for event_str in node_events:
            event_data = event_str.strip().replace("data: ", "")
            parsed = json.loads(event_data)
            
            assert parsed["event"] == "node_progress"
            assert "event_type" in parsed["data"]
            assert "node_name" in parsed["data"]
            assert parsed["data"]["node_name"] == "stream_test_node"
    
    @pytest.mark.asyncio
    async def test_stream_status_updates(self):
        """Test that status updates are streamed"""
        
        # Complete job quickly
        self.running_jobs[self.job_id]["status"] = "completed"
        
        events = []
        async for event_str in self.streamer.stream_job_progress(self.job_id):
            events.append(event_str)
            if "job_complete" in event_str:
                break
        
        # Should have status update and completion
        status_events = [e for e in events if "status_update" in e]
        complete_events = [e for e in events if "job_complete" in e]
        
        assert len(status_events) >= 1
        assert len(complete_events) == 1
    
    @pytest.mark.asyncio
    async def test_human_input_streaming(self):
        """Test human input requirement streaming"""
        
        # Setup job awaiting human input
        self.running_jobs[self.job_id].update({
            "awaiting_human": True,
            "human_question": "What do you prefer?"
        })
        
        events = []
        # Create a task to simulate human response after delay
        async def simulate_human_response():
            await asyncio.sleep(0.1)  # Short delay
            self.running_jobs[self.job_id]["awaiting_human"] = False
            self.running_jobs[self.job_id]["status"] = "completed"
        
        # Start simulation task
        response_task = asyncio.create_task(simulate_human_response())
        
        # Stream events
        async for event_str in self.streamer.stream_job_progress(self.job_id):
            events.append(event_str)
            if "job_complete" in event_str:
                break
        
        await response_task
        
        # Verify human input event was streamed
        human_events = [e for e in events if "human_input_required" in e]
        assert len(human_events) >= 1
        
        # Parse human event
        human_event_data = human_events[0].strip().replace("data: ", "")
        parsed = json.loads(human_event_data)
        
        assert parsed["event"] == "human_input_required"
        assert parsed["data"]["question"] == "What do you prefer?"
        assert parsed["data"]["status"] == "awaiting_human_input"


class TestEndToEndIntegration:
    """End-to-end integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_workflow_streaming(self):
        """Test complete workflow with multiple nodes streaming"""
        
        job_id = "integration-test"
        
        # Define test workflow nodes
        @track_node_progress("step_1")
        def step_one(state, config=None):
            return {**state, "step_1_done": True}
        
        @track_node_progress("step_2") 
        def step_two(state, config=None):
            return {**state, "step_2_done": True}
        
        @track_node_progress("step_3")
        def step_three(state, config=None):
            return {**state, "step_3_done": True}
        
        # Setup job tracking
        running_jobs = {
            job_id: {
                "status": "running",
                "query": "integration test",
                "html_file_path": None,
                "error": None
            }
        }
        
        streamer = JobProgressStreamer(running_jobs)
        config = {"configurable": {"thread_id": job_id}}
        
        # Start streaming task
        streamed_events = []
        
        async def collect_events():
            async for event in streamer.stream_job_progress(job_id):
                streamed_events.append(event)
                if "job_complete" in event:
                    break
        
        # Start streaming
        stream_task = asyncio.create_task(collect_events())
        
        # Execute workflow steps with small delays
        await asyncio.sleep(0.05)
        step_one({"start": True}, config)
        
        await asyncio.sleep(0.05) 
        step_two({"start": True}, config)
        
        await asyncio.sleep(0.05)
        step_three({"start": True}, config)
        
        # Mark job complete
        running_jobs[job_id]["status"] = "completed"
        
        # Wait for streaming to complete
        await stream_task
        
        # Verify all node events were streamed
        node_events = [e for e in streamed_events if "node_progress" in e]
        
        # Should have start/end events for each of 3 steps = 6 events
        assert len(node_events) == 6
        
        # Verify proper sequence
        step_names = []
        for event_str in node_events:
            event_data = event_str.strip().replace("data: ", "")
            parsed = json.loads(event_data)
            step_names.append(f"{parsed['data']['node_name']}_{parsed['data']['event_type']}")
        
        expected_sequence = [
            "step_1_node_start", "step_1_node_end",
            "step_2_node_start", "step_2_node_end", 
            "step_3_node_start", "step_3_node_end"
        ]
        
        assert step_names == expected_sequence
        
        # Cleanup
        cleanup_progress(job_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])