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
import time
import logging
from pydantic import BaseModel, Field
from agent.configuration.search_limits import ComponentNames


# Base state that all search subgraphs will extend
class BaseSearchState(TypedDict):
    """Base state for all search patterns - your exact structure"""
    ai_queries: Annotated[List[AIMessage], add_messages]
    tool_saved_info: Annotated[List[str], add_messages]
    tool_last_output: List[AIMessage]
    final_output: str
    last_tool_call_count: int  # Track how many tool calls were made in the last step


class SearchConfig(BaseModel):
    """Configuration for the search pattern"""
    analyze_prompt: str = Field(description="Step 1: Analyze last tool call")
    search_prompt: str = Field(description="Step 2: Generate new search or done")
    format_prompt: str = Field(description="Step 3: Format final output")
    state_field_mapping: Dict[str, str] = Field(description="Map template variables to state fields")
    component_name: str = Field(description="Component name for search limits (e.g. 'product_research')")
    
    def get_max_searches(self, search_limits) -> int:
        """Get max searches from search_limits configuration"""
        component_limits = {
            "product_exploration": search_limits.product_exploration_max_searches,
            "product_research": search_limits.product_research_max_searches, 
            "final_product_info": search_limits.final_product_info_max_searches,
        }
        return component_limits.get(self.component_name, 3)


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


def retry_llm_tool_call(llm_with_tools, formatted_prompt: str, max_retries: int = 3):
    """
    Retry wrapper for LLM tool calls that handles validation errors.
    
    Args:
        llm_with_tools: The LLM instance bound to tools
        formatted_prompt: The formatted prompt to send
        max_retries: Maximum number of retry attempts
        
    Returns:
        The LLM response or None if all retries fail
    """
    logger = logging.getLogger(__name__)
    
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Attempting tool call (attempt {attempt + 1}/{max_retries + 1})")
            result = llm_with_tools.invoke(formatted_prompt)
            logger.info("Tool call succeeded")
            return result
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check if it's a tool validation error
            is_validation_error = any(keyword in error_msg for keyword in [
                'tool call validation failed',
                'parameters for tool',
                'did not match schema',
                'expected boolean, but got string',
                'badrequest'
            ])
            
            if is_validation_error and attempt < max_retries:
                logger.warning(f"Tool validation failed (attempt {attempt + 1}): {str(e)}")
                
                # Create a simpler prompt for retry
                if attempt == 0:
                    # First retry: Add explicit instructions about parameter types
                    retry_prompt = formatted_prompt + """\n\nIMPORTANT: When calling tools:
- Use boolean values (true/false), NOT strings ("true"/"false")
- Only use valid tool parameters
- For TavilySearch: valid boolean params are include_answer, include_raw_content, include_images, include_image_descriptions
- Example: {"query": "search term", "include_images": true}"""
                    
                elif attempt == 1:
                    # Second retry: Use basic search only
                    retry_prompt = f"""Based on this context, generate a simple web search query using only the 'query' parameter.
                    
Context: {formatted_prompt[:1000]}

Generate a Tavily search tool call with ONLY the query parameter. Example:
{{"query": "your search term here"}}

Do not use any other parameters like include_images, search_depth, etc."""
                
                else:
                    # Final retry: Most basic possible search
                    retry_prompt = "Generate a simple web search about the topic using only: {\"query\": \"search term\"}"
                
                formatted_prompt = retry_prompt
                
                # Exponential backoff
                if attempt > 0:
                    sleep_time = 2 ** (attempt - 1)
                    logger.info(f"Waiting {sleep_time}s before retry...")
                    time.sleep(sleep_time)
                    
            else:
                # Either not a validation error, or we've exhausted retries
                if attempt >= max_retries:
                    logger.error(f"All retry attempts failed. Final error: {str(e)}")
                    return None
                else:
                    # Non-validation error - don't retry
                    logger.error(f"Non-validation error, not retrying: {str(e)}")
                    raise e
    
    return None


