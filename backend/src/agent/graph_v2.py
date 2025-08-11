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
from agent.search_limits import configure_search_limits_from_main_graph, ComponentNames




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
    """
    configure_search_limits_from_main_graph(
        product_exploration=2,      # explore-agent-graph 
        product_research=3,         # research-with-pattern
        final_product_info=8        # final-info-graph
    )
    print("🎯 Search limits configured: explore=2, research=3, final=8")


def configure_aggressive_search_limits():
    """
    Configure more aggressive (faster) search limits for quick results.
    """
    configure_search_limits_from_main_graph(
        product_exploration=2,
        product_research=2, 
        final_product_info=2
    )
    print("⚡ Aggressive search limits: explore=1, research=2, final=4")


def configure_thorough_search_limits():
    """
    Configure more thorough search limits for comprehensive research.
    """
    configure_search_limits_from_main_graph(
        product_exploration=5,
        product_research=8,
        final_product_info=8
    )
    print("🔍 Thorough search limits: explore=5, research=8, final=8")


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
    
    # Test the graph with a sample state
    initial_state = OverallState(
        user_query="sleep tracking device with app",
        max_explore_products=2,
        max_research_products=2,
        max_explore_queries=5,
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