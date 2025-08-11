"""
Example of how to configure search limits from the main graph

This shows how to set up centralized search limits that work consistently
across all search patterns and loops.
"""

from agent.search_limits import configure_search_limits_from_main_graph, ComponentNames

def configure_search_limits_for_product_search():
    """
    Example configuration for product search workflow.
    Call this from graph_v2.py before starting the graph execution.
    """
    
    # Configure different limits for different loops/phases
    configure_search_limits_from_main_graph(
        # Base component limits
        product_exploration=2,     # Base limit for product exploration
        product_research=3,        # Base limit for product research  
        final_product_info=8,      # Base limit for final product info
        
        # Loop-specific limits (overrides base limits)
        loop_limits={
            ComponentNames.PRODUCT_RESEARCH: {
                1: 2,  # First product research loop: 2 searches max
                2: 4,  # Second loop: 4 searches max  
                3: 1,  # Third loop: 1 search max (quick validation)
            },
            ComponentNames.FINAL_PRODUCT_INFO: {
                1: 5,  # First pass: 5 searches for detailed info
                2: 8,  # Second pass: up to 8 searches for complete info
                3: 2,  # Final pass: just 2 searches for any missing pieces
            }
        }
    )
    
    print("🎯 Search limits configured for product search workflow")


def configure_aggressive_search_limits():
    """
    More aggressive search limits for faster execution
    """
    configure_search_limits_from_main_graph(
        product_exploration=1,
        product_research=2, 
        final_product_info=4,
        loop_limits={
            ComponentNames.PRODUCT_RESEARCH: {
                1: 1,  # Very quick first pass
                2: 2,  # Slightly more thorough second pass
            }
        }
    )
    
    print("⚡ Aggressive search limits configured")


def configure_thorough_search_limits():
    """
    More thorough search limits for comprehensive research
    """
    configure_search_limits_from_main_graph(
        product_exploration=4,
        product_research=6,
        final_product_info=12,
        loop_limits={
            ComponentNames.PRODUCT_RESEARCH: {
                1: 3,  # Initial research phase  
                2: 6,  # Deep research phase
                3: 4,  # Validation phase
                4: 2,  # Final cleanup phase
            }
        }
    )
    
    print("🔍 Thorough search limits configured")


# Usage examples:

# In graph_v2.py, at the beginning of main execution:
# from agent.search_limits_example import configure_search_limits_for_product_search
# configure_search_limits_for_product_search()

# When creating search configs with loop numbers:
# from agent.search_pattern import create_product_research_config
# 
# # For different loops in the same workflow:
# config_loop1 = create_product_research_config(loop_number=1)  # Uses loop 1 limits
# config_loop2 = create_product_research_config(loop_number=2)  # Uses loop 2 limits 
# config_loop3 = create_product_research_config(loop_number=3)  # Uses loop 3 limits