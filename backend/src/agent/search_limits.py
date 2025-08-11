"""
Centralized Search Limits Configuration

This module provides a single source of truth for all search tool call limits
across different graph components, ensuring consistency between prompts and hard checks.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class SearchLimitsConfig(BaseModel):
    """Centralized configuration for search limits across all graphs"""
    
    # Simple search limits - one per pattern
    product_exploration_max_searches: int = Field(default=2, description="Max searches for product exploration phase")
    product_research_max_searches: int = Field(default=3, description="Max searches for detailed product research")
    final_product_info_max_searches: int = Field(default=8, description="Max searches for final product information completion")
    
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


def configure_search_limits_from_main_graph(
    product_exploration: int = None,
    product_research: int = None, 
    final_product_info: int = None
) -> None:
    """
    Configure search limits from the main graph - allows override from graph_v2.py
    
    Usage from graph_v2.py:
        from agent.search_limits import configure_search_limits_from_main_graph
        
        # Set custom limits at startup
        configure_search_limits_from_main_graph(
            product_exploration=2,    # explore-agent-graph uses this
            product_research=3,       # research-with-pattern uses this  
            final_product_info=8      # final-info-graph uses this
        )
    """
    global SEARCH_LIMITS
    
    updates = {}
    if product_exploration is not None:
        updates['product_exploration_max_searches'] = product_exploration
    if product_research is not None:
        updates['product_research_max_searches'] = product_research
    if final_product_info is not None:
        updates['final_product_info_max_searches'] = final_product_info
    
    if updates:
        # Create new instance with updated values
        current_data = SEARCH_LIMITS.model_dump()
        current_data.update(updates)
        SEARCH_LIMITS = SearchLimitsConfig(**current_data)
        
        print(f"🔧 Updated search limits: {updates}")


# Component name constants for consistency
class ComponentNames:
    PRODUCT_EXPLORATION = "product_exploration"  # explore_agent_graph.py
    PRODUCT_RESEARCH = "product_research"        # research_with_pattern.py
    FINAL_PRODUCT_INFO = "final_product_info"    # final_info_graph.py