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
from agent.state_V2 import ProductFull
from agent.basic_tools import llm_gemini, tavily
from agent.tool_orchestrator import SimpleToolOrchestrator
from agent.search_pattern import BaseSearchState, execute_search_pattern_flexible, SearchConfig

#set_debug(True)
#set_verbose(True)


# State extends the base search state for product completion
class FinalInfoState(BaseSearchState):
    """State for final product information completion"""
    product: dict  # ProductSimple with basic info (name, criteria, USP, use_case)
    product_output_string: str
    product_output_formatted: ProductFull
    
    # BaseSearchState provides:
    # ai_queries: Annotated[List[AIMessage], add_messages]
    # tool_saved_info: Annotated[List[str], add_messages]
    # tool_last_output: List[AIMessage]
    # final_output: str


# Simple tool setup
tools_setup = SimpleToolOrchestrator([tavily])


def create_final_info_config() -> SearchConfig:
    """Configuration for final product information completion"""
    
    return SearchConfig(
        analyze_prompt="""
        <SYSTEM>
        You are a product information completion agent. Analyze the last search result to extract missing ProductFull fields.
        </SYSTEM>

        <INSTRUCTIONS>
        Extract key product information from the search results:
        - Release year, manufacture country
        - User ratings, review counts, review summaries
        - Product URLs, image URLs
        - Any other ProductFull fields that were missing
        
        Focus on factual data, avoid marketing fluff.
        Return insights as a list of strings.
        </INSTRUCTIONS>

        <INPUT>
        product: {product}
        last_tool_call_arguments: {last_tool_call_arguments}
        last_tool_call_output: {last_tool_call_output}
        </INPUT>
        """,
        
        search_prompt="""
        <SYSTEM_PROMPT>
        You are a product research agent.

        <TASK>
        For the given product, FILL all remaining fields in the `ProductFull` class.
        Use the SEARCH TOOL if any field is missing (except: `criteria`, `USP`, `use_case` — these are already provided).
        Return either:
        - a search tool call (with precise query string), OR
        - nothing if you have enough information.
        </TASK>

        <CONSTRAINTS>
        - Max 5 searches per product. Prefer getting everything in 1 or 2 searches. You already used {len_ai_queries} searches.
        - Be concise, avoid fluff. Use info-dense, direct language.
        - If a value is unknown or unverifiable, write `"unknown"` (never guess).
        - Review summaries = keyword-only, no generic opinions (e.g., say "short battery, clean app" not "great product").
        - Image URLs: 1–3, from official or reputable retailers.
        - Product URL must be live and specific to given country; if not available, include original URL + warning.
        - Stop and return empty if product model is unclear.
        - DO NOT search for information you already have in tool_saved_info or in product info input.
        - DO NOT repeat queries in ai_queries.
        - New search query should be significantly different from previous ones.
        - Use function calling for the search
        - DO NOT use include_domains
        - DO NOT bundle not related key words in search like manufacture country, user ratings, review count, review summaries, official product images
        - Either search for each missing field individually, or use general query like honest reviews of X
        - image_url is very important always include it
        </CONSTRAINTS>

        <INPUT FORMAT>
        Product:
        - name: str
        - criteria: Dict[str, str]
        - USP: str
        - use_case: str

        <OUTPUT FORMAT>
        Return one of:
        1. `search("your_query_here")`
        2. Nothing if you have sufficient information

        <EXAMPLES>

        # ✅ EXAMPLE 1 - First Search
        search("Withings Sleep Analyzer specifications")

        # ✅ EXAMPLE 2 - First Search
        search("Oura Ring Gen3 expert reviews and details")
        </EXAMPLES>
        </SYSTEM_PROMPT>

        <INPUT>
        product: {product}
        tool_saved_info: {tool_saved_info}
        ai_queries: {ai_queries}
        </INPUT>
        """,
        
        format_prompt="""
        <SYSTEM>
        You are a product information completion agent.
        </SYSTEM>

        <INSTRUCTIONS>
        Create a fully completed ProductFull dictionary using all gathered information.
        
        FILL all remaining fields in the `ProductFull` class:
        - id: Create from product name and year (e.g., "withings_sleep_analyzer_2020")
        - name: Full product name
        - criteria: Already provided
        - USP: Already provided  
        - use_case: Already provided
        - price: Numeric value
        - country: Design/manufacture origin
        - year: Release year
        - review_summary: Keyword-only, no generic opinions
        - rating: Format like "4.2/5 on Amazon"
        - reviews_count: String number
        - image_url: List of 1-3 URLs
        - product_url: Live, specific URL
        
        If any field cannot be determined from the research, use "unknown".
        Return valid JSON format for ProductFull.
        
        <EXAMPLES>
        
        # ✅ EXAMPLE OUTPUT
        {{
            "id": "withings_sleep_analyzer_2020",
            "name": "Withings Sleep Analyzer – Advanced Sleep Tracking Pad",
            "criteria": {{
                "price": "$129",
                "accuracy_of_total_sleep_time": "Acceptable (within ~20 min bias vs PSG in clinical studies)",
                "accuracy_of_sleep_stages": "Fair (good for light/deep, but struggles with REM detection)"
            }},
            "USP": "non-wearable apnea tracking",
            "use_case": "at-home sleep diagnostics",
            "price": 129.0,
            "country": "Designed in France, produced in China",
            "year": 2020,
            "review_summary": "non-intrusive, accurate apnea detection, app sync issues",
            "rating": "4.2/5 on Amazon",
            "reviews_count": "1563",
            "image_url": [
                "https://www.withings.com/us/en/sleep-analyzer/img1.jpg"
            ],
            "product_url": "https://www.withings.com/fr/en/sleep-analyzer"
        }}
        </EXAMPLES>
        </INSTRUCTIONS>

        <INPUT>
        product: {product}
        tool_saved_info: {tool_saved_info}
        </INPUT>
        """,
        
        state_field_mapping={
            "product": "product"
        },
        
        max_searches=5
    )


