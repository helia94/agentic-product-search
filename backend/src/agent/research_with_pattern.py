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
load_dotenv()

from agent.state_V2 import ProductSimple
from agent.basic_tools import llm_gemini, tavily
from agent.tool_orchestrator import AgentToolOrchestrator
from agent.search_pattern import BaseSearchState, execute_search_pattern_flexible, create_product_research_config

from langchain.globals import set_debug
set_debug(True)


# Your state extends the base search state
class ProductResearchState(BaseSearchState):
    """Your exact state structure using the search pattern base"""
    # Add your domain-specific fields
    query: str
    criteria: List[str]
    product: ProductSimple
    
    # BaseSearchState provides:
    # ai_queries: Annotated[List[AIMessage], add_messages]
    # tool_saved_info: Annotated[List[str], add_messages]
    # tool_last_output: List[AIMessage]
    # final_output: str

# Tool orchestrator for this agent
tool_orchestrator = AgentToolOrchestrator(tools=[tavily])


def chatbot_research_with_pattern(state: ProductResearchState):
    """
    Your exact research logic using the flexible pattern.
    Same execution, same prompts, configurable state mapping.
    """
    
    # Create config with your exact prompts and state mapping
    config = create_product_research_config()
    
    # Execute the 3-step pattern with your exact logic
    return execute_search_pattern_flexible(
        state=state,
        llm=llm_gemini,
        llm_with_tools=tool_orchestrator.get_llm_with_tools(llm_gemini),
        config=config
    )


def route_tools(state: ProductResearchState):
    """Clean routing logic using tool orchestrator"""
    ai_queries = state.get("ai_queries", [])
    print(f"[DEBUG] route_tools called with {len(ai_queries)} ai_queries")
    if ai_queries:
        print(f"[DEBUG] Last ai_query has tool_calls: {hasattr(ai_queries[-1], 'tool_calls') and len(ai_queries[-1].tool_calls) > 0}")
    
    result = tool_orchestrator.create_router_function("tools")(state)
    print(f"[DEBUG] route_tools returning: {result}")
    return result


# Your exact graph structure - cleaned up
def create_research_graph():
    graph_builder = StateGraph(ProductResearchState)
    tool_node_research = tool_orchestrator.create_tool_node()

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
        }
    }):
        print("Event", event.keys())
        
        if "chatbot_research" in event and "final_output" in event["chatbot_research"]:
            final_output = event["chatbot_research"]["final_output"]
            print("✅ Final Research Output:")
            print("-" * 40)
            print(final_output[:500] + "..." if len(final_output) > 500 else final_output)