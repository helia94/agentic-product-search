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
from agent.basic_tools import llm_gemini
from agent.tool_orchestrator import SimpleToolOrchestrator
from agent.search_pattern import BaseSearchState, execute_search_pattern_flexible, SearchConfig
from agent.search_limits import (
    get_search_limit, 
    generate_search_prompt_text, 
    is_search_limit_reached,
    get_tavily_config,
    ComponentNames
)
from langchain_tavily import TavilySearch

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


# Create Tavily instance with centralized configuration
def create_final_info_tavily():
    """Create Tavily instance for final product info with centralized config"""
    tavily_config = get_tavily_config(ComponentNames.FINAL_PRODUCT_INFO)
    return TavilySearch(
        max_results=tavily_config.max_results,
        include_answer=tavily_config.include_answer,
        search_depth=tavily_config.search_depth
    )

# Tool setup with final-info-specific Tavily
final_info_tavily = create_final_info_tavily()
tools_setup = SimpleToolOrchestrator([final_info_tavily])


def create_final_info_config() -> SearchConfig:
    """Configuration for final product information completion"""
    
    return SearchConfig(
        analyze_prompt="""
        <SYSTEM>
        You are a product information completion agent. Analyze the last search result to extract missing ProductFull fields.
        </SYSTEM>

        <INSTRUCTIONS>
        Extract key product information from the search results:
        "USP": "One-sentence unique selling proposition.",
        "use_case": "Primary context or user segment.",
        "country": "Design and manufacturing origin (e.g., 'Designed in FI, made in CN').",
        "year": "Release year (YYYY).",
        "review_summary": "Keyword-style user review highlights; no fluff.",
        "rating": "Score plus source (e.g., '4.5/5 on Amazon').",
        "reviews_count": "Exact review count; no ranges.",
        "image_url": "1–3 image URLs, prefer official/reputable.",
        "product_url": "Retailer link for the specified country; note if unavailable."
         any other nuance interesting info you found nothing generic

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
        For the given product, FILL all remaining fields. 
        Use the SEARCH TOOL if any field is missing.
        Return either:
        - a search tool call (with precise query string), OR
        - nothing if you have enough information.
        we need these fields in order of importance:
        "product_url": "Retailer link for the specified country; note if unavailable."
        "image_url": "1–3 image URLs, prefer official/reputable.",
        "review_summary": "Keyword-style user review highlights; no fluff.",
        "rating": "Score plus source (e.g., '4.5/5 on Amazon').",
        "reviews_count": "Exact review count; no ranges.",
        "USP": "One-sentence unique selling proposition.",
        "use_case": "Primary context or user segment.",
        "country": "Design and manufacturing origin (e.g., 'Designed in FI, made in CN').",
        "year": "Release year (YYYY).",
        </TASK>

        <CONSTRAINTS>
        {search_limit_text}
        - Be concise, avoid fluff. Use info-dense, direct language.
        - Review summaries = keyword-only, no generic opinions (e.g., say "short battery, clean app" not "great product").
        - Image URLs: 1–3, from official or reputable retailers.
        - Product URL must be live and specific to given country; if not available, include original URL + warning.
        - Stop and return empty if product model is unclear.
        - DO NOT search for information you already have in tool_saved_info or in product info input. check all we have first before writing queries.
        - DO NOT repeat queries in ai_queries.
        - New search query should be significantly different from previous ones.
        - Use function calling for the search
        - DO NOT use include_domains
        - DO NOT BUNDLE unrelated key words in search like "manufacture country, user ratings, review count, review summaries, official product images
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
        Create a fully completed product information json using all gathered information.
        YOU HAVE TO RETURN A VALID JSON.
        Put all the gathered information into the appropriate fields.
        DO NOT add any extra fluff or jargon this is not a report.
        It should make decision making easier and more informative. 
        This is for the buyer not for the brands.

        FILL all remaining json fields:
        "id": "Internal unique ID for tracking/retrieval. Inside product info.",
        "name": "Fully qualified product name incl. model/specs. Inside product info.",
        "criteria": "Dict of {{criterion: brief value/notes}}. Inside product info under evaluation.",
        "USP": "One-line unique advantage. Inside product info or tool_saved_info.",
        "use_case": "Primary intended user/usage. Inside product info or tool_saved_info.",
        "price": "Exact numeric price (no ranges). Inside product info.",
        "country": "Design and manufacture line (e.g., 'Designed in X, made in Y'). Inside tool_saved_info.",
        "year": "Release year (YYYY). Inside tool_saved_info.",
        "review_summary": "Comma-separated review keywords (no fluff). Inside tool_saved_info or product.",
        "rating": "Score + source (e.g., '4.6/5 on Amazon').  Inside tool_saved_info.",
        "reviews_count": "Exact review count at the source.  Inside tool_saved_info.",
        "image_url": "1–3 image URLs (official/reputable).  Inside tool_saved_info.",
        "product_url": "Retailer URL for target country; otherwise original with warning. Inside tool_saved_info."
        
        If any field cannot be determined from the research, use "unknown".
        Return valid JSON format for ProductFull.
        </INSTRUCTIONS>
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

        <INPUT>
        product: {product}
        tool_saved_info: {tool_saved_info}
        </INPUT>
        """,
        
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
        fix_prompt = """
        The following text should be valid JSON but it's malformed. 
        Fix it to be valid JSON without changing the content meaning.
        Return only the fixed JSON, no explanations or markdown.
        
        Text to fix:
        {final_output}
        """
        
        try:
            formatted_prompt = fix_prompt.format(final_output=final_output)
            fixed_json = llm_gemini.invoke(formatted_prompt).content
            
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

    graph_builder.add_node("tool_node_final_info", tool_node_research)
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