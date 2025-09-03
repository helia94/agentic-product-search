import os
import json
import sqlite3
from typing import List
from datetime import datetime

from langgraph.graph import StateGraph
from langgraph.graph import START, END
from langgraph.types import Command
from langgraph.checkpoint.sqlite import SqliteSaver

from agent.state_V2 import OverallState
from agent.query_processing import (
    pars_query, enrich_query, should_ask_for_use_case, 
    human_ask_for_use_case, find_criteria
)
from agent.query_generation import query_generator
from agent.product_orchestration import call_product_search_graph, complete_product_info
from agent.result_processing import save_results_to_disk, select_final_products
from agent.html_generation import generate_html_results
from agent.configuration import Configuration
from agent.search_limits import (
    configure_search_limits_from_main_graph, 
    ComponentNames,
    get_max_explore_products,
    get_max_research_products, 
    get_max_explore_queries
)




# Create our Agent Graph
builder = StateGraph(OverallState, config_schema=Configuration)

# Define the nodes we will cycle between
builder.add_node("pars_query", pars_query) 
builder.add_node("enrich_query", enrich_query)
builder.add_node("human_ask_for_use_case", human_ask_for_use_case)
builder.add_node("find_criteria", find_criteria)
builder.add_node("query_generator", query_generator)
builder.add_node("call_product_search_graph", call_product_search_graph)
builder.add_node("complete_product_info", complete_product_info)
builder.add_node("select_final_products", select_final_products)
builder.add_node("save_results_to_disk", save_results_to_disk)
builder.add_node("generate_html_results", generate_html_results)


# Set the entrypoint as `planner`
builder.add_edge(START, "pars_query")
builder.add_edge("pars_query", "enrich_query")

builder.add_conditional_edges(
    "enrich_query",
    should_ask_for_use_case,
    {
        True: "human_ask_for_use_case",
        False: "find_criteria"
    }
)
builder.add_edge("human_ask_for_use_case", "find_criteria")
builder.add_edge("find_criteria", "query_generator")
builder.add_edge("query_generator", "call_product_search_graph")
builder.add_edge("call_product_search_graph", "select_final_products")
builder.add_edge("select_final_products", "complete_product_info")
builder.add_edge("complete_product_info", "save_results_to_disk")
builder.add_edge("save_results_to_disk", "generate_html_results")
builder.add_edge("generate_html_results", END)


# Create persistent SQLite checkpointer that survives process restarts
checkpointer = SqliteSaver(sqlite3.connect("checkpoints.db", check_same_thread=False))

# Compile the graph
graph = builder.compile(name="product-search-agent", checkpointer=checkpointer)

# =====================================================================================
# SEARCH LIMITS CONFIGURATION
# =====================================================================================
# The search limits are centrally managed and applied across all search components:
# 
# - explore_agent_graph.py: Uses ComponentNames.PRODUCT_EXPLORATION limits (2)
# - research_with_pattern.py: Uses ComponentNames.PRODUCT_RESEARCH limits (3)
# - final_info_graph.py: Uses ComponentNames.FINAL_PRODUCT_INFO limits (8)
#
# Both prompts and hard checks use the same centralized values, ensuring consistency.
# Just three simple values - one per search pattern as requested.
# =====================================================================================


def configure_search_limits_for_product_search():
    """
    Configure search limits for the product search workflow.
    Simple configuration with just three values - one per search pattern.
    Also configures Tavily settings and product processing limits for each component.
    """
    configure_search_limits_from_main_graph(
        product_exploration=2,      # explore-agent-graph 
        product_research=3,         # research-with-pattern
        final_product_info=8,       # final-info-graph
        
        # Product processing limits
        max_explore_products=2,
        max_research_products=2,
        max_explore_queries=5,
        
        # Concurrent search configuration - parallel tool calls per step
        exploration_concurrent_searches=3,
        research_concurrent_searches=3,
        final_info_concurrent_searches=3,
        
        # Tavily configuration - customize these settings
        exploration_tavily_max_results=3,
        exploration_tavily_include_answer=False,
        exploration_tavily_search_depth="basic",
        
        research_tavily_max_results=5,
        research_tavily_include_answer=True,
        research_tavily_search_depth="advanced",
        
        final_info_tavily_max_results=4,
        final_info_tavily_include_answer=False,
        final_info_tavily_search_depth="basic"
    )
    print("Search limits configured: explore=2, research=3, final=8")
    print("Product limits: explore=2 products, research=2 products, queries=5")
    print("Concurrent searches: exploration=2, research=3, final=2 parallel calls per step")
    print("Tavily configured: exploration=3/basic, research=5/advanced, final=4/basic")


def configure_aggressive_search_limits():
    """
    Configure more aggressive (faster) search limits for quick results.
    """
    configure_search_limits_from_main_graph(
        product_exploration=3,
        product_research=3, 
        final_product_info=3,
        
        # Aggressive product limits - fewer products for speed
        max_explore_products=2,
        max_research_products=1,
        max_explore_queries=3,
        
        # Aggressive concurrent searches - more parallel calls for speed
        exploration_concurrent_searches=2,
        research_concurrent_searches=2,
        final_info_concurrent_searches=2,
        
        # Aggressive Tavily settings - fewer results, basic search
        exploration_tavily_max_results=5,
        exploration_tavily_include_answer=False,
        exploration_tavily_search_depth="basic",
        
        research_tavily_max_results=5,
        research_tavily_include_answer=True,
        research_tavily_search_depth="basic",
        
        final_info_tavily_max_results=5,
        final_info_tavily_include_answer=True,
        final_info_tavily_search_depth="basic"
    )
    print("⚡ Aggressive search limits: explore=3, research=3, final=3")
    print("📦 Aggressive product limits: explore=2 products, research=1 product, queries=3")
    print("🚀 Aggressive concurrent: exploration=3, research=4, final=3 parallel calls per step")
    print("🔍 Aggressive Tavily: exploration=5/basic, research=5/basic, final=5/basic")


