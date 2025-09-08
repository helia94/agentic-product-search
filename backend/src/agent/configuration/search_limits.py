"""
Centralized Search Limits Configuration

This module provides a single source of truth for all search tool call limits
across different graph components, ensuring consistency between prompts and hard checks.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class TavilyConfig(BaseModel):
    """Configuration for Tavily search parameters"""
    max_results: int = Field(description="Maximum number of search results")
    include_answer: bool = Field(description="Include direct answer in results") 
    search_depth: str = Field(description="Search depth: 'basic' or 'advanced'")


class SearchLimitsConfig(BaseModel):
    """Base configuration for search limits and Tavily settings across all graphs"""
    
    # Simple search limits - one per pattern
    product_exploration_max_searches: int = Field(description="Max searches for product exploration phase")
    product_research_max_searches: int = Field(description="Max searches for detailed product research")
    final_product_info_max_searches: int = Field(description="Max searches for final product information completion")
    
    # Product processing limits
    max_explore_products: int = Field(description="Maximum products to explore")
    max_research_products: int = Field(description="Maximum products to research in detail")
    max_explore_queries: int = Field(description="Maximum exploration queries to generate")
    
    # Concurrent tool calls configuration
    product_exploration_concurrent_searches: int = Field(description="Number of parallel searches per step in exploration")
    product_research_concurrent_searches: int = Field(description="Number of parallel searches per step in research")
    final_product_info_concurrent_searches: int = Field(description="Number of parallel searches per step in final info")
    
    # Tavily configuration per component
    product_exploration_tavily: TavilyConfig = Field(description="Tavily configuration for exploration")
    product_research_tavily: TavilyConfig = Field(description="Tavily configuration for research")
    final_product_info_tavily: TavilyConfig = Field(description="Tavily configuration for final info")



class Low(SearchLimitsConfig):
    """Low effort configuration - quick results with minimal searches"""
    
    product_exploration_max_searches: int = 2
    product_research_max_searches: int = 2
    final_product_info_max_searches: int = 3
    
    max_explore_products: int = 1
    max_research_products: int = 1
    max_explore_queries: int = 3
    
    product_exploration_concurrent_searches: int = 3
    product_research_concurrent_searches: int = 3
    final_product_info_concurrent_searches: int = 3
    
    product_exploration_tavily: TavilyConfig = Field(default_factory=lambda: TavilyConfig(max_results=2, include_answer=False, search_depth="basic"))
    product_research_tavily: TavilyConfig = Field(default_factory=lambda: TavilyConfig(max_results=2, include_answer=True, search_depth="basic"))
    final_product_info_tavily: TavilyConfig = Field(default_factory=lambda: TavilyConfig(max_results=2, include_answer=True, search_depth="basic"))


class Medium(SearchLimitsConfig):
    """Medium effort configuration - balanced performance and thoroughness"""
    
    product_exploration_max_searches: int = 3
    product_research_max_searches: int = 5
    final_product_info_max_searches: int = 8
    
    max_explore_products: int = 6
    max_research_products: int = 3
    max_explore_queries: int = 5
    
    product_exploration_concurrent_searches: int = 5
    product_research_concurrent_searches: int = 5
    final_product_info_concurrent_searches: int = 5
    
    product_exploration_tavily: TavilyConfig = Field(default_factory=lambda: TavilyConfig(max_results=5, include_answer=False, search_depth="basic"))
    product_research_tavily: TavilyConfig = Field(default_factory=lambda: TavilyConfig(max_results=5, include_answer=True, search_depth="advanced"))
    final_product_info_tavily: TavilyConfig = Field(default_factory=lambda: TavilyConfig(max_results=5, include_answer=True, search_depth="basic"))


class High(SearchLimitsConfig):
    """High effort configuration - thorough research with comprehensive analysis"""
    
    product_exploration_max_searches: int = 5
    product_research_max_searches: int = 12
    final_product_info_max_searches: int = 10
    
    max_explore_products: int = 10
    max_research_products: int = 5
    max_explore_queries: int = 7
    
    product_exploration_concurrent_searches: int = 5
    product_research_concurrent_searches: int = 5
    final_product_info_concurrent_searches: int = 5
    
    product_exploration_tavily: TavilyConfig = Field(default_factory=lambda: TavilyConfig(max_results=20, include_answer=False, search_depth="basic"))
    product_research_tavily: TavilyConfig = Field(default_factory=lambda: TavilyConfig(max_results=20, include_answer=True, search_depth="advanced"))
    final_product_info_tavily: TavilyConfig = Field(default_factory=lambda: TavilyConfig(max_results=20, include_answer=True, search_depth="advanced"))



# Global instance removed - use map_to_search_limits() to get configuration based on effort level



class ComponentNames:
    PRODUCT_EXPLORATION = "product_exploration"  # explore_agent_graph.py
    PRODUCT_RESEARCH = "product_research"        # research_with_pattern.py
    FINAL_PRODUCT_INFO = "final_product_info"    # final_info_graph.py


def map_to_search_limits(effort: str) -> SearchLimitsConfig:
    """Map effort level to corresponding SearchLimitsConfig"""
    effort_map = {
        "low": Low(),
        "medium": Medium(),
        "high": High()
    }
    return effort_map.get(effort.lower()) 

# Function removed - search limits are now managed through the LangGraph state