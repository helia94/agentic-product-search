"""
Test suite for execute_search_pattern_flexible function.

This test suite is designed to be agnostic to internal class structure,
focusing on testing the outer function behavior with comprehensive scenarios.
"""

import json
import re
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
    
    # Verify document store is empty (no previous searches to analyze)
    TestHelpers.assert_document_store_length(result[StateKeys.TOOL_SAVED_INFO], 0, "No previous tool outputs should result in empty document store: ")
    
    # Verify analyze step was skipped (no previous outputs)
    assert not structured_llm.was_called()
    
    # Verify search prompt contains expected elements
    search_prompt = tools_llm.get_last_prompt()
    assert "Use a MAX of 3 searches" in search_prompt
    assert "Prior:[]" in search_prompt
    assert "Used:0" in search_prompt
    assert "CC:2" in search_prompt
    
    # Verify search prompt excludes URLs and titles (no documents to leak from)
    TestHelpers.assert_prompt_excludes_urls_and_titles(search_prompt, "Initial search prompt should not contain URLs or titles: ")


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
    
    # Verify document store has documents from analyzed search results
    TestHelpers.assert_document_store_length(result[StateKeys.TOOL_SAVED_INFO], 2, "Should have 2 analyzed facts in tool_saved_info: ")
    TestHelpers.assert_documents_have_urls_and_titles(result[StateKeys.TOOL_SAVED_INFO], "Analyzed documents should have proper URLs and titles: ")
    
    # Verify analyze step was called
    assert structured_llm.was_called()
    analyze_prompt = structured_llm.get_last_prompt()
    assert '"Search 1: alpha-1"' in analyze_prompt
    assert "Content about alpha-1" in analyze_prompt
    
    # Verify analyze prompt excludes URLs and titles
    TestHelpers.assert_prompt_excludes_urls_and_titles(analyze_prompt, "Analyze prompt should not contain URLs or titles: ")
    
    # Verify search prompt includes analyzed facts content
    search_prompt = tools_llm.get_last_prompt()
    assert "Saved:" in search_prompt
    assert '"alpha-1"' in search_prompt
    assert "You already used 1 searches." in search_prompt
    assert "Analyzed fact 1 from search results" in search_prompt, "Search prompt should contain analyzed facts content"
    assert "Analyzed fact 2 from search results" in search_prompt, "Search prompt should contain analyzed facts content"
    
    # Verify search prompt excludes URLs and titles
    TestHelpers.assert_prompt_excludes_urls_and_titles(search_prompt, "Search prompt should not contain URLs or titles: ")


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
    
    # Verify document store has documents from analyzed search results
    TestHelpers.assert_document_store_length(result[StateKeys.TOOL_SAVED_INFO], 2, "Should have 2 analyzed facts in tool_saved_info: ")
    TestHelpers.assert_documents_have_urls_and_titles(result[StateKeys.TOOL_SAVED_INFO], "Analyzed documents should have proper URLs and titles: ")
    
    # Verify analyze prompt includes all queries and their content
    analyze_prompt = structured_llm.get_last_prompt()
    assert '"Search 1: alpha-1"' in analyze_prompt
    assert '"Search 2: alpha-2"' in analyze_prompt
    assert '"Search 3: alpha-3"' in analyze_prompt
    assert "Content about alpha-1" in analyze_prompt, "Analyze prompt should contain tool call content"
    assert "Content about alpha-2" in analyze_prompt, "Analyze prompt should contain tool call content"
    assert "Content about alpha-3" in analyze_prompt, "Analyze prompt should contain tool call content"
    
    # Verify analyze prompt excludes URLs and titles
    TestHelpers.assert_prompt_excludes_urls_and_titles(analyze_prompt, "Multi-query analyze prompt should not contain URLs or titles: ")


