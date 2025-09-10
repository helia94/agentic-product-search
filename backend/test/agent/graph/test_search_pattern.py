"""
Test suite for execute_search_pattern_flexible function.

This test suite is designed to be agnostic to internal class structure,
focusing on testing the outer function behavior with comprehensive scenarios.
"""

import json
import pytest
from unittest.mock import Mock, patch
from typing import List, Dict, Any

from agent.graph.search_pattern import execute_search_pattern_flexible, SearchConfig, StateKeys
from langchain_core.messages import AIMessage
from langchain_core.messages.tool import ToolCall


# =========================
#       TEST CASES
# =========================

def test_no_previous_tool_call_requests_one_search(search_config, search_limits, mock_llms):
    """No tool history -> analyze is skipped; search LLM is asked; returns 1 tool call."""
    structured_llm, tools_llm = mock_llms
    
    # Setup: LLM will return one search query
    tools_llm.setup_responses([
        TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "alpha"})])
    ])
    
    state = TestHelpers.create_state(search_limits=search_limits)
    
    result = execute_search_pattern_flexible(state, structured_llm, tools_llm, search_config)
    
    # Verify return structure
    assert set(result.keys()) == {StateKeys.AI_QUERIES, StateKeys.TOOL_SAVED_INFO, StateKeys.LAST_TOOL_CALL_COUNT}
    assert result[StateKeys.LAST_TOOL_CALL_COUNT] == 1
    assert TestHelpers.is_document_store(result[StateKeys.TOOL_SAVED_INFO])
    
    # Verify analyze step was skipped (no previous outputs)
    assert not structured_llm.was_called()
    
    # Verify search prompt contains expected elements
    search_prompt = tools_llm.get_last_prompt()
    assert "Use a MAX of 3 searches" in search_prompt
    assert "Prior:[]" in search_prompt
    assert "Used:0" in search_prompt
    assert "CC:2" in search_prompt


def test_prev_tool_call_len_one_requests_one_more(search_config, search_limits, mock_llms):
    """Tool history len=1 -> analyze runs; search LLM requested; returns 1 tool call."""
    structured_llm, tools_llm = mock_llms
    
    # Setup: Previous search and new search response
    tools_llm.setup_responses([
        TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "beta-2"})])
    ])
    
    state = TestHelpers.create_state(
        search_limits=search_limits,
        tool_last_output=[TestHelpers.create_tool_output_message("alpha-1")],
        last_tool_call_count=1,
        ai_queries=[TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "alpha-1"})])]
    )
    
    result = execute_search_pattern_flexible(state, structured_llm, tools_llm, search_config)
    
    # Verify return structure
    assert set(result.keys()) == {StateKeys.AI_QUERIES, StateKeys.TOOL_SAVED_INFO, StateKeys.LAST_TOOL_CALL_COUNT}
    assert result[StateKeys.LAST_TOOL_CALL_COUNT] == 1
    
    # Verify analyze step was called
    assert structured_llm.was_called()
    analyze_prompt = structured_llm.get_last_prompt()
    assert '"Search 1: alpha-1"' in analyze_prompt
    assert "Content about alpha-1" in analyze_prompt
    
    # Verify search prompt includes context
    search_prompt = tools_llm.get_last_prompt()
    assert "Saved:" in search_prompt
    assert '"alpha-1"' in search_prompt
    assert "You already used 1 searches." in search_prompt


