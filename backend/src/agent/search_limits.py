"""
Centralized Search Limits Configuration

This module provides a single source of truth for all search tool call limits
across different graph components, ensuring consistency between prompts and hard checks.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class TavilyConfig(BaseModel):
    """Configuration for Tavily search parameters"""
    max_results: int = Field(default=5, description="Maximum number of search results")
    include_answer: bool = Field(default=False, description="Include direct answer in results") 
    search_depth: str = Field(default="basic", description="Search depth: 'basic' or 'advanced'")


class SearchLimitsConfig(BaseModel):
    """Centralized configuration for search limits and Tavily settings across all graphs"""
    
    # Simple search limits - one per pattern
    product_exploration_max_searches: int = Field(default=2, description="Max searches for product exploration phase")
    product_research_max_searches: int = Field(default=3, description="Max searches for detailed product research")
    final_product_info_max_searches: int = Field(default=8, description="Max searches for final product information completion")
    
    # Product processing limits
    max_explore_products: int = Field(default=2, description="Maximum products to explore")
    max_research_products: int = Field(default=2, description="Maximum products to research in detail")
    max_explore_queries: int = Field(default=5, description="Maximum exploration queries to generate")
    
    # Concurrent tool calls configuration
    product_exploration_concurrent_searches: int = Field(default=2, description="Number of parallel searches per step in exploration")
    product_research_concurrent_searches: int = Field(default=3, description="Number of parallel searches per step in research")
    final_product_info_concurrent_searches: int = Field(default=2, description="Number of parallel searches per step in final info")
    
    # Tavily configuration per component
    product_exploration_tavily: TavilyConfig = Field(default_factory=lambda: TavilyConfig(max_results=3, include_answer=False, search_depth="basic"))
    product_research_tavily: TavilyConfig = Field(default_factory=lambda: TavilyConfig(max_results=5, include_answer=True, search_depth="advanced")) 
    final_product_info_tavily: TavilyConfig = Field(default_factory=lambda: TavilyConfig(max_results=4, include_answer=False, search_depth="basic"))
    
    def get_limits_for_component(self, component_name: str) -> int:
        """Get the search limit for a specific component"""
        component_limits = {
            "product_exploration": self.product_exploration_max_searches,
            "product_research": self.product_research_max_searches, 
            "final_product_info": self.final_product_info_max_searches,
        }
        
        return component_limits.get(component_name, 3)  # Default fallback
    
    def generate_prompt_text(self, component_name: str, current_searches: int = 0) -> str:
        """Generate consistent prompt text about search limits"""
        max_searches = self.get_limits_for_component(component_name)
        
        if current_searches > 0:
            return f"- Max {max_searches} searches for this task. You already used {current_searches} searches."
        else:
            return f"- Use a MAX of {max_searches} searches for this task, ideally fewer."
    
    def check_search_limit(self, component_name: str, current_searches: int) -> bool:
        """Check if we've reached the search limit for a component"""
        max_searches = self.get_limits_for_component(component_name)
        return current_searches >= max_searches
    
    def get_remaining_searches(self, component_name: str, current_searches: int) -> int:
        """Get the number of remaining searches for a component"""
        max_searches = self.get_limits_for_component(component_name)
        return max(0, max_searches - current_searches)
    
    def get_tavily_config(self, component_name: str) -> TavilyConfig:
        """Get Tavily configuration for a specific component"""
        tavily_configs = {
            "product_exploration": self.product_exploration_tavily,
            "product_research": self.product_research_tavily,
            "final_product_info": self.final_product_info_tavily,
        }
        
        return tavily_configs.get(component_name, TavilyConfig())  # Default fallback
    
    def get_concurrent_searches(self, component_name: str) -> int:
        """Get concurrent search count for a specific component"""
        concurrent_configs = {
            "product_exploration": self.product_exploration_concurrent_searches,
            "product_research": self.product_research_concurrent_searches,
            "final_product_info": self.final_product_info_concurrent_searches,
        }
        
        return concurrent_configs.get(component_name, 3)  # Default fallback


# Global instance - single source of truth
SEARCH_LIMITS = SearchLimitsConfig()


# Convenience functions for easy access
def get_search_limit(component_name: str) -> int:
    """Get the search limit for a component"""
    return SEARCH_LIMITS.get_limits_for_component(component_name)


def generate_search_prompt_text(component_name: str, current_searches: int = 0) -> str:
    """Generate prompt text about search limits"""
    return SEARCH_LIMITS.generate_prompt_text(component_name, current_searches)


def is_search_limit_reached(component_name: str, current_searches: int) -> bool:
    """Check if search limit is reached"""
    return SEARCH_LIMITS.check_search_limit(component_name, current_searches)


def get_remaining_searches(component_name: str, current_searches: int) -> int:
    """Get remaining searches"""
    return SEARCH_LIMITS.get_remaining_searches(component_name, current_searches)


def get_tavily_config(component_name: str) -> TavilyConfig:
    """Get Tavily configuration for a component"""
    return SEARCH_LIMITS.get_tavily_config(component_name)


def get_max_explore_products() -> int:
    """Get maximum explore products limit"""
    return SEARCH_LIMITS.max_explore_products


