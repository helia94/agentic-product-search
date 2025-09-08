"""
Pre-configured Tavily Tools for Different Configurations

This module creates multiple TavilySearch tools with different configurations
since parameters like max_results and include_answer must be set at tool creation time.
search_depth can be set at invocation time.
"""

from langchain_tavily import TavilySearch
from typing import Dict, List, Any

# Create Tavily tools with different max_results and include_answer combinations
# Key format: (max_results, include_answer)
TAVILY_TOOLS = {
    (2, False): TavilySearch(max_results=2, include_answer=False),
    (2, True): TavilySearch(max_results=2, include_answer=True),
    (5, False): TavilySearch(max_results=5, include_answer=False),
    (5, True): TavilySearch(max_results=5, include_answer=True),
    (10, False): TavilySearch(max_results=10, include_answer=False),
    (10, True): TavilySearch(max_results=10, include_answer=True),
    (20, False): TavilySearch(max_results=20, include_answer=False),
    (20, True): TavilySearch(max_results=20, include_answer=True),
}

def get_tavily_tool(max_results: int, include_answer: bool) -> TavilySearch:
    """Get the appropriate TavilySearch tool for the given configuration"""
    # Find the closest matching max_results, defaulting to the next higher value
    available_limits = sorted(set(key[0] for key in TAVILY_TOOLS.keys()))
    
    # Find exact match or next higher value for max_results
    target_max_results = None
    for limit in available_limits:
        if limit >= max_results:
            target_max_results = limit
            break
    
    # If max_results is higher than all available, use the highest
    if target_max_results is None:
        target_max_results = available_limits[-1]
    
    # Get the tool with the matching configuration
    tool_key = (target_max_results, include_answer)
    if tool_key in TAVILY_TOOLS:
        return TAVILY_TOOLS[tool_key]
    
    # Fallback to default configuration
    return TAVILY_TOOLS[(5, False)]

def create_component_tavily_tool(search_limits, component_name: str) -> TavilySearch:
    """Create appropriate Tavily tool for a specific component based on search_limits"""
    tavily_configs = {
        "product_exploration": search_limits.product_exploration_tavily,
        "product_research": search_limits.product_research_tavily,
        "final_product_info": search_limits.final_product_info_tavily,
    }
    
    config = tavily_configs.get(component_name)
    if not config:
        # Default fallback
        return get_tavily_tool(5, False)
    
    return get_tavily_tool(config.max_results, config.include_answer)

def get_search_depth_for_component(search_limits, component_name: str) -> str:
    """Get search_depth for a component - this can be used at invocation time"""
    tavily_configs = {
        "product_exploration": search_limits.product_exploration_tavily,
        "product_research": search_limits.product_research_tavily,
        "final_product_info": search_limits.final_product_info_tavily,
    }
    
    config = tavily_configs.get(component_name)
    if not config:
        return "basic"  # Default fallback
    
    return config.search_depth