def step1_analyze_last_tool_call(state: Dict[str, Any], 
                                llm,
                                config: SearchConfig) -> List[str]:
    """
    Step 1: Look at last tool calls - handles multiple parallel tool call outputs using actual count
    """
    
    tool_last_output_list = state.get("tool_last_output", [])
    ai_queries = state.get("ai_queries", [])
    last_tool_call_count = state.get("last_tool_call_count", 1)  # Default to 1 if not set
    
    if not tool_last_output_list:
        print("no last tool call outputs, skipping analysis")
        return []
        
    # Get the exact number of tool call outputs from the last step
    recent_outputs = tool_last_output_list[-last_tool_call_count:] if len(tool_last_output_list) >= last_tool_call_count else tool_last_output_list
    
    print(f"analyzing {len(recent_outputs)} recent tool call outputs from last step")
    
    # Build context from multiple tool call results
    tool_arguments = []
    tool_outputs = []
    
    # Get the most recent AI query(s) that generated these tool calls
    if ai_queries:
        recent_ai_query = ai_queries[-1]
        if hasattr(recent_ai_query, 'tool_calls') and recent_ai_query.tool_calls:
            # Handle the actual number of tool calls that were made (not assume concurrent_count)
            actual_tool_calls = recent_ai_query.tool_calls[:last_tool_call_count]
            for i, tool_call in enumerate(actual_tool_calls):
                query = tool_call.get("args", {}).get("query", "")
                tool_arguments.append(f"Search {i+1}: {query}")
        else:
            tool_arguments.append("No tool call arguments found")
    
    # Process multiple outputs
    for i, output in enumerate(recent_outputs):
        content = output.content if hasattr(output, 'content') else str(output)
        tool_outputs.append(f"Result {i+1}: {content}")
    
    # Your exact tool call context but for multiple calls
    tool_context = {
        "last_tool_call_arguments": json.dumps(tool_arguments),
        "last_tool_call_output": " | ".join(tool_outputs),
    }
    
    # Apply configurable state mapping
    format_context = apply_state_mapping(state, config.state_field_mapping, tool_context)
    
    # Your exact prompt formatting and LLM call
    formatted_prompt = config.analyze_prompt.format(**format_context)
    result = llm.invoke(formatted_prompt)
    return [result.content]

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

    # Get search_limits from state
    search_limits = state.get("search_limits")
    if not search_limits:
        print(f"Warning: No search_limits found in state for {config.component_name}")
        return None, serializable_tool_info
    
    # Check max searches limit using search_limits from state
    max_limit = config.get_max_searches(search_limits)
    if len(ai_queries) >= max_limit:
        print(f"Skipping search query generation, reached maximum number of queries ({max_limit}) for {config.component_name}")
        return None, serializable_tool_info
    
    # Get concurrent search configuration from search_limits
    concurrent_configs = {
        ComponentNames.PRODUCT_EXPLORATION: search_limits.product_exploration_concurrent_searches,
        ComponentNames.PRODUCT_RESEARCH: search_limits.product_research_concurrent_searches,
        ComponentNames.FINAL_PRODUCT_INFO: search_limits.final_product_info_concurrent_searches,
    }
    concurrent_count = concurrent_configs.get(config.component_name, 3)  # Default fallback
    
    # Generate search limit text dynamically
    if len(ai_queries) > 0:
        search_limit_text = f"- Max {max_limit} searches for this task. You already used {len(ai_queries)} searches."
    else:
        search_limit_text = f"- Use a MAX of {max_limit} searches for this task, ideally fewer."
    
    # Your exact search context with dynamic search limit text and concurrent search info
    search_context = {
        "tool_saved_info": json.dumps(serializable_tool_info + result_tool_call_analysis),
        "ai_queries": json.dumps([msg.tool_calls[0].get("args", {}).get("query", "") for msg in ai_queries]),
        "len_ai_queries": len(ai_queries),
        "search_limit_text": search_limit_text,
        "concurrent_searches": concurrent_count,
    }
    
    # Apply configurable state mapping
    format_context = apply_state_mapping(state, config.state_field_mapping, search_context)
    
    # Your exact prompt formatting and LLM call with retry logic
    formatted_prompt = config.search_prompt.format(**format_context)
    result_search_query = retry_llm_tool_call(llm_with_tools, formatted_prompt)
    
    # Handle case where all retries failed
    if result_search_query is None:
        logger = logging.getLogger(__name__)
        logger.warning("All retry attempts failed for tool call, returning None to continue execution")
        return None, serializable_tool_info
    
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
        actual_tool_call_count = len(result_search_query.tool_calls)
        print(f"we have {actual_tool_call_count} search queries to run in parallel")
        return {
            "ai_queries": [result_search_query],
            "tool_saved_info": result_tool_call_analysis,
            "last_tool_call_count": actual_tool_call_count
        }
    else:
        final_output = step3_format_final_output(
            state, result_tool_call_analysis, serializable_tool_info, llm, config
        )
        
        return {
            "final_output": final_output,
            "ai_queries": [AIMessage(content="no more searches")],
            "last_tool_call_count": 0  # No tool calls made in this step
        }


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
        
        component_name=ComponentNames.PRODUCT_RESEARCH  # Use product_research limits for this example
    )