def test_prev_tool_call_len_three_requests_multiple(search_config, search_limits, mock_llms):
    """Tool history len=3 -> analyze runs; LLM proposes 2 parallel queries -> count is 2."""
    structured_llm, tools_llm = mock_llms
    
    # Setup: LLM will return two parallel searches
    tools_llm.setup_responses([
        TestHelpers.create_ai_message_with_tool_calls([
            ("tavily_search_results_json", {"query": "beta-1"}),
            ("tavily_search_results_json", {"query": "beta-2"})
        ])
    ])
    
    state = TestHelpers.create_state(
        search_limits=search_limits,
        tool_last_output=[
            TestHelpers.create_tool_output_message("alpha-1"),
            TestHelpers.create_tool_output_message("alpha-2"),
            TestHelpers.create_tool_output_message("alpha-3")
        ],
        last_tool_call_count=3,
        ai_queries=[TestHelpers.create_ai_message_with_tool_calls([
            ("tavily_search_results_json", {"query": "alpha-1"}),
            ("tavily_search_results_json", {"query": "alpha-2"}),
            ("tavily_search_results_json", {"query": "alpha-3"})
        ])]
    )
    
    result = execute_search_pattern_flexible(state, structured_llm, tools_llm, search_config)
    
    # Verify return structure
    assert set(result.keys()) == {StateKeys.AI_QUERIES, StateKeys.TOOL_SAVED_INFO, StateKeys.LAST_TOOL_CALL_COUNT}
    assert result[StateKeys.LAST_TOOL_CALL_COUNT] == 2
    
    # Verify analyze prompt includes all queries
    analyze_prompt = structured_llm.get_last_prompt()
    assert '"Search 1: alpha-1"' in analyze_prompt
    assert '"Search 2: alpha-2"' in analyze_prompt
    assert '"Search 3: alpha-3"' in analyze_prompt


def test_hard_limit_reached_skips_search_and_formats(search_config, search_limits, mock_llms):
    """If used == max_searches, we do NOT call tool LLM; we immediately format and finish."""
    structured_llm, tools_llm = mock_llms
    
    # Setup: Already used 3 searches (equals max)
    state = TestHelpers.create_state(
        search_limits=search_limits,
        ai_queries=[
            TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "q-1"})]),
            TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "q-2"})]),
            TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "q-3"})])
        ],
        tool_last_output=[TestHelpers.create_tool_output_message("q-3")],
        last_tool_call_count=1
    )
    
    result = execute_search_pattern_flexible(state, structured_llm, tools_llm, search_config)
    
    # Verify finalization
    assert set(result.keys()) == {StateKeys.FINAL_OUTPUT, StateKeys.AI_QUERIES}
    assert TestHelpers.is_document_store(result[StateKeys.FINAL_OUTPUT])
    assert result[StateKeys.AI_QUERIES][0].content == "no more searches"
    
    # Verify search LLM was NOT called
    assert not tools_llm.was_called()
    
    # Verify both analyze and format were called
    assert structured_llm.call_count() == 2  # analyze + format


def test_llm_decides_no_more_searches_returns_final(search_config, search_limits, mock_llms):
    """LLM responds without tool_calls -> we format and finish."""
    structured_llm, tools_llm = mock_llms
    
    # Setup: LLM returns no tool calls (decides it's enough)
    tools_llm.setup_responses([
        AIMessage(content="I have enough information", tool_calls=[])
    ])
    
    state = TestHelpers.create_state(
        search_limits=search_limits,
        ai_queries=[TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "alpha-1"})])],
        tool_last_output=[TestHelpers.create_tool_output_message("alpha-1")],
        last_tool_call_count=1
    )
    
    result = execute_search_pattern_flexible(state, structured_llm, tools_llm, search_config)
    
    # Verify finalization
    assert set(result.keys()) == {StateKeys.FINAL_OUTPUT, StateKeys.AI_QUERIES}
    assert TestHelpers.is_document_store(result[StateKeys.FINAL_OUTPUT])
    assert result[StateKeys.AI_QUERIES][0].content == "no more searches"
    
    # Verify prompts include prior context
    search_prompt = tools_llm.get_last_prompt()
    assert '"alpha-1"' in search_prompt
    
    # Verify analyze was called (should be first call to structured LLM)
    assert structured_llm.call_count() == 2  # analyze + format


