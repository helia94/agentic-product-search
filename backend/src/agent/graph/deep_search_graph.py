"""
Research Agent Using Generic Search Pattern

This shows how to use the reusable search pattern in your research agent.
Your exact logic and prompts, just organized through the pattern.
"""

import os
from typing import List
from typing_extensions import TypedDict
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated

from dotenv import load_dotenv

from agent.graph.search_pattern import SearchConfig
load_dotenv()

from agent.graph.state_V2 import ProductSimple
from agent.configuration.llm_setup import get_llm
from agent.utils.tool_orchestrator import DynamicTavilyToolOrchestrator
from agent.graph.search_pattern import BaseSearchState, execute_search_pattern_flexible
from agent.configuration.search_limits import ComponentNames, SearchLimitsConfig
from langchain_tavily import TavilySearch

from langchain.globals import set_debug
from agent.prompts.deep_search.deep_search_analyze_prompt import DEEP_SEARCH_ANALYZE_PROMPT
from agent.prompts.deep_search.deep_search_format_prompt import DEEP_SEARCH_FORMAT_PROMPT
from agent.prompts.deep_search.deep_search_search_prompt import DEEP_SEARCH_SEARCH_PROMPT
from agent.configuration.search_limits import Low
set_debug(True)


# Your state extends the base search state
class ProductResearchState(BaseSearchState):
    """Your exact state structure using the search pattern base"""
    # Add your domain-specific fields
    query: str
    criteria: List[str]
    product: ProductSimple
    search_limits: SearchLimitsConfig
    
    # BaseSearchState provides:
    # ai_queries: Annotated[List[AIMessage], add_messages]
    # tool_saved_info: Annotated[List[str], add_messages]
    # tool_last_output: List[AIMessage]
    # final_output: str

# Dynamic tool orchestrator for product research
tools_orchestrator = DynamicTavilyToolOrchestrator(
    component_name=ComponentNames.PRODUCT_RESEARCH,
    input_field="ai_queries", 
    output_field="tool_last_output"
)




# Pre-configured examples for different domains
def create_product_research_config() -> SearchConfig:
    """Your exact product research configuration"""
    
    return SearchConfig(
        analyze_prompt=DEEP_SEARCH_ANALYZE_PROMPT,
        search_prompt=DEEP_SEARCH_SEARCH_PROMPT,
        format_prompt=DEEP_SEARCH_FORMAT_PROMPT,

        state_field_mapping={
            "product": "product",
            "criteria": "criteria"
        },
        
        component_name=ComponentNames.PRODUCT_RESEARCH
    )


def chatbot_research_with_pattern(state: ProductResearchState):
    """
    Your exact research logic using the flexible pattern.
    Same execution, same prompts, configurable state mapping.
    """
    
    # Create config with your exact prompts and state mapping
    config = create_product_research_config()
    search_limits = state.get("search_limits")
    
    # Execute the 3-step pattern with your exact logic
    return execute_search_pattern_flexible(
        state=state,
        llm=get_llm("search_pattern"),
        llm_with_tools=tools_orchestrator.bind_tools_to_llm(get_llm("pattern_tool_calls"), search_limits),
        config=config
    )


def route_tools(state: ProductResearchState):
    """Simple routing logic"""
    ai_queries = state.get("ai_queries", [])
    print(f"[DEBUG] route_tools called with {len(ai_queries)} ai_queries")
    if ai_queries:
        print(f"[DEBUG] Last ai_query has tool_calls: {hasattr(ai_queries[-1], 'tool_calls') and len(ai_queries[-1].tool_calls) > 0}")
    
    result = tools_orchestrator.router("tools")(state)
    print(f"[DEBUG] route_tools returning: {result}")
    return result


# Tool node function that creates tools dynamically
def tool_node_research(state: ProductResearchState):
    """Tool node that creates tools dynamically based on search_limits from state"""
    search_limits = state.get("search_limits")
    return tools_orchestrator.tool_node(search_limits)(state)

# Your exact graph structure - cleaned up
def create_research_graph():
    graph_builder = StateGraph(ProductResearchState)

    graph_builder.add_node("tool_node_research", tool_node_research)
    graph_builder.add_node("chatbot_research", chatbot_research_with_pattern)  # Only change: use pattern

    graph_builder.add_edge(START, "chatbot_research")

    graph_builder.add_conditional_edges(
        "chatbot_research",
        route_tools,
        {"tools": "tool_node_research", END: END}
    )
    graph_builder.add_edge("tool_node_research", "chatbot_research")

    return graph_builder.compile()


research_graph_with_pattern = create_research_graph()


if __name__ == "__main__":
    """Test the pattern-based research agent"""
    
    print("🔬 Testing Research Agent with Search Pattern")
    print("=" * 60)
    
    for event in research_graph_with_pattern.stream({
        "criteria": [
            "price",
            "IOS app insights and interpretability"
        ],
        "product": {
            "id": "fitbit-charge-6",
            "name": "Fitbit Charge 6", 
            "USP": "GPS, Google, ECG",
            "use_case": "Serious fitness tracking",
            "other_info": "40+ modes, 7-day battery, $160"
        },
        "search_limits": Low(),
    }):
        print("Event", event.keys())
        
        if "chatbot_research" in event and "final_output" in event["chatbot_research"]:
            final_output = event["chatbot_research"]["final_output"]
            print("✅ Final Research Output:")
            print("-" * 40)
            print(final_output[:500] + "..." if len(final_output) > 500 else final_output)