def test_hard_limit_reached_skips_search_and_formats(search_config, search_limits, mock_llms):
    """If used == max_searches, we do NOT call tool LLM; we immediately format and finish."""
    structured_llm, tools_llm = mock_llms
    
    # Create existing documents in TOOL_SAVED_INFO from previous searches
    from agent.citation.document import DocumentStore, Document
    existing_tool_saved_info = DocumentStore([
        Document(id="previous_fact_1", title="Previous Fact 1", url="https://example.com/fact1", content="Previous analyzed fact 1"),
        Document(id="previous_fact_2", title="Previous Fact 2", url="https://example.com/fact2", content="Previous analyzed fact 2"),
        Document(id="previous_fact_3", title="Previous Fact 3", url="https://example.com/fact3", content="Previous analyzed fact 3")
    ])
    
    # Setup: Already used 3 searches (equals max)
    state = TestHelpers.create_state(
        search_limits=search_limits,
        ai_queries=[
            TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "q-1"})]),
            TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "q-2"})]),
            TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "q-3"})])
        ],
        tool_last_output=[TestHelpers.create_tool_output_message("q-3")],
        last_tool_call_count=1,
        tool_saved_info=existing_tool_saved_info
    )
    
    result = execute_search_pattern_flexible(state, structured_llm, tools_llm, search_config)
    
    # Verify finalization
    assert set(result.keys()) == {StateKeys.FINAL_OUTPUT, StateKeys.AI_QUERIES}
    assert TestHelpers.is_document_store(result[StateKeys.FINAL_OUTPUT])
    assert result[StateKeys.AI_QUERIES][0].content == "no more searches"
    
    # Verify final output document store has processed documents from formatting (only 2 facts from format LLM)
    TestHelpers.assert_document_store_length(result[StateKeys.FINAL_OUTPUT], 2, "Should have 2 formatted facts in final_output (format LLM output): ")
    TestHelpers.assert_documents_have_urls_and_titles(result[StateKeys.FINAL_OUTPUT], "Final output documents should have proper URLs and titles: ")
    # Verify search LLM was NOT called
    assert not tools_llm.was_called()
    
    # Verify both analyze and format were called
    assert structured_llm.call_count() == 2  # analyze + format
    
    # Get the format prompt and verify it contains both existing and analyzed content
    format_prompts = [prompt for prompt in structured_llm._prompts if "FORMAT:" in prompt]
    assert len(format_prompts) == 1, "Should have exactly one FORMAT prompt"
    format_prompt = format_prompts[0]
    
    # Verify format prompt contains existing TOOL_SAVED_INFO content (3 previous facts)
    assert "Previous analyzed fact 1" in format_prompt, "Format prompt should contain existing tool_saved_info"
    assert "Previous analyzed fact 2" in format_prompt, "Format prompt should contain existing tool_saved_info"  
    assert "Previous analyzed fact 3" in format_prompt, "Format prompt should contain existing tool_saved_info"
    
    # Verify format prompt contains newly analyzed facts from q-3 tool output
    assert "Analyzed fact 1 from search results" in format_prompt, "Format prompt should contain analyzed facts from tool_last_output"
    assert "Analyzed fact 2 from search results" in format_prompt, "Format prompt should contain analyzed facts from tool_last_output"


