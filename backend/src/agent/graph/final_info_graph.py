"""
Final Info Graph - Product Information Completion Agent

This agent fills remaining ProductFull fields using web search.
"""

import os
import json
from typing import List
from datetime import datetime
from typing_extensions import TypedDict
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated

from dotenv import load_dotenv
load_dotenv()

from langchain.globals import set_debug, set_verbose
from agent.graph.state_V2 import ProductFull
from agent.configuration.llm_setup import get_llm
from agent.utils.tool_orchestrator import DynamicTavilyToolOrchestrator
from agent.graph.search_pattern import BaseSearchState, execute_search_pattern_flexible, SearchConfig
from agent.configuration.search_limits import ComponentNames, SearchLimitsConfig
from langchain_tavily import TavilySearch
from agent.prompts.final_info.final_info_analyze_prompt import FINAL_INFO_ANALYZE_PROMPT
from agent.prompts.final_info.final_info_search_prompt import FINAL_INFO_SEARCH_PROMPT
from agent.prompts.final_info.final_info_format_prompt import FINAL_INFO_FORMAT_PROMPT
from agent.prompts.final_info.final_info_fix_prompt import FINAL_INFO_FIX_PROMPT
from agent.prompts.final_info.final_info_conversion_prompt import FINAL_INFO_CONVERSION_PROMPT

#set_debug(True)
#set_verbose(True)


# State extends the base search state for product completion
class FinalInfoState(BaseSearchState):
    """State for final product information completion"""
    product: dict  # ProductSimple with basic info (name, criteria, USP, use_case)
    product_output_string: str
    product_output_formatted: ProductFull
    search_limits: SearchLimitsConfig
    
    # BaseSearchState provides:
    # ai_queries: Annotated[List[AIMessage], add_messages]
    # tool_saved_info: Annotated[List[str], add_messages]
    # tool_last_output: List[AIMessage]
    # final_output: str


# Dynamic tool orchestrator for final product info
tools_orchestrator = DynamicTavilyToolOrchestrator(
    component_name=ComponentNames.FINAL_PRODUCT_INFO,
    input_field="ai_queries", 
    output_field="tool_last_output"
)


def create_final_info_config() -> SearchConfig:
    """Configuration for final product information completion"""
    
    return SearchConfig(
        analyze_prompt=FINAL_INFO_ANALYZE_PROMPT,
        search_prompt=FINAL_INFO_SEARCH_PROMPT,
        format_prompt=FINAL_INFO_FORMAT_PROMPT,
        state_field_mapping={
            "product": "product"
        },
        
        component_name=ComponentNames.FINAL_PRODUCT_INFO
    )


def chatbot_research_with_pattern(state: FinalInfoState):
    """
    Product information completion using the flexible search pattern.
    """
    
    # Create config with the final info completion prompts
    config = create_final_info_config()
    search_limits = state.get("search_limits")
    
    # Execute the 3-step pattern
    return execute_search_pattern_flexible(
        state=state,
        llm=get_llm("search_pattern"),
        llm_with_tools=tools_orchestrator.bind_tools_to_llm(get_llm("pattern_tool_calls"), search_limits),
        config=config
    )


def route_tools(state: FinalInfoState):
    """Simple routing logic"""
    return tools_orchestrator.router("tools")(state)


def validate_and_fix_json(state: FinalInfoState):
    """
    Validate if final_output is valid JSON, if not use LLM to fix it without schemas.
    """
    final_output = state.get("final_output", "")
    
    if not final_output:
        return {"product_output_string": ""}
    
    # Try to parse as JSON first
    try:
        json.loads(final_output)
        return {"product_output_string": final_output}
    except json.JSONDecodeError:
        # If invalid JSON, use LLM to fix it
        fix_prompt = FINAL_INFO_FIX_PROMPT

        try:
            formatted_prompt = fix_prompt.format(final_output=final_output)
            fixed_json = get_llm("json_fixing").invoke(formatted_prompt).content
            
            # Validate the fixed JSON
            json.loads(fixed_json)
            return {"product_output_string": fixed_json}
            
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error fixing JSON: {e}")
            return {"product_output_string": final_output}


def convert_to_product_full(state: FinalInfoState):
    """
    Convert the final_output string to a proper ProductFull object using LLM structured output.
    """
    final_output = state.get("final_output", "")
    
    if not final_output:
        return {"product_output_formatted": None}
    
    llm_structured = get_llm("final_product_info").with_structured_output(ProductFull)

    conversion_prompt = FINAL_INFO_CONVERSION_PROMPT

    try:
        formatted_prompt = conversion_prompt.format(final_output=final_output)
        product_full = llm_structured.invoke(formatted_prompt)
        return {
            "product_output_formatted": product_full,
            "product_output_string": final_output
        }
    except Exception as e:
        print(f"Error converting to ProductFull: {e}")
        return {
            "product_output_formatted": None,
            "product_output_string": final_output
        }


def print_node(state: FinalInfoState):
    product_formatted = state.get("product_output_formatted", None)
    if product_formatted:
        product_name = getattr(product_formatted, 'name', None) or product_formatted.get('name', 'Unknown')
        print(f"✅ ProductFull created: {product_name}")
    else:
        print("❌ ProductFull conversion failed")
    return state


# Graph construction using the pattern
# Tool node function that creates tools dynamically
def tool_node_final_info(state: FinalInfoState):
    """Tool node that creates tools dynamically based on search_limits from state"""
    search_limits = state.get("search_limits")
    return tools_orchestrator.tool_node(search_limits)(state)

def create_final_info_graph():
    graph_builder = StateGraph(FinalInfoState)

    graph_builder.add_node("tool_node_final_info", tool_node_final_info)
    graph_builder.add_node("final_info_chatbot", chatbot_research_with_pattern)
    graph_builder.add_node("format_final_info", validate_and_fix_json)


    graph_builder.add_edge(START, "final_info_chatbot")

    graph_builder.add_conditional_edges(
        "final_info_chatbot",
        route_tools,
        {"tools": "tool_node_final_info", END: "format_final_info"},
    )
    graph_builder.add_edge("tool_node_final_info", "final_info_chatbot")
    graph_builder.add_edge("format_final_info", END)

    return graph_builder.compile()


final_info_graph = create_final_info_graph()


if __name__ == "__main__":
    """
    Test the final info completion agent
    """
    
    print("🏷️ Testing Final Info Completion Agent")
    print("=" * 60)
    
    for event in final_info_graph.stream({
        "product": {
            "id": "fitbit-charge-6",
            "name": "Fitbit Charge 6",
            "criteria": {
                "price": "$160",
                "accuracy_of_total_sleep_time": "Good (within 10-15 min bias vs PSG)",
                "accuracy_of_deep_sleep_stage": "Fair (struggles with short sleep cycles)",
                "IOS_app_insights_and_interpretability": "Excellent (detailed graphs, trends, coaching)"
            },
            "USP": "GPS, Google, ECG",
            "use_case": "Serious fitness tracking",
            "other_info": "40+ modes, 7-day battery, $160"
        }
    }):
        print("Event", event.keys())
        
        if "chatbot_research" in event and "final_output" in event["chatbot_research"]:
            final_output = event["chatbot_research"]["final_output"]
            print("✅ Final Product Info:")
            print("-" * 40)
            print(final_output[:500] + "..." if len(final_output) > 500 else final_output)