def chatbot_research_with_pattern(state: FinalInfoState):
    """
    Product information completion using the flexible search pattern.
    """
    
    # Create config with the final info completion prompts
    config = create_final_info_config()
    
    # Execute the 3-step pattern
    return execute_search_pattern_flexible(
        state=state,
        llm=llm_gemini,
        llm_with_tools=tools_setup.bind_tools_to_llm(llm_gemini),
        config=config
    )


def route_tools(state: FinalInfoState):
    """Simple routing logic"""
    return tools_setup.router("tools")(state)


def convert_to_product_full(state: FinalInfoState):
    """
    Convert the final_output string to a proper ProductFull object using LLM structured output.
    """
    final_output = state.get("final_output", "")
    
    if not final_output:
        return {"product_output_formatted": None}
    
    llm_structured = llm_gemini.with_structured_output(ProductFull)
    
    conversion_prompt = """
    Convert this product information into a properly structured ProductFull object.
    Ensure all fields are correctly typed and formatted.
    
    Product information to convert:
    {final_output}
    """
    
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
def create_final_info_graph():
    graph_builder = StateGraph(FinalInfoState)
    tool_node_research = tools_setup.tool_node()

    graph_builder.add_node("tool_node_research", tool_node_research)
    graph_builder.add_node("chatbot_research", chatbot_research_with_pattern)
    graph_builder.add_node("convert_to_product_full", convert_to_product_full)
    graph_builder.add_node("print_node", print_node)

    graph_builder.add_edge(START, "chatbot_research")

    graph_builder.add_conditional_edges(
        "chatbot_research",
        route_tools,
        {"tools": "tool_node_research", END: "convert_to_product_full"},
    )
    graph_builder.add_edge("tool_node_research", "chatbot_research")
    graph_builder.add_edge("convert_to_product_full", "print_node")
    graph_builder.add_edge("print_node", END)

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