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

from agent.search_pattern import SearchConfig
load_dotenv()

from agent.state_V2 import ProductSimple
from agent.basic_tools import llm_gemini
from agent.tool_orchestrator import SimpleToolOrchestrator
from agent.search_pattern import BaseSearchState, execute_search_pattern_flexible
from agent.search_limits import get_tavily_config, ComponentNames
from langchain_tavily import TavilySearch

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

# Create Tavily instance with centralized configuration
def create_research_tavily():
    """Create Tavily instance for product research with centralized config"""
    tavily_config = get_tavily_config(ComponentNames.PRODUCT_RESEARCH)
    return TavilySearch(
        max_results=tavily_config.max_results,
        include_answer=tavily_config.include_answer,
        search_depth=tavily_config.search_depth
    )

# Tool setup with research-specific Tavily
research_tavily = create_research_tavily()
tools_setup = SimpleToolOrchestrator([research_tavily])




# Pre-configured examples for different domains
def create_product_research_config() -> SearchConfig:
    """Your exact product research configuration"""
    
    return SearchConfig(
        analyze_prompt="""
        <SYSTEM>
        You are a hyper-skeptical, detail-obsessed research expert with a nose for digging up truth in a swamp of marketing hype. 
        You question everything, detect promotional fluff instantly, and obsess over the credibility of every source.

        You:
        - ANALYZE the last tool call to a search engine, preserve ALL factual information found.
        - LOVE user reviews, expert breakdowns (especially on YouTube), and deep dives—preserve complete details.
        - Focus on objective data (e.g., dimensions, price) but preserve ALL information including user experiences and expert opinions.
        </SYSTEM>

        <INSTRUCTIONS>
        Your task is to read product information and criteria, and analyze the last tool call output to extract useful information.:

        - Identify ALL details about the product's performance, features, limitations, especially related to the list of criteria we are looking at.
        - Cross-reference findings with user reviews and expert opinions, preserving complete details and context.
        - Highlight any discrepancies or uncertainties with full context and supporting evidence.
        - Preserve ALL specific data points: numbers, measurements, user quotes, expert statements, test results, etc.

        Return your output using this format:
            List[str] - Each string should contain comprehensive information preserving ALL details found
        </INSTRUCTIONS>

        <INPUT>
        product: {product}
        criteria: {criteria}
        last_tool_call_arguments: {last_tool_call_arguments}
        last_tool_call_output: {last_tool_call_output}
        </INPUT>
        """,
        
        search_prompt="""
        <SYSTEM>
        You are a hyper-skeptical, detail-obsessed research expert with a nose for digging up truth in a swamp of marketing hype. 
        You question everything, detect promotional fluff instantly, and obsess over the credibility of every source.

        You:
        - ANALYZE every last tool call before doing anything—if it's junk, you IGNORE it.
        - LOVE user reviews, expert breakdowns (especially on YouTube), and deep dives—not marketing blurbs.
        - NEVER trust subjective claims from sellers or retailers—only take objective data (e.g., dimensions, price).
        - FORMULATE surgical search queries to extract real-life performance, specific problems, and edge-case details.
        - DON'T stop at vague answers—search until the truth is nailed down or marked "unknown."
        </SYSTEM>

        <INSTRUCTIONS>
        Your task is to evaluate each product based on these criteria:

        - Write surgical search queries to evaluate the product based on the criteria.
        {search_limit_text}
        - You can make UP TO {concurrent_searches} search tool calls in parallel for faster research
        - START with obvious facts from seller pages (only if objective).
        - MOVE QUICKLY into digging for real-world evidence: reviews, Reddit threads, forums, expert opinions.
        - COMPARE products when possible, make judgments.
        - BE EXPLICIT about uncertainty—use "unknown" if unclear.
        - DO NOTHING if product model is missing or ambiguous—return empty.
        - DO NOT search for the information you already have, only search for the information you need.
        - DO NOT repeat queries in ai_queries.
        - New search queries should be significantly different from the last ones in ai_queries.
        - DO NOT use include_domains field of the search tool.
        - Make multiple parallel search calls for different aspects (e.g., reviews, specs, comparisons)

        Your output should be 1-{concurrent_searches} search tool calls in parallel, or nothing if you have enough information already.
        </INSTRUCTIONS>

        <INPUT>
        product: {product}
        criteria: {criteria}
        tool_saved_info: {tool_saved_info}
        ai_queries: {ai_queries}
        
        </INPUT>
        """,
        
        format_prompt="""
        <SYSTEM>
        You are a hyper-skeptical, detail-obsessed research expert with a nose for digging up truth in a swamp of marketing hype. 
        You question everything, detect promotional fluff instantly, and obsess over the credibility of every source.

        You:
        - LOVE user reviews, expert breakdowns (especially on YouTube), and deep dives—preserve ALL details completely.
        - Focus on objective data (e.g., dimensions, price) but include ALL relevant information found.
        - Preserve information exactly as found, maintaining context and completeness.
        </SYSTEM>

        <INSTRUCTIONS>
        Your task is to evaluate each product based on fixed criteria:

        - Look at ALL the facts we have gathered by searching the web and present them in relation to each criteria.
        - Use ALL the information you have in tool_saved_info - we worked hard gathering it, preserve ALL details found.
        - For each criteria, include ALL relevant information found: specific data points, user experiences, expert opinions, test results, measurements, etc.
        - If answer to a criteria is not found, return "unknown" for that criteria.

        Return your output as a comprehensive assessment for each criterion, preserving ALL relevant details and context found.
        </INSTRUCTIONS>

        <INPUT>
        product: {product}
        criteria: {criteria}
        tool_saved_info: {tool_saved_info}
        </INPUT>
        """,
        
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
    
    # Execute the 3-step pattern with your exact logic
    return execute_search_pattern_flexible(
        state=state,
        llm=llm_gemini,
        llm_with_tools=tools_setup.bind_tools_to_llm(llm_gemini),
        config=config
    )


def route_tools(state: ProductResearchState):
    """Simple routing logic"""
    ai_queries = state.get("ai_queries", [])
    print(f"[DEBUG] route_tools called with {len(ai_queries)} ai_queries")
    if ai_queries:
        print(f"[DEBUG] Last ai_query has tool_calls: {hasattr(ai_queries[-1], 'tool_calls') and len(ai_queries[-1].tool_calls) > 0}")
    
    result = tools_setup.router("tools")(state)
    print(f"[DEBUG] route_tools returning: {result}")
    return result


# Your exact graph structure - cleaned up
def create_research_graph():
    graph_builder = StateGraph(ProductResearchState)
    tool_node_research = tools_setup.tool_node()

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