def test_llm_decides_no_more_searches_returns_final(search_config, search_limits, mock_llms):
    """LLM responds without tool_calls -> we format and finish."""
    structured_llm, tools_llm = mock_llms
    
    # Setup: LLM returns no tool calls (decides it's enough)
    tools_llm.setup_responses([
        AIMessage(content="I have enough information", tool_calls=[])
    ])
    
    # Create existing documents in TOOL_SAVED_INFO from previous searches
    from agent.citation.document import DocumentStore, Document
    existing_tool_saved_info = DocumentStore([
        Document(id="prev_search_1", title="Previous Search Result 1", url="https://example.com/prev1", content="Previous search content 1"),
        Document(id="prev_search_2", title="Previous Search Result 2", url="https://example.com/prev2", content="Previous search content 2")
    ])
    
    state = TestHelpers.create_state(
        search_limits=search_limits,
        ai_queries=[TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "alpha-1"})])],
        tool_last_output=[TestHelpers.create_tool_output_message("alpha-1")],
        last_tool_call_count=1,
        tool_saved_info=existing_tool_saved_info
    )
    
    result = execute_search_pattern_flexible(state, structured_llm, tools_llm, search_config)
    
    # Verify finalization
    assert set(result.keys()) == {StateKeys.FINAL_OUTPUT, StateKeys.AI_QUERIES}
    assert TestHelpers.is_document_store(result[StateKeys.FINAL_OUTPUT])
    assert result[StateKeys.AI_QUERIES][0].content == "no more searches"
    
    # Verify final output document store has processed documents from formatting (only 2 facts from format LLM)
    TestHelpers.assert_document_store_length(result[StateKeys.FINAL_OUTPUT], 2, "Should have 2 formatted facts in final_output (format LLM output): ")
    TestHelpers.assert_documents_have_urls_and_titles(result[StateKeys.FINAL_OUTPUT], "Final output documents should have proper URLs and titles: ")
    
    # Verify prompts include prior context
    search_prompt = tools_llm.get_last_prompt()
    assert '"alpha-1"' in search_prompt
    
    # Verify analyze was called and format prompt contains both existing and analyzed content
    assert structured_llm.call_count() == 2  # analyze + format
    
    # Get the format prompt (the second call to structured LLM)
    format_prompts = [prompt for prompt in structured_llm._prompts if "FORMAT:" in prompt]
    assert len(format_prompts) == 1, "Should have exactly one FORMAT prompt"
    format_prompt = format_prompts[0]
    
    # Verify format prompt contains existing TOOL_SAVED_INFO content
    assert "Previous search content 1" in format_prompt, "Format prompt should contain existing tool_saved_info"
    assert "Previous search content 2" in format_prompt, "Format prompt should contain existing tool_saved_info"
    
    # Verify format prompt contains analyzed facts content  
    assert "Analyzed fact 1 from search results" in format_prompt, "Format prompt should contain analyzed facts"
    assert "Analyzed fact 2 from search results" in format_prompt, "Format prompt should contain analyzed facts"


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
    
    # Verify document store has documents from analyzed search results
    TestHelpers.assert_document_store_length(result[StateKeys.TOOL_SAVED_INFO], 2, "Should have 2 analyzed facts in tool_saved_info: ")
    TestHelpers.assert_documents_have_urls_and_titles(result[StateKeys.TOOL_SAVED_INFO], "Analyzed documents should have proper URLs and titles: ")
    
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
    
    @staticmethod
    def assert_document_store_length(doc_store, expected_length, message=""):
        """Assert that a DocumentStore has the expected length."""
        from agent.citation.document import DocumentStore
        assert isinstance(doc_store, DocumentStore), f"Expected DocumentStore, got {type(doc_store)}"
        actual_length = len(doc_store)
        assert actual_length == expected_length, f"{message}Expected {expected_length} documents, got {actual_length}"
    
    @staticmethod
    def assert_documents_have_urls_and_titles(doc_store, message=""):
        """Assert that all documents in the store have proper URLs and titles."""
        from agent.citation.document import DocumentStore
        assert isinstance(doc_store, DocumentStore), f"Expected DocumentStore, got {type(doc_store)}"
        
        for i, doc in enumerate(doc_store):
            assert hasattr(doc, 'url'), f"{message}Document {i} missing 'url' attribute"
            assert hasattr(doc, 'title'), f"{message}Document {i} missing 'title' attribute"
            assert hasattr(doc, 'id'), f"{message}Document {i} missing 'id' attribute"
            assert hasattr(doc, 'content'), f"{message}Document {i} missing 'content' attribute"
            
            # Check that URLs look roughly correct (not empty and contain http/https or are special cases like "")
            if doc.url:  # Allow empty URLs for special documents like "answer"
                assert doc.url.startswith(('http://', 'https://')), f"{message}Document {i} has invalid URL: {doc.url}"
            
            # Check that titles are not empty (unless it's a special case)
            assert isinstance(doc.title, str), f"{message}Document {i} title must be string, got {type(doc.title)}"
            
            # Check that IDs are reasonable
            assert doc.id and isinstance(doc.id, str), f"{message}Document {i} must have valid ID, got: {doc.id}"
    
    @staticmethod
    def assert_prompt_excludes_urls_and_titles(prompt_text, message=""):
        """Assert that a prompt does not contain URLs or document titles."""
        # Check for common URL patterns (more specific to avoid false positives)
        url_patterns = [
            r'https?://[^\s]+',  # HTTP/HTTPS URLs
            r'www\.[^\s]+\.[a-zA-Z]{2,}',      # www. domains with valid TLD
            r'\b[a-zA-Z0-9-]+\.[a-zA-Z]{2,}/[^\s]*',  # domain with path
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, prompt_text)
            assert not matches, f"{message}Prompt contains URLs: {matches}"
        
        # Check that prompt doesn't contain title-like patterns from test data
        # (We know our test data uses titles like "Result for {query}")
        title_patterns = [
            r'Result for [^\s]+',
            r'Title:\s*[^\n]+',
            r'URL:\s*https?://[^\s]+',
        ]
        
        for pattern in title_patterns:
            matches = re.findall(pattern, prompt_text, re.IGNORECASE)
            assert not matches, f"{message}Prompt contains title/URL indicators: {matches}"


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
        """Record the prompt and return mock facts based on the prompt content."""
        self.parent_llm.record_call(prompt)
        
        # Extract document ID from prompt content - look for common patterns
        doc_id = "result_for_q-3"  # default
        if "alpha-1" in prompt:
            doc_id = "result_for_alpha-1"
        elif "alpha-2" in prompt:
            doc_id = "result_for_alpha-2"
        elif "alpha-3" in prompt:
            doc_id = "result_for_alpha-3"
        elif "seed" in prompt:
            doc_id = "result_for_seed"
        elif "p-1" in prompt:
            doc_id = "result_for_p-1"
        elif "p-2" in prompt:
            doc_id = "result_for_p-2"
        elif "p-3" in prompt:
            doc_id = "result_for_p-3"
        elif "q-3" in prompt:
            doc_id = "result_for_q-3"
        
        # Generate facts based on whether this is an analyze or format call
        if "ANALYZE:" in prompt:
            facts = [
                {"fact": f"Analyzed fact 1 from search results", "document_id": doc_id},
                {"fact": f"Analyzed fact 2 from search results", "document_id": "answer"}
            ]
        elif "FORMAT:" in prompt:
            facts = [
                {"fact": f"Formatted fact 1 combining all search results", "document_id": doc_id},
                {"fact": f"Formatted fact 2 with comprehensive analysis", "document_id": "answer"}
            ]
        else:
            facts = [
                {"fact": f"Default fact 1 from search analysis", "document_id": doc_id},
                {"fact": f"Default fact 2 from search analysis", "document_id": "answer"}
            ]
            
        return {"facts": facts}


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