def test_llm_generates_three_parallel_queries_when_allowed(search_config, search_limits, mock_llms):
    """Not at limit; LLM proposes 3 parallel searches -> last_tool_call_count=3."""
    structured_llm, tools_llm = mock_llms
    
    # Setup: LLM will return three parallel searches
    tools_llm.setup_responses([
        TestHelpers.create_ai_message_with_tool_calls([
            ("tavily_search_results_json", {"query": "p-1"}),
            ("tavily_search_results_json", {"query": "p-2"}),
            ("tavily_search_results_json", {"query": "p-3"})
        ])
    ])
    
    state = TestHelpers.create_state(
        search_limits=search_limits,
        ai_queries=[TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "seed"})])],
        tool_last_output=[TestHelpers.create_tool_output_message("seed")]
    )
    
    result = execute_search_pattern_flexible(state, structured_llm, tools_llm, search_config)
    
    # Verify return structure
    assert set(result.keys()) == {StateKeys.AI_QUERIES, StateKeys.TOOL_SAVED_INFO, StateKeys.LAST_TOOL_CALL_COUNT}
    assert result[StateKeys.LAST_TOOL_CALL_COUNT] == 3
    
    # Verify search prompt includes usage info
    search_prompt = tools_llm.get_last_prompt()
    assert "You already used 1 searches." in search_prompt
    assert '"seed"' in search_prompt


# =========================
#   FIXTURES & HELPERS
# =========================

@pytest.fixture
def search_limits():
    """Create search limits configuration."""
    return TestHelpers.create_search_limits()


@pytest.fixture
def search_config():
    """Create search configuration with test-friendly prompts."""
    return TestHelpers.create_search_config()


@pytest.fixture
def mock_llms():
    """Create mock LLM pair for testing."""
    return TestHelpers.create_mock_llm_pair()


class TestHelpers:
    """Helper class containing all test utilities."""
    
    @staticmethod
    def create_search_limits():
        """Create a mock search limits object."""
        class SearchLimits:
            def __init__(self):
                self.product_exploration_max_searches = 3
                self.product_exploration_concurrent_searches = 2
                self.product_research_max_searches = 3
                self.product_research_concurrent_searches = 2
                self.final_product_info_max_searches = 3
                self.final_product_info_concurrent_searches = 2
        
        return SearchLimits()
    
    @staticmethod
    def create_search_config():
        """Create search configuration with test-friendly prompts."""
        return SearchConfig(
            analyze_prompt=(
                "ANALYZE:\n"
                "Args:{last_tool_call_arguments}\n"
                "Output:{last_tool_call_output}\n"
            ),
            search_prompt=(
                "SEARCH:\n"
                "Saved:{tool_saved_info}\n"
                "Prior:{ai_queries}\n"
                "Used:{len_ai_queries}\n"
                "{search_limit_text}\n"
                "CC:{concurrent_searches}\n"
            ),
            format_prompt=(
                "FORMAT:\n"
                "Saved:{tool_saved_info}\n"
            ),
            state_field_mapping={},
            component_name="product_exploration"
        )
    
    @staticmethod
    def create_mock_llm_pair():
        """Create a pair of mock LLMs for testing."""
        return MockStructuredLLM(), MockToolsLLM()
    
    @staticmethod
    def create_state(search_limits, ai_queries=None, tool_last_output=None, 
                    last_tool_call_count=None, tool_saved_info=None):
        """Create a test state dictionary."""
        from agent.citation.document import DocumentStore
        
        state = {
            StateKeys.SEARCH_LIMITS: search_limits,
            StateKeys.AI_QUERIES: ai_queries or [],
            StateKeys.TOOL_LAST_OUTPUT: tool_last_output or []
        }
        
        if tool_saved_info is not None:
            state[StateKeys.TOOL_SAVED_INFO] = tool_saved_info
        else:
            state[StateKeys.TOOL_SAVED_INFO] = DocumentStore()
            
        if last_tool_call_count is not None:
            state[StateKeys.LAST_TOOL_CALL_COUNT] = last_tool_call_count
            
        return state
    
    @staticmethod
    def create_ai_message_with_tool_calls(tool_calls_data):
        """Create an AIMessage with properly formatted tool calls."""
        tool_calls = []
        for i, (name, args) in enumerate(tool_calls_data):
            tool_calls.append(ToolCall(
                name=name,
                args=args,
                id=f"call_{i+1}",
                type="tool_call"
            ))
        
        return AIMessage(content="", tool_calls=tool_calls)
    
    @staticmethod
    def create_tool_output_message(query):
        """Create a tool output message with mock Tavily response."""
        payload = {
            "query": query,
            "follow_up_questions": None,
            "answer": f"Answer for {query}",
            "images": [],
            "results": [
                {
                    "title": f"Result for {query}",
                    "url": f"https://example.com/{query.replace(' ', '-')}",
                    "content": f"Content about {query} with detailed information.",
                    "score": 0.9,
                    "published_date": "2024-01-15"
                }
            ]
        }
        return AIMessage(content=json.dumps(payload))
    
    @staticmethod
    def is_document_store(obj):
        """Check if object is a DocumentStore instance."""
        from agent.citation.document import DocumentStore
        return isinstance(obj, DocumentStore)


