import json

from agent.graph.state_V2 import OverallState
from agent.graph.explore_agent_graph import graph_explore
from agent.graph.final_info_graph import final_info_graph
from agent.configuration.search_limits import get_max_explore_products, get_max_research_products


def call_product_search_graph(state: OverallState) -> OverallState:
    """
    Call the product search graph with the current state.
    This function is used to initiate the product search process.
    """

    query = state.get("query_breakdown", {})
    query_str = json.dumps(query, indent=0, default=str)
    queries = state.get("queries", [])
    criteria = state.get("criteria", [])

    exploration_state = graph_explore.invoke(
        {
            "query": query_str,
            "queries": queries,
            "criteria": criteria,
            "max_explore_products": get_max_explore_products(),
            "max_research_products": get_max_research_products(),
        }
    )

    return {
        "explored_products": exploration_state.get("products", []),
        "researched_products": exploration_state.get("research_results", []),
    }


def complete_product_info(state: OverallState) -> OverallState:
    """
    Complete missing ProductFull fields for selected products using final_info_graph.
    This happens after product selection to enrich the final chosen products.
    Uses batch processing for better performance.
    """
    selected_product_ids = state.get("selected_product_ids", [])
    researched_products = state.get("researched_products", [])
    explored_products = state.get("explored_products", [])
    
    # Prepare batch inputs for final_info_graph
    inputs = []
    product_context = []  # Keep track of research evaluations
    
    for product_id in selected_product_ids:
        # Find the research result for this product
        research_result = next((r for r in researched_products if r.get("product_id") == product_id), {})
        evaluation = research_result.get("evaluation", "")
        
        # Find the corresponding product from explored_products
        base_product = next((p for p in explored_products if p["id"] == product_id), {})
        
        # Prepare input for final_info_graph
        product_input = {
            "id": base_product.get("id", product_id),
            "name": base_product.get("name", "Unknown Product"),
            "criteria_keys": state.get("criteria", []),
            "criteria_values": evaluation,
            "USP": base_product.get("USP", "unknown"),
            "use_case": base_product.get("use_case", "unknown"),
            "other_info": base_product.get("other_info", "")
        }
        
        inputs.append({"product": product_input})

    
    # Batch process all products
    state_list = final_info_graph.batch(inputs, concurrency=len(inputs))
    
    # Process batch results - now using structured ProductFull objects
    completed_products = []
    for state_result in state_list:
        product_formatted = state_result.get("product_output_string", None)
        completed_products.append(product_formatted)

    return {
        "completed_products": completed_products
    }