def test_existing_tool_saved_info_plus_new_analysis_plus_more_searches(search_config, search_limits, mock_llms):
    """Test scenario with existing tool_saved_info + tool_last_output analysis + LLM requesting more searches.
    
    This tests the complete document flow:
    1. Start with existing facts in TOOL_SAVED_INFO (from previous searches)
    2. Analyze new tool_last_output to create additional facts  
    3. LLM decides to make more tool calls
    4. Resulting TOOL_SAVED_INFO contains only newly analyzed facts (documents current behavior)
    
    IMPORTANT: This test reveals that existing TOOL_SAVED_INFO is NOT combined with newly 
    analyzed facts in the return value. However, both existing and new facts ARE passed
    to the search prompt generation. This may be a bug in the implementation.
    """
    structured_llm, tools_llm = mock_llms
    
    # Setup: LLM will request one more search
    tools_llm.setup_responses([
        TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "follow-up-search"})])
    ])
    
    # Create existing documents in TOOL_SAVED_INFO from previous searches
    from agent.citation.document import DocumentStore, Document
    existing_tool_saved_info = DocumentStore([
        Document(id="existing_fact_1", title="Existing Fact 1", url="https://example.com/existing1", content="Previously analyzed content 1"),
        Document(id="existing_fact_2", title="Existing Fact 2", url="https://example.com/existing2", content="Previously analyzed content 2"),
        Document(id="existing_fact_3", title="Existing Fact 3", url="https://example.com/existing3", content="Previously analyzed content 3")
    ])
    
    # Setup state with both existing TOOL_SAVED_INFO and new tool_last_output
    state = TestHelpers.create_state(
        search_limits=search_limits,
        ai_queries=[TestHelpers.create_ai_message_with_tool_calls([("tavily_search_results_json", {"query": "recent-query"})])],
        tool_last_output=[TestHelpers.create_tool_output_message("recent-query")],
        last_tool_call_count=1,
        tool_saved_info=existing_tool_saved_info
    )
    
    result = execute_search_pattern_flexible(state, structured_llm, tools_llm, search_config)
    
    # Verify return structure (should continue with more searches, not finalize)
    assert set(result.keys()) == {StateKeys.AI_QUERIES, StateKeys.TOOL_SAVED_INFO, StateKeys.LAST_TOOL_CALL_COUNT}
    assert result[StateKeys.LAST_TOOL_CALL_COUNT] == 1
    

    TestHelpers.assert_document_store_length(result[StateKeys.TOOL_SAVED_INFO], 2, " only newly analyzed facts: merge is through langchain chain, not here")
    
    
    # Verify the newly analyzed content is present
    analyzed_content = result[StateKeys.TOOL_SAVED_INFO].get_document_content_as_str()
    
    # Check that newly analyzed facts are present
    assert "Analyzed fact 1 from search results" in analyzed_content, "Should include newly analyzed fact 1"
    assert "Analyzed fact 2 from search results" in analyzed_content, "Should include newly analyzed fact 2"
    assert "Previously analyzed content 1" not in analyzed_content, "Should NOT include existing already analyzed content"
    
    # Verify analyze step was called
    assert structured_llm.was_called()
    analyze_prompt = structured_llm.get_last_prompt()
    assert '"Search 1: recent-query"' in analyze_prompt
    assert "Content about recent-query" in analyze_prompt
    
    # Verify search prompt includes the combined content that was passed to search generation
    search_prompt = tools_llm.get_last_prompt()
    assert "Saved:" in search_prompt
    assert '"recent-query"' in search_prompt
    assert "You already used 1 searches." in search_prompt
    
    # The search prompt should contain both existing and newly analyzed facts
    assert "Previously analyzed content 1" in search_prompt, "Search prompt should contain existing facts"
    assert "Previously analyzed content 2" in search_prompt, "Search prompt should contain existing facts" 
    assert "Previously analyzed content 3" in search_prompt, "Search prompt should contain existing facts"
    
    # Verify search prompt contains content from newly analyzed facts
    assert "Analyzed fact 1 from search results" in search_prompt, "Search prompt should contain newly analyzed facts"
    assert "Analyzed fact 2 from search results" in search_prompt, "Search prompt should contain newly analyzed facts"
