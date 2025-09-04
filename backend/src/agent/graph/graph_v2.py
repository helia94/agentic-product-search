import os
import json
import sqlite3
from typing import List
from datetime import datetime

from langgraph.graph import StateGraph
from langgraph.graph import START, END
from langgraph.types import Command
from langgraph.checkpoint.sqlite import SqliteSaver

from agent.graph.state_V2 import OverallState
from agent.graph.query_processing import (
    pars_query, enrich_query, should_ask_for_use_case, 
    human_ask_for_use_case, find_criteria
)
from agent.graph.query_generation import query_generator
from agent.graph.product_orchestration import call_product_search_graph, complete_product_info
from agent.utils.result_processing import save_results_to_disk, select_final_products
from agent.graph.html_generation import generate_html_results
from agent.configuration import Configuration
from agent.configuration.search_limits import initialize_graph_with_search_limits





# Create our Agent Graph
builder = StateGraph(OverallState, config_schema=Configuration)



# Add tracked nodes to the graph
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
print("[GRAPH] All nodes wrapped with progress tracking")


# Set the entrypoint 
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


# Create persistent SQLite checkpointer 
checkpointer = SqliteSaver(sqlite3.connect("checkpoints.db", check_same_thread=False))

# Compile the graph
graph = builder.compile(name="product-search-agent", checkpointer=checkpointer)




if __name__ == "__main__":
    # Search limits are already configured when module is imported
    print("[SEARCH] Search limits configured and ready...")
    initialize_graph_with_search_limits(search_mode = "aggressive")
    
    # Configuration options - change these to control execution
    RUN_FROM_BEGINNING = True  # Set to True to run from start, False to resume
    RESUME_FROM_NODE = "select_final_products"  # Node name to resume from
    THREAD_ID = "some_id"  # Keep consistent for checkpoint persistence
    
    # Test the graph with a sample state - product limits now come from centralized config
    initial_state = OverallState(
        user_query="home physiotherapy device for Paraplegia patient",
        effort="medium"  # Test with medium effort level
    )

    config = {"configurable": {"thread_id": THREAD_ID}}
    
    if RUN_FROM_BEGINNING:
        print("[GRAPH] Running from beginning...")
        result_state = graph.invoke(initial_state, config=config)
        
        # Check if graph execution is incomplete and needs resume
        if (hasattr(result_state, 'query_tips') and 
            hasattr(result_state.query_tips, 'potential_use_cases_to_clarify') and 
            result_state.query_tips.potential_use_cases_to_clarify and
            (not hasattr(result_state, 'queries') or not result_state.queries) and
            (not hasattr(result_state, 'html_report') or not result_state.html_report)):
            print("[GRAPH] Graph not fully complete, invoking resume...")
            result_state = graph.invoke(Command(resume="2"), config=config)
        
        print("[GRAPH] Execution completed from beginning")
        print(json.dumps(result_state, indent=2, default=str))
    else:
        print(f"[GRAPH] Attempting to resume from node: {RESUME_FROM_NODE}")
        
        # Get state history from last run
        print("[GRAPH] Getting state history from last run...")
        state_history = list(graph.get_state_history(config))
        
        # Find checkpoint at the specified node
        checkpoint_id = None
        for state in state_history:
            if state.next == (RESUME_FROM_NODE,):  # Node about to execute
                checkpoint_id = state.config["configurable"]["checkpoint_id"]
                print(f"[GRAPH] Found checkpoint at {RESUME_FROM_NODE}: {checkpoint_id}")
                break
        
        if checkpoint_id:
            # Resume from that checkpoint with updated code
            print(f"[GRAPH] Resuming from {RESUME_FROM_NODE} checkpoint...")
            resume_config = {
                "configurable": {
                    "thread_id": THREAD_ID, 
                    "checkpoint_id": checkpoint_id
                }
            }
            result_state = graph.invoke(None, config=resume_config)
            print("[GRAPH] Resumed execution completed")
            print(json.dumps(result_state, indent=2, default=str))
        else:
            print(f"[GRAPH] Could not find checkpoint at {RESUME_FROM_NODE}")
            print(f"Available checkpoints ({len(state_history)} total):")
            for i, state in enumerate(state_history):
                print(f"{i}: next={state.next}, checkpoint_id={state.config['configurable']['checkpoint_id']}")
            
            if len(state_history) == 0:
                print("\n[GRAPH] No checkpoints found. Running from beginning...")
                result_state = graph.invoke(initial_state, config=config)
            else:
                print(f"\n[GRAPH] Available nodes to resume from:")
                unique_nodes = set()
                for state in state_history:
                    if state.next:
                        unique_nodes.add(state.next[0])
                for node in sorted(unique_nodes):
                    print(f"  - {node}")
                print(f"\nChange RESUME_FROM_NODE to one of these and run again.") 