class MockStructuredLLM:
    """Mock for the structured LLM used for analyze and format steps."""
    
    def __init__(self):
        self._prompts = []
        self._call_count = 0
    
    def with_structured_output(self, schema):
        """Return a mock invoker that records prompts and returns empty facts."""
        return MockStructuredInvoker(self)
    
    def record_call(self, prompt):
        """Record a call to the LLM."""
        self._prompts.append(prompt)
        self._call_count += 1
    
    def was_called(self):
        """Check if the LLM was called."""
        return self._call_count > 0
    
    def call_count(self):
        """Get the number of times the LLM was called."""
        return self._call_count
    
    def get_last_prompt(self):
        """Get the last prompt sent to the LLM."""
        return self._prompts[-1] if self._prompts else ""


class MockStructuredInvoker:
    """Mock invoker for structured LLM calls."""
    
    def __init__(self, parent_llm):
        self.parent_llm = parent_llm
    
    def invoke(self, prompt):
        """Record the prompt and return empty facts list."""
        self.parent_llm.record_call(prompt)
        return {"facts": []}  # Return empty facts list


class MockToolsLLM:
    """Mock for the tools LLM used for search generation."""
    
    def __init__(self):
        self._responses = []
        self._prompts = []
        self._response_index = 0
    
    def setup_responses(self, responses):
        """Setup predefined responses for the LLM."""
        self._responses = responses
        self._response_index = 0
    
    def invoke(self, prompt):
        """Record prompt and return next predefined response."""
        self._prompts.append(prompt)
        
        if self._response_index < len(self._responses):
            response = self._responses[self._response_index]
            self._response_index += 1
            return response
        
        # Default response if no more predefined responses
        return AIMessage(content="", tool_calls=[])
    
    def was_called(self):
        """Check if the LLM was called."""
        return len(self._prompts) > 0
    
    def get_last_prompt(self):
        """Get the last prompt sent to the LLM."""
        return self._prompts[-1] if self._prompts else ""



def test_empty_tool_output_handles_gracefully(search_config, search_limits, mock_llms):
    """Test that empty or malformed tool outputs are handled gracefully."""
    structured_llm, tools_llm = mock_llms
    
    tools_llm.setup_responses([
        TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "recovery"})])
    ])
    
    # Create state with empty/malformed tool output
    state = TestHelpers.create_state(
        search_limits=search_limits,
        tool_last_output=[AIMessage(content="")],  # Empty content
        last_tool_call_count=1,
        ai_queries=[TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "test"})])]
    )
    
    result = execute_search_pattern_flexible(state, structured_llm, tools_llm, search_config)
    
    # Should still work and return valid structure
    assert set(result.keys()) == {StateKeys.AI_QUERIES, StateKeys.TOOL_SAVED_INFO, StateKeys.LAST_TOOL_CALL_COUNT}
    assert result[StateKeys.LAST_TOOL_CALL_COUNT] == 1


