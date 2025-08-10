"""
Flexible Search Pattern - Configurable State Fields

This makes the state field mapping completely configurable so each subgraph
can specify which state fields map to which prompt template variables.
"""

from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
from langchain_core.messages import AIMessage
from langgraph.graph.message import add_messages
from typing import Annotated
import json
from pydantic import BaseModel, Field


# Base state that all search subgraphs will extend
class BaseSearchState(TypedDict):
    """Base state for all search patterns - your exact structure"""
    ai_queries: Annotated[List[AIMessage], add_messages]
    tool_saved_info: Annotated[List[str], add_messages]
    tool_last_output: List[AIMessage]
    final_output: str


class SearchConfig(BaseModel):
    """Configuration for the search pattern"""
    analyze_prompt: str = Field(description="Step 1: Analyze last tool call")
    search_prompt: str = Field(description="Step 2: Generate new search or done")
    format_prompt: str = Field(description="Step 3: Format final output")
    state_field_mapping: Dict[str, str] = Field(description="Map template variables to state fields")
    max_searches: int = Field(default=3, description="Maximum number of searches")


class AnalysisResult(BaseModel):
    """Your exact tool call analysis structure"""
    insights: List[str] = Field(description="List of key insights extracted from the tool call")


def apply_state_mapping(state: Dict[str, Any], 
                       state_field_mapping: Dict[str, str],
                       additional_context: Dict[str, Any] = None) -> Dict[str, str]:
    """
    Apply configurable state field mapping to create prompt context.
    
    Args:
        state: The graph state
        state_field_mapping: {"template_var": "state_field"} mapping
        additional_context: Extra context variables
    
    Returns:
        Dictionary ready for prompt formatting
    """
    
    format_context = {}
    
    # Apply the configurable mapping
    for template_key, state_key in state_field_mapping.items():
        value = state.get(state_key, "")
        
        # Handle list fields (like criteria) - join with comma
        if isinstance(value, list):
            format_context[template_key] = " ,".join(str(v) for v in value)
        else:
            format_context[template_key] = str(value)
    
    # Add any additional context
    if additional_context:
        format_context.update(additional_context)
    
    return format_context


def step1_analyze_last_tool_call(state: Dict[str, Any], 
                                llm,
                                config: SearchConfig) -> List[str]:
    """
    Step 1: Look at last tool call - your exact logic with configurable state mapping
    """
    
    tool_last_output_list = state.get("tool_last_output", [])
    last_tool_call_output = tool_last_output_list[-1] if tool_last_output_list else None
    ai_queries = state.get("ai_queries", [])
    
    if not last_tool_call_output:
        print("no last tool call output, skipping analysis")
        return []
        
    print("analyzing last tool call output")
    
    # Your exact tool call context
    tool_context = {
        "last_tool_call_arguments": json.dumps(ai_queries[-1].tool_calls[0].get("args", {}).get("query", "")) if ai_queries else "{}",
        "last_tool_call_output": last_tool_call_output.content if hasattr(last_tool_call_output, 'content') else str(last_tool_call_output),
    }
    
    # Apply configurable state mapping
    format_context = apply_state_mapping(state, config.state_field_mapping, tool_context)
    
    # Your exact prompt formatting and LLM call
    formatted_prompt = config.analyze_prompt.format(**format_context)
    result = llm.with_structured_output(AnalysisResult).invoke(formatted_prompt)
    return result.insights


def step2_generate_search_or_done(state: Dict[str, Any],
                                 result_tool_call_analysis: List[str],
                                 llm_with_tools,
                                 config: SearchConfig):
    """
    Step 2: Send new query or done - your exact logic with configurable state mapping
    """
    
    tool_saved_info = state.get("tool_saved_info", [])
    ai_queries = state.get("ai_queries", [])
    
    # Your exact serialization logic
    serializable_tool_info = []
    for item in tool_saved_info:
        if hasattr(item, 'content'):
            serializable_tool_info.append(item.content)
        else:
            serializable_tool_info.append(str(item))

    # Check max searches limit
    if len(ai_queries) >= config.max_searches:
        print(f"Skipping search query generation, reached maximum number of queries ({config.max_searches})")
        return None, serializable_tool_info
    
    # Your exact search context
    search_context = {
        "tool_saved_info": json.dumps(serializable_tool_info + result_tool_call_analysis),
        "ai_queries": json.dumps([msg.tool_calls[0].get("args", {}).get("query", "") for msg in ai_queries]),
        "len_ai_queries": len(ai_queries),
    }
    
    # Apply configurable state mapping
    format_context = apply_state_mapping(state, config.state_field_mapping, search_context)
    
    # Your exact prompt formatting and LLM call
    formatted_prompt = config.search_prompt.format(**format_context)
    result_search_query = llm_with_tools.invoke(formatted_prompt)
    
    return result_search_query, serializable_tool_info


def step3_format_final_output(state: Dict[str, Any],
                             result_tool_call_analysis: List[str],
                             serializable_tool_info: List[str],
                             llm,
                             config: SearchConfig) -> str:
    """
    Step 3: Write final format - your exact logic with configurable state mapping
    """
    
    print("no search query to run, formatting final output")
    
    # Your exact final context
    final_context = {
        "tool_saved_info": json.dumps(serializable_tool_info + result_tool_call_analysis)
    }
    
    # Apply configurable state mapping
    format_context = apply_state_mapping(state, config.state_field_mapping, final_context)
    
    # Your exact prompt formatting and LLM call
    formatted_prompt = config.format_prompt.format(**format_context)
    final_result = llm.invoke(formatted_prompt)
    return final_result.content