def configure_thorough_search_limits():
    """
    Configure more thorough search limits for comprehensive research.
    """
    configure_search_limits_from_main_graph(
        product_exploration=5,
        product_research=10,
        final_product_info=10,
        
        # Thorough product limits - more products for comprehensive analysis
        max_explore_queries=7,
        max_explore_products=10,
        max_research_products=5,
        
        # Thorough concurrent searches - moderate parallel calls for accuracy
        exploration_concurrent_searches=3,
        research_concurrent_searches=3,
        final_info_concurrent_searches=3,
        
        # Thorough Tavily settings - more results, advanced search
        exploration_tavily_max_results=5,
        exploration_tavily_include_answer=False,
        exploration_tavily_search_depth="basic",
        
        research_tavily_max_results=20,
        research_tavily_include_answer=True,
        research_tavily_search_depth="advanced",
        
        final_info_tavily_max_results=10,
        final_info_tavily_include_answer=True,
        final_info_tavily_search_depth="advanced"
    )
    print("🔍 Thorough search limits: explore=5, research=10, final=10")
    print("📦 Thorough product limits: explore=7 products, research=2 products, queries=5")
    print("🚀 Thorough concurrent: exploration=2, research=3, final=3 parallel calls per step")
    print("🔍 Thorough Tavily: exploration=5/basic, research=20/advanced, final=10/advanced")


def initialize_graph_with_search_limits(search_mode: str = "default"):
    """
    Initialize the graph with specified search limit configuration.
    
    Args:
        search_mode: "default", "aggressive", or "thorough"
    """
    if search_mode == "aggressive":
        configure_aggressive_search_limits()
    elif search_mode == "thorough":
        configure_thorough_search_limits() 
    else:
        configure_search_limits_for_product_search()
    
    return graph


# Initialize with default configuration when module is imported
# This ensures search limits are set up when the module is loaded
configure_search_limits_for_product_search()



if __name__ == "__main__":
    # Search limits are already configured when module is imported
    print("🔧 Search limits configured and ready...")
    
    # Optionally override with different configuration:
    # configure_aggressive_search_limits()  # For faster execution
    configure_thorough_search_limits()    # For comprehensive research
    
    # Configuration options - change these to control execution
    RUN_FROM_BEGINNING = True  # Set to True to run from start, False to resume
    RESUME_FROM_NODE = "select_final_products"  # Node name to resume from
    THREAD_ID = "some_id"  # Keep consistent for checkpoint persistence
    
    # Test the graph with a sample state - product limits now come from centralized config
    initial_state = OverallState(
        user_query="home physiotherapy device for Paraplegia patient"
    )

    config = {"configurable": {"thread_id": THREAD_ID}}
    
    if RUN_FROM_BEGINNING:
        print("🚀 Running from beginning...")
        result_state = graph.invoke(initial_state, config=config)
        result_state = graph.invoke(Command(resume="2"), config=config)
        print("✅ Execution completed from beginning")
        print(json.dumps(result_state, indent=2, default=str))
    else:
        print(f"🔄 Attempting to resume from node: {RESUME_FROM_NODE}")
        
        # Get state history from last run
        print("📋 Getting state history from last run...")
        state_history = list(graph.get_state_history(config))
        
        # Find checkpoint at the specified node
        checkpoint_id = None
        for state in state_history:
            if state.next == (RESUME_FROM_NODE,):  # Node about to execute
                checkpoint_id = state.config["configurable"]["checkpoint_id"]
                print(f"✅ Found checkpoint at {RESUME_FROM_NODE}: {checkpoint_id}")
                break
        
        if checkpoint_id:
            # Resume from that checkpoint with updated code
            print(f"🔄 Resuming from {RESUME_FROM_NODE} checkpoint...")
            resume_config = {
                "configurable": {
                    "thread_id": THREAD_ID, 
                    "checkpoint_id": checkpoint_id
                }
            }
            result_state = graph.invoke(None, config=resume_config)
            print("✅ Resumed execution completed")
            print(json.dumps(result_state, indent=2, default=str))
        else:
            print(f"❌ Could not find checkpoint at {RESUME_FROM_NODE}")
            print(f"Available checkpoints ({len(state_history)} total):")
            for i, state in enumerate(state_history):
                print(f"{i}: next={state.next}, checkpoint_id={state.config['configurable']['checkpoint_id']}")
            
            if len(state_history) == 0:
                print("\n💡 No checkpoints found. Running from beginning...")
                result_state = graph.invoke(initial_state, config=config)
            else:
                print(f"\n💡 Available nodes to resume from:")
                unique_nodes = set()
                for state in state_history:
                    if state.next:
                        unique_nodes.add(state.next[0])
                for node in sorted(unique_nodes):
                    print(f"  - {node}")
                print(f"\nChange RESUME_FROM_NODE to one of these and run again.") 