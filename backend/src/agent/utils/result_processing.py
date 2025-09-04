import os
import json
from typing import List
from datetime import datetime
from pydantic import BaseModel, Field

from agent.graph.state_V2 import OverallState
from agent.configuration.llm_setup import get_llm
from agent.configuration.search_limits import get_max_research_products


def save_results_to_disk(state: OverallState) -> OverallState:
    """
    Save the complete state and final product information to disk files.
    Creates timestamped files for both state and products.
    """
    
    # Create results directory if it doesn't exist
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)
    
    # Generate timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save complete state
    try:
        state_filename = f"{results_dir}/state_{timestamp}.json"
        # Convert state to serializable format
        serializable_state = {}
        for key, value in state.items():
            try:
                # Test if value is JSON serializable
                json.dumps(value, default=str)
                serializable_state[key] = value
            except (TypeError, ValueError):
                # If not serializable, convert to string
                serializable_state[key] = str(value)
        
        with open(state_filename, 'w', encoding='utf-8') as f:
            json.dump(serializable_state, f, indent=2, default=str, ensure_ascii=False)
        
        print(f"✅ Complete state saved to: {state_filename}")
        
    except Exception as e:
        print(f"❌ Error saving state: {e}")
    
    # Save final products
    try:
        products_filename = f"{results_dir}/products_{timestamp}.json"
        completed_products = state.get("completed_products", [])
        
        with open(products_filename, 'w', encoding='utf-8') as f:
            json.dump(completed_products, f, indent=2, default=str, ensure_ascii=False)
        
        print(f"✅ Final products saved to: {products_filename}")
        print(f"📊 Saved {len(completed_products)} completed products")
        
    except Exception as e:
        print(f"❌ Error saving products: {e}")
    
    # Return state unchanged (this is a side-effect only node)
    return state


def select_final_products(state: OverallState) -> OverallState:
    """
    Select the final products based on the researched products.
    This function is used to finalize the product selection process.
    """

    query_str = json.dumps(state.get("query_breakdown", {}), indent=0, default=str)

    # Use merged product info (back to original logic)
    products_full_info = merge_product_info(state) 

    products_string = json.dumps(products_full_info, indent=0, default=str)

    instructions = """ 
    You are an expert product researcher. 
    Based on all research and price, keep the products that have a COMPETITIVE ADVANTAGE in at least one dimension. 
    Aim for a MAXIMUM of {max_products_to_show} options, but less is also fine. 
    Choose something you would consider buying for yourself — do NOT overthink, use COMMON SENSE.
    Return a list of PRODUCT IDs you would consider buying — JUST the list, nothing else (no explanation, no text, no markdown).
    You must select AT LEAST TWO.
    
    ***CRITICAL RULE — READ CAREFULLY AND DO NOT IGNORE: ONLY select SPECIFIC PRODUCT MODELS — NOT categories, NOT brands.***
    WRONG example: Smartphone-based sEMG  
    CORRECT example: Spren Body Composition Scanner - Pro iOS App  

    Example output:
    ["id1", "id2", "id3"]

    Here is the query you are trying to solve:
    {query}

    Here is the list of products you should consider:
    {products_string}
    """

    
    max_products_to_show = get_max_research_products()
    instructions = instructions.format(
        query=query_str,
        max_products_to_show=max_products_to_show,
        products_string=products_string
    )

    class ProductSelection(BaseModel):
        products: List[str] = Field(
            description="List of product IDs that are selected based on the research."
        )

        reasoning: str = Field(
            description="Reasoning behind the selection of products, explaining how they compare in meet the user's needs."
        )

    llm_gemini_structured = get_llm("product_selection").with_structured_output(ProductSelection)
    results = llm_gemini_structured.invoke(instructions)

    result_list = results.products

    if not result_list:
        result_list = [products_full_info[0]["id"]]  # Fallback to first product if none selected
        

    return {
        "selected_product_ids": result_list
    }


def merge_product_info(state):
    researched_products = state.get("researched_products", [])
    explored_products = state.get("explored_products", [])
    products_full_info = []

    for product in researched_products:
        product_id = product["product_id"]
        product_info = next((p for p in explored_products if p["id"] == product_id), None)
        if product_info:
           # merge product info and product dicts
            product.update(product_info)
        products_full_info.append(product)
    return products_full_info