def get_max_research_products() -> int:
    """Get maximum research products limit"""
    return SEARCH_LIMITS.max_research_products


def get_max_explore_queries() -> int:
    """Get maximum explore queries limit"""
    return SEARCH_LIMITS.max_explore_queries


def get_concurrent_searches(component_name: str) -> int:
    """Get concurrent searches count for a component"""
    return SEARCH_LIMITS.get_concurrent_searches(component_name)


def configure_search_limits_from_main_graph(
    product_exploration: int = None,
    product_research: int = None, 
    final_product_info: int = None,
    # Product processing limits
    max_explore_products: int = None,
    max_research_products: int = None,
    max_explore_queries: int = None,
    # Concurrent search configuration
    exploration_concurrent_searches: int = None,
    research_concurrent_searches: int = None,
    final_info_concurrent_searches: int = None,
    # Tavily configuration
    exploration_tavily_max_results: int = None,
    exploration_tavily_include_answer: bool = None,
    exploration_tavily_search_depth: str = None,
    research_tavily_max_results: int = None,
    research_tavily_include_answer: bool = None,
    research_tavily_search_depth: str = None,
    final_info_tavily_max_results: int = None,
    final_info_tavily_include_answer: bool = None,
    final_info_tavily_search_depth: str = None
) -> None:
    """
    Configure search limits and Tavily settings from the main graph - allows override from graph_v2.py
    
    Usage from graph_v2.py:
        configure_search_limits_from_main_graph(
            product_exploration=2,    # explore-agent-graph uses this
            product_research=3,       # research-with-pattern uses this  
            final_product_info=8,     # final-info-graph uses this
            
            # Tavily settings
            exploration_tavily_max_results=3,
            exploration_tavily_include_answer=False,
            exploration_tavily_search_depth="basic"
        )
    """
    global SEARCH_LIMITS
    
    current_data = SEARCH_LIMITS.model_dump()
    updates = {}
    
    # Update search limits
    if product_exploration is not None:
        updates['product_exploration_max_searches'] = product_exploration
    if product_research is not None:
        updates['product_research_max_searches'] = product_research
    if final_product_info is not None:
        updates['final_product_info_max_searches'] = final_product_info
    
    # Update product processing limits
    if max_explore_products is not None:
        updates['max_explore_products'] = max_explore_products
    if max_research_products is not None:
        updates['max_research_products'] = max_research_products
    if max_explore_queries is not None:
        updates['max_explore_queries'] = max_explore_queries
    
    # Update concurrent search configuration
    if exploration_concurrent_searches is not None:
        updates['product_exploration_concurrent_searches'] = exploration_concurrent_searches
    if research_concurrent_searches is not None:
        updates['product_research_concurrent_searches'] = research_concurrent_searches
    if final_info_concurrent_searches is not None:
        updates['final_product_info_concurrent_searches'] = final_info_concurrent_searches
    
    # Update Tavily configurations
    if any([exploration_tavily_max_results is not None, exploration_tavily_include_answer is not None, exploration_tavily_search_depth is not None]):
        tavily_config = current_data['product_exploration_tavily']
        if exploration_tavily_max_results is not None:
            tavily_config['max_results'] = exploration_tavily_max_results
        if exploration_tavily_include_answer is not None:
            tavily_config['include_answer'] = exploration_tavily_include_answer
        if exploration_tavily_search_depth is not None:
            tavily_config['search_depth'] = exploration_tavily_search_depth
        updates['product_exploration_tavily'] = tavily_config
    
    if any([research_tavily_max_results is not None, research_tavily_include_answer is not None, research_tavily_search_depth is not None]):
        tavily_config = current_data['product_research_tavily']
        if research_tavily_max_results is not None:
            tavily_config['max_results'] = research_tavily_max_results
        if research_tavily_include_answer is not None:
            tavily_config['include_answer'] = research_tavily_include_answer
        if research_tavily_search_depth is not None:
            tavily_config['search_depth'] = research_tavily_search_depth
        updates['product_research_tavily'] = tavily_config
    
    if any([final_info_tavily_max_results is not None, final_info_tavily_include_answer is not None, final_info_tavily_search_depth is not None]):
        tavily_config = current_data['final_product_info_tavily']
        if final_info_tavily_max_results is not None:
            tavily_config['max_results'] = final_info_tavily_max_results
        if final_info_tavily_include_answer is not None:
            tavily_config['include_answer'] = final_info_tavily_include_answer
        if final_info_tavily_search_depth is not None:
            tavily_config['search_depth'] = final_info_tavily_search_depth
        updates['final_product_info_tavily'] = tavily_config
    
    if updates:
        # Create new instance with updated values
        current_data.update(updates)
        SEARCH_LIMITS = SearchLimitsConfig(**current_data)
        
        print(f"🔧 Updated search limits and Tavily config: {list(updates.keys())}")


# Component name constants for consistency
class ComponentNames:
    PRODUCT_EXPLORATION = "product_exploration"  # explore_agent_graph.py
    PRODUCT_RESEARCH = "product_research"        # research_with_pattern.py
    FINAL_PRODUCT_INFO = "final_product_info"    # final_info_graph.py