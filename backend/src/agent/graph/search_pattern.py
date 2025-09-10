"""
Refactored: Flexible Search Pattern (drop‑in outputs, typed internals)
- Keeps EXACT output keys: "ai_queries", "tool_saved_info", "last_tool_call_count" OR
  "final_output", "ai_queries".
- Uses CONSTs for state keys.
- Splits LLM logic into dedicated private methods.
- Adds typed internal result classes.
- Clear scenario paths without IF-maze.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Annotated
import json
import logging
from pydantic import BaseModel, Field

from typing_extensions import Literal
from langchain_core.messages import AIMessage
from langgraph.graph.message import add_messages

from agent.citation.document import (
    DocumentStore,
    SourcedFactsList,
)
from agent.graph.retry_utils import retry_llm_tool_call


# ====== Constants for state/return keys ======
class StateKeys:
    AI_QUERIES = "ai_queries"
    TOOL_SAVED_INFO = "tool_saved_info"
    TOOL_LAST_OUTPUT = "tool_last_output"
    FINAL_OUTPUT = "final_output"
    LAST_TOOL_CALL_COUNT = "last_tool_call_count"
    SEARCH_LIMITS = "search_limits"


# ====== External config/typed state ======
class BaseSearchState(TypedDict):
    ai_queries: Annotated[List[AIMessage], add_messages]
    tool_saved_info: DocumentStore
    tool_last_output: List[AIMessage]
    final_output: DocumentStore
    last_tool_call_count: int
    search_limits: Any  


class SearchConfig(BaseModel):
    analyze_prompt: str = Field(description="Step 1: Analyze last tool call")
    search_prompt: str = Field(description="Step 2: Generate new search or done")
    format_prompt: str = Field(description="Step 3: Format final output")
    state_field_mapping: Dict[str, str] = Field(description="Map template vars to state fields")
    component_name: str = Field(description="Component name for search limits")

    def get_max_searches(self, search_limits) -> int:
        component_limits = {
            "product_exploration": search_limits.product_exploration_max_searches,
            "product_research": search_limits.product_research_max_searches,
            "final_product_info": search_limits.final_product_info_max_searches,
        }
        return component_limits.get(self.component_name, 3)


# ====== Internal typed results (not exposed to graph) ======
@dataclass(frozen=True)
class RequestMoreSearches:
    ai_query: AIMessage
    last_tool_call_count: int
    tool_saved_info: DocumentStore


@dataclass(frozen=True)
class FinishWithDocuments:
    final_output: DocumentStore


class FlexibleSearchRunner:
    """Encapsulates 3-step flow with typed internals and drop-in outputs."""

    def __init__(self, llm, llm_with_tools, config: SearchConfig):
        self.llm = llm
        self.llm_with_tools = llm_with_tools
        self.config = config
        self._log = logging.getLogger(__name__)

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        analysis_docs = self._analyze_past_search_result_from_tool(state)

        decision = self._create_search_tool_calls_if_needed(state, analysis_docs)

        if isinstance(decision, RequestMoreSearches):
            # Scenario A: No previous tool call → tool call → finish
            # Scenario B: Previous tool call → more tool call → finish
            return {
                StateKeys.AI_QUERIES: [decision.ai_query],
                StateKeys.TOOL_SAVED_INFO: analysis_docs,
                StateKeys.LAST_TOOL_CALL_COUNT: decision.last_tool_call_count,
            }

        # Scenario C: Previous tool call → no more tool call → format → finish
        assert isinstance(decision, FinishWithDocuments)
        return {
            StateKeys.FINAL_OUTPUT: decision.final_output,
            StateKeys.AI_QUERIES: [AIMessage(content="no more searches")],
        }

    # ---- LLM steps (private) ----
    def _analyze_past_search_result_from_tool(self, state: Dict[str, Any]) -> DocumentStore:
        """Analyze last tool call outputs → DocumentStore with citations.
        Orchestrates small, well-named helpers for clarity.
        """
        recent_outputs = self._recent_tool_outputs(state)
        if not recent_outputs:
            self._log.debug("No last tool call outputs, skipping analysis")
            return DocumentStore()

        tool_arguments = self._extract_tool_arguments(state, count=len(recent_outputs))
        documents = self._documents_from_tool_outputs(recent_outputs)
        return self._format_and_call_analyze(state, documents, tool_arguments)

    # ---- _llm_analyze helpers ----
    def _recent_tool_outputs(self, state: Dict[str, Any]) -> List[AIMessage]:
        """Slice the last N tool outputs based on LAST_TOOL_CALL_COUNT."""
        tool_last_output: List[AIMessage] = state.get(StateKeys.TOOL_LAST_OUTPUT, [])
        last_tool_call_count: int = state.get(StateKeys.LAST_TOOL_CALL_COUNT, 1)
        if not tool_last_output:
            return []
        if last_tool_call_count <= 0:
            return []
        if len(tool_last_output) >= last_tool_call_count:
            recent = tool_last_output[-last_tool_call_count:]
        else:
            recent = tool_last_output
        self._log.debug("Analyzing %d recent tool call outputs", len(recent))
        return recent

    def _extract_tool_arguments(self, state: Dict[str, Any], count: int) -> List[str]:
        """Collect the textual arguments (queries) that produced the last tool calls."""
        ai_queries: List[AIMessage] = state.get(StateKeys.AI_QUERIES, [])
        if not ai_queries:
            return []
        last_ai = ai_queries[-1]
        args: List[str] = []
        if getattr(last_ai, "tool_calls", None):
            actual = last_ai.tool_calls[:count]
            for i, tc in enumerate(actual, 1):
                q = tc.get("args", {}).get("query", "")
                args.append(f"Search {i}: {q}")
        else:
            args.append("No tool call arguments found")
        return args

    def _documents_from_tool_outputs(self, outputs: List[AIMessage]) -> DocumentStore:
        """Parse tool outputs (JSON in message.content) and merge into a DocumentStore."""
        stores: List[DocumentStore] = []
        for msg in outputs:
            try:
                payload = json.loads(msg.content)
                stores.append(DocumentStore.add_documents_from_tavily(payload))
            except Exception as e:
                self._log.warning("Failed to parse tool output as JSON: %s", e)
        return DocumentStore.merge(stores) if stores else DocumentStore()

    def _format_and_call_analyze(
        self,
        state: Dict[str, Any],
        documents: DocumentStore,
        tool_arguments: List[str],
    ) -> DocumentStore:
        """Build analyze prompt and call the structured LLM; return recreated DocumentStore."""
        tool_context = {
            "last_tool_call_arguments": json.dumps(tool_arguments),
            "last_tool_call_output": documents.get_document_content_as_str(),
        }
        format_ctx = self._apply_state_mapping(state, self.config.state_field_mapping, tool_context)
        prompt = self.config.analyze_prompt.format(**format_ctx)

        output_format_prompt = (
            """
            All returned insights should have citations to the source documents. 
            Document all have after their content [ref:document_id].
            Return you output as a list of Facts. Each fact has content write as instructed in the beginning of the prompt, 
            and a document_id field with the source document id.
        """
        )
        llm_with_format = self.llm.with_structured_output(SourcedFactsList)
        result = llm_with_format.invoke(prompt + output_format_prompt)
        return documents.recreate_from_sourced_facts(result)

    def _create_search_tool_calls_if_needed(self, state: Dict[str, Any], analysis_docs: DocumentStore) -> RequestMoreSearches | FinishWithDocuments:
        """Generate new searches or decide to stop; respects limits."""
        tool_saved_info: DocumentStore = state.get(StateKeys.TOOL_SAVED_INFO) or DocumentStore()
        ai_queries: List[AIMessage] = state.get(StateKeys.AI_QUERIES, [])

        search_limits = state.get(StateKeys.SEARCH_LIMITS)

        max_searches, concurrent_count = self._limits_for_component(search_limits, self.config.component_name)
        if self._should_stop_searching(len(ai_queries), max_searches):
            self._log.debug("Reached max searches (%s). Formatting final output.", max_searches)
            return FinishWithDocuments(final_output=self._format_all_findings_into_desired_schema(state, analysis_docs, tool_saved_info))
        
        number_of_used_ai_queries = len(ai_queries)
        search_limit_text = self._get_search_limit_text(number_of_used_ai_queries, max_searches)
        prior_queries = self._get_prior_queries(ai_queries)

        result_search_query = self._execute_search_generation(state, analysis_docs, tool_saved_info, concurrent_count, search_limit_text, prior_queries, number_of_used_ai_queries)

        if result_search_query:
            actual_tool_call_count = len(getattr(result_search_query, "tool_calls", []) or [])
            if actual_tool_call_count > 0:
                self._log.debug("Prepared %d parallel search queries", actual_tool_call_count)
                return RequestMoreSearches(
                    ai_query=result_search_query,
                    last_tool_call_count=actual_tool_call_count,
                    tool_saved_info=analysis_docs,
                )
        else:
            self._log.warning("All retry attempts failed for tool call. Formatting final output.")
        # No tool calls → proceed to format
        return FinishWithDocuments(final_output=self._format_all_findings_into_desired_schema(state, analysis_docs, tool_saved_info))

    def _get_search_limit_text(self, used: int, max_searches: int) -> str:
        """Generate search limit text based on usage."""
        return (
            f"- Max {max_searches} searches for this task. You already used {used} searches."
            if used > 0
            else f"- Use a MAX of {max_searches} searches for this task, ideally fewer."
        )

    def _get_prior_queries(self, ai_queries: List[AIMessage]) -> List[str]:
        """Extract prior query strings from AI messages."""
        prior_queries = []
        for msg in ai_queries:
            try:
                prior_queries.append(msg.tool_calls[0].get("args", {}).get("query", ""))
            except Exception:
                prior_queries.append("")
        return prior_queries

    def _execute_search_generation(self, state: Dict[str, Any], analysis_docs: DocumentStore, tool_saved_info: DocumentStore, concurrent_count: int, search_limit_text: str, prior_queries: List[str],  number_of_used_ai_queries: int) -> RequestMoreSearches | FinishWithDocuments:

        search_context = {
            "tool_saved_info": json.dumps(
                tool_saved_info.get_document_content_as_str() + analysis_docs.get_document_content_as_str()
            ),
            "ai_queries": json.dumps(prior_queries),
            "len_ai_queries": number_of_used_ai_queries,
            "search_limit_text": search_limit_text,
            "concurrent_searches": concurrent_count,
        }

        format_ctx = self._apply_state_mapping(state, self.config.state_field_mapping, search_context)
        prompt = self.config.search_prompt.format(**format_ctx)

        # Execute with retry (LLM with tools)
        result_search_query: Optional[AIMessage] = retry_llm_tool_call(self.llm_with_tools, prompt)

        return result_search_query

        

    def _format_all_findings_into_desired_schema(
        self,
        state: Dict[str, Any],
        analysis_docs: DocumentStore,
        serializable_tool_info: DocumentStore,
    ) -> DocumentStore:
        serializable_tool_info = serializable_tool_info or DocumentStore()

        final_context = {
            "tool_saved_info": serializable_tool_info.get_document_content_as_str()
            + analysis_docs.get_document_content_as_str(),
        }
        format_ctx = self._apply_state_mapping(state, self.config.state_field_mapping, final_context)
        prompt = self.config.format_prompt.format(**format_ctx)

        output_format_prompt = (
            "\nAll returned insights should have citations to the source documents. "
            "Document all have after their content [ref:document_id].\n"
            "Return you output as a list of Facts. Each fact has content write as instructed in the beginning of the prompt, "
            "and a document_id field with the source document id.\n"
        )
        llm_with_format = self.llm.with_structured_output(SourcedFactsList)
        result = llm_with_format.invoke(prompt + output_format_prompt)

        merged = serializable_tool_info + analysis_docs
        return merged.recreate_from_sourced_facts(result)

    # ---- Helpers ----
    @staticmethod
    def _apply_state_mapping(
        state: Dict[str, Any], mapping: Dict[str, str], extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        ctx: Dict[str, str] = {}
        for template_key, state_key in mapping.items():
            value = state.get(state_key, "")
            if isinstance(value, list):
                ctx[template_key] = " ,".join(str(v) for v in value)
            else:
                ctx[template_key] = str(value)
        if extra:
            ctx.update({k: str(v) for k, v in extra.items()})
        return ctx

    @staticmethod
    def _limits_for_component(search_limits, component_name: str) -> Tuple[int, int]:
        """Return (max_searches, concurrent_count) using match for clarity."""
        match component_name:
            case "product_exploration":
                return (
                    search_limits.product_exploration_max_searches,
                    search_limits.product_exploration_concurrent_searches,
                )
            case "product_research":
                return (
                    search_limits.product_research_max_searches,
                    search_limits.product_research_concurrent_searches,
                )
            case "final_product_info":
                return (
                    search_limits.final_product_info_max_searches,
                    search_limits.final_product_info_concurrent_searches,
                )
            case _:
                raise ValueError(f"Unknown component name: {component_name}")

    @staticmethod
    def _should_stop_searching(used: int, max_allowed: int) -> bool:
        return used >= max_allowed


# ====== Thin, drop-in compatible function (same name & outputs) ======

def execute_search_pattern_flexible(
    state: Dict[str, Any],
    llm,
    llm_with_tools,
    config: SearchConfig,
) -> Dict[str, Any]:
    """Backward-compatible adapter around FlexibleSearchRunner.run()."""
    runner = FlexibleSearchRunner(llm=llm, llm_with_tools=llm_with_tools, config=config)
    return runner.run(state)