def execute_search_pattern_flexible(state: Dict[str, Any],
                                   llm,
                                   llm_with_tools,
                                   config: SearchConfig) -> Dict[str, Any]:
    """
    Execute the complete 3-step search pattern with configurable state mapping.
    
    This is your exact chatbot_research logic made generic and flexible.
    """
    
    # Step 1: Analyze last tool call
    result_tool_call_analysis = step1_analyze_last_tool_call(state, llm, config)
    
    # Step 2: Generate search query or decide to finish
    result_search_query, serializable_tool_info = step2_generate_search_or_done(
        state, result_tool_call_analysis, llm_with_tools, config
    )
    
    # Step 3: Return search action or final output
    if result_search_query and result_search_query.tool_calls:
        print("we have a search query to run")
        return {
            "ai_queries": [result_search_query],
            "tool_saved_info": result_tool_call_analysis
        }
    else:
        final_output = step3_format_final_output(
            state, result_tool_call_analysis, serializable_tool_info, llm, config
        )
        
        return {
            "final_output": final_output,
            "ai_queries": [AIMessage(content="no more searches")],
        }


# Pre-configured examples for different domains
def create_product_research_config() -> SearchConfig:
    """Your exact product research configuration"""
    
    return SearchConfig(
        analyze_prompt="""
        <SYSTEM>
        You are a hyper-skeptical, detail-obsessed research expert with a nose for digging up truth in a swamp of marketing hype. 
        You question everything, detect promotional fluff instantly, and obsess over the credibility of every source.

        You:
        - ANALYZE the last tool call to a search engine, take useful info and ignore the junk.
        - LOVE user reviews, expert breakdowns (especially on YouTube), and deep dives—not marketing blurbs.
        - NEVER trust subjective claims from sellers or retailers—only take objective data (e.g., dimensions, price).
        </SYSTEM>

        <INSTRUCTIONS>
        Your task is to read product information and criteria, and analyze the last tool call output to extract useful information.:

        - Identify key details about the product's performance, features, limitations, especially related to the list of criteria we are looking at.
        - Cross-reference findings with user reviews and expert opinions to validate claims.
        - Highlight any discrepancies or uncertainties in the information gathered.
        - WRITE like you're texting a sharp best friend: quick, blunt, clear.

        Return your output using this format:
            List[str]
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
        - Use a MAX of 3 searches per product, ideally fewer. You already used {len_ai_queries} searches.
        - START with obvious facts from seller pages (only if objective).
        - MOVE QUICKLY into digging for real-world evidence: reviews, Reddit threads, forums, expert opinions.
        - COMPARE products when possible, make judgments.
        - BE EXPLICIT about uncertainty—use "unknown" if unclear.
        - DO NOTHING if product model is missing or ambiguous—return empty.
        - DO NOT search for the information you already have, only search for the information you need.
        - DO NOT repeat queries in ai_queries.
        - New search query should be significantly different from the last ones in ai_queries.
        - DO NOT use include_domains field of the search tool.

        your output should be a searching tool call or nothing if you have enough information already.
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
        - LOVE user reviews, expert breakdowns (especially on YouTube), and deep dives—not marketing blurbs.
        - NEVER trust subjective claims from sellers or retailers—only take objective data (e.g., dimensions, price).
        - WRITE like you're texting a sharp best friend: quick, blunt, clear.
        </SYSTEM>

        <INSTRUCTIONS>
        Your task is to evaluate each product based on fixed criteria:

        - Look at all the facts we have gathered by searching the web and formulate them to criteria assessments.
        - Try to use all the information you have in tool_saved_info we tried hard in gathering it, try to fit into the criteria, but do not invent anything.
        - If answer to a criteria is not found, return "unknown" for that criteria.

        Return your output as a clear assessment for each criterion.
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
        
        max_searches=3
    )


def create_market_research_config() -> SearchConfig:
    """Example configuration for market research subgraph"""
    
    return SearchConfig(
        analyze_prompt="""
        <SYSTEM>You are a market research analyst studying: {market_segment}</SYSTEM>
        <INSTRUCTIONS>Extract market data, trends, and competitive insights</INSTRUCTIONS>
        <INPUT>
        market_segment: {market_segment}
        research_goals: {research_goals}
        last_tool_call_output: {last_tool_call_output}
        </INPUT>
        """,
        
        search_prompt="""
        <SYSTEM>You are a market researcher.</SYSTEM>
        <INSTRUCTIONS>Find market data for {market_segment} focused on: {research_goals}</INSTRUCTIONS>
        <INPUT>
        market_segment: {market_segment}
        research_goals: {research_goals}
        tool_saved_info: {tool_saved_info}
        ai_queries: {ai_queries}
        </INPUT>
        """,
        
        format_prompt="""
        <SYSTEM>You are a market analyst.</SYSTEM>
        <INSTRUCTIONS>Create market analysis report for: {market_segment}</INSTRUCTIONS>
        <INPUT>
        market_segment: {market_segment}
        research_goals: {research_goals}
        tool_saved_info: {tool_saved_info}
        </INPUT>
        """,
        
        state_field_mapping={
            "market_segment": "market_segment",
            "research_goals": "research_goals"
        },
        
        max_searches=4
    )