def test_concurrent_search_limit_respected(search_config, search_limits, mock_llms):
    """Test that concurrent search limits are properly communicated to LLM."""
    structured_llm, tools_llm = mock_llms
    
    # Setup LLM to return exactly the concurrent limit (2)
    tools_llm.setup_responses([
        TestHelpers.create_ai_message_with_tool_calls([
            ("tavily_search_results_json", {"query": "concurrent-1"}),
            ("tavily_search_results_json", {"query": "concurrent-2"})
        ])
    ])
    
    state = TestHelpers.create_state(search_limits=search_limits)
    
    result = execute_search_pattern_flexible(state, structured_llm, tools_llm, search_config)
    
    # Verify concurrent limit is communicated
    search_prompt = tools_llm.get_last_prompt()
    assert "CC:2" in search_prompt
    
    # Verify result respects the concurrent count
    assert result[StateKeys.LAST_TOOL_CALL_COUNT] == 2


def test_search_limit_boundary_conditions(search_config, search_limits, mock_llms):
    """Test behavior at search limit boundaries (2 used, 1 remaining)."""
    structured_llm, tools_llm = mock_llms
    
    tools_llm.setup_responses([
        TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "final"})])
    ])
    
    # Setup state with 2 searches used (1 remaining before limit)
    state = TestHelpers.create_state(
        search_limits=search_limits,
        ai_queries=[
            TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "first"})]),
            TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "second"})])
        ],
        tool_last_output=[TestHelpers.create_tool_output_message("second")],
        last_tool_call_count=1
    )
    
    result = execute_search_pattern_flexible(state, structured_llm, tools_llm, search_config)
    
    # Should still allow one more search
    assert set(result.keys()) == {StateKeys.AI_QUERIES, StateKeys.TOOL_SAVED_INFO, StateKeys.LAST_TOOL_CALL_COUNT}
    
    # Verify limit communication
    search_prompt = tools_llm.get_last_prompt()
    assert "You already used 2 searches." in search_prompt


def test_tool_call_with_missing_query_parameter(search_config, search_limits, mock_llms):
    """Test handling of tool calls with missing or malformed query parameters."""
    structured_llm, tools_llm = mock_llms
    
    tools_llm.setup_responses([
        TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "recovery"})])
    ])
    
    # Create AI message with malformed tool call (missing query)
    malformed_tool_call = TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {})])
    
    state = TestHelpers.create_state(
        search_limits=search_limits,
        ai_queries=[malformed_tool_call],
        tool_last_output=[TestHelpers.create_tool_output_message("test")],
        last_tool_call_count=1
    )
    
    result = execute_search_pattern_flexible(state, structured_llm, tools_llm, search_config)
    
    # Should handle gracefully and continue
    assert set(result.keys()) == {StateKeys.AI_QUERIES, StateKeys.TOOL_SAVED_INFO, StateKeys.LAST_TOOL_CALL_COUNT}


def test_multiple_ai_queries_with_different_tool_call_counts(search_config, search_limits, mock_llms):
    """Test handling of multiple AI queries with varying tool call counts."""
    structured_llm, tools_llm = mock_llms
    
    tools_llm.setup_responses([
        AIMessage(content="Enough information gathered", tool_calls=[])
    ])
    
    # Setup state with mixed tool call counts
    state = TestHelpers.create_state(
        search_limits=search_limits,
        ai_queries=[
            TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "single"})]),
            TestHelpers.create_ai_message_with_tool_calls([
                ("tavily_search_results_json", {"query": "multi-1"}),
                ("tavily_search_results_json", {"query": "multi-2"})
            ])
        ],
        tool_last_output=[
            TestHelpers.create_tool_output_message("multi-1"),
            TestHelpers.create_tool_output_message("multi-2")
        ],
        last_tool_call_count=2
    )
    
    result = execute_search_pattern_flexible(state, structured_llm, tools_llm, search_config)
    
    # Should finalize since LLM decided no more searches
    assert set(result.keys()) == {StateKeys.FINAL_OUTPUT, StateKeys.AI_QUERIES}
    assert result[StateKeys.AI_QUERIES][0].content == "no more searches"
