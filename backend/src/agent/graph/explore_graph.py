from typing import List
from dotenv import load_dotenv

load_dotenv()

from langgraph.graph import StateGraph
from langgraph.graph import START, END

from agent.graph.state_V2 import ProductSimple, ProductSimpleList
from agent.configuration.search_limits import SearchLimitsConfig



from typing import List
from typing import Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from langchain.globals import set_debug, set_verbose
from agent.configuration.llm_setup import get_llm
from agent.utils.tool_orchestrator import DynamicTavilyToolOrchestrator
from agent.graph.search_pattern import BaseSearchState, execute_search_pattern_flexible, SearchConfig
from agent.configuration.search_limits import ComponentNames
from agent.graph.deep_search_graph import research_graph_with_pattern
from agent.prompts.exploration.explore_analyze_prompt import EXPLORE_ANALYZE_PROMPT
from agent.prompts.exploration.explore_search_prompt import EXPLORE_SEARCH_PROMPT
from agent.prompts.exploration.explore_format_prompt import EXPLORE_FORMAT_PROMPT

#set_debug(True)
#set_verbose(True)




class State(BaseSearchState):
    query: str
    queries: List[str]
    criteria: List[str]
    messages_explore: Annotated[list, add_messages]
    products: List[ProductSimple]
    research_results: List[str]
    effort: str  # "low", "medium", "high" - controls search configuration via SearchLimitsConfig
    search_limits: SearchLimitsConfig
    
    # BaseSearchState provides:
    # ai_queries: Annotated[List[AIMessage], add_messages]
    # tool_saved_info: Annotated[List[str], add_messages]
    # tool_last_output: List[AIMessage]
    # final_output: str

# Create Tavily instance with centralized configuration
# Dynamic tool orchestrator for product exploration
tools_orchestrator = DynamicTavilyToolOrchestrator(
    component_name=ComponentNames.PRODUCT_EXPLORATION,
    input_field="ai_queries", 
    output_field="tool_last_output"
)



def create_product_explore_config() -> SearchConfig:
    """Configuration for product exploration search pattern"""
    
    return SearchConfig(
        analyze_prompt=EXPLORE_ANALYZE_PROMPT,
        search_prompt=EXPLORE_SEARCH_PROMPT,
        format_prompt=EXPLORE_FORMAT_PROMPT,
        state_field_mapping={
            "query": "query",
            "queries": "queries",
            "max_explore_products": "max_explore_products"
        },
        
        component_name=ComponentNames.PRODUCT_EXPLORATION
    )


def chatbot_explore(state: State):
    """
    Product exploration using the search pattern
    """
    config = create_product_explore_config()
    search_limits = state.get("search_limits")
    
    return execute_search_pattern_flexible(
        state=state,
        llm=get_llm("search_pattern"),
        llm_with_tools=tools_orchestrator.bind_tools_to_llm(get_llm("pattern_tool_calls"), search_limits),
        config=config
    )

 


def route_tools(state: State):
    """Route based on ai_queries for search pattern"""
    return tools_orchestrator.router("tools")(state)


def format_products(state: State):
    """Format final_output from search pattern into structured products"""
    final_output = state.get("final_output", "")
    print(f"Final explore output: {final_output}")
    
    llm_with_structured_output = get_llm("product_exploration").with_structured_output(ProductSimpleList)
    max_products = state.get("max_explore_products", 15)
    
    result = llm_with_structured_output.invoke(f"""
    Extract and format the product list from this text into the required structure.
    PRESERVE ALL INFORMATION - do not summarize, shorten, or lose any details.
    Keep maximum {max_products} products based on relevance to query: {state.get("query", "")}
    For each product, include ALL available information in the appropriate fields.
    ONLY Look for specific product models, DO not choose a product if it is just a category or brand. Wrong example: Smartphone-based sEMG. Correct example: Spren Body Composition Scanner - Pro ios app.  

    
    Text to process:
    {final_output}
    """)

    return {
        "products": [{
            "id": product["id"],
            "name": product["name"],
            "USP": product["USP"],
            "use_case": product["use_case"],
            "other_info": product["other_info"]
        } for product in result.get("products", [])[:max_products]],
    }

def call_product_research_tool(state: State):
    from langchain_core.runnables import RunnableWithFallbacks, RunnableLambda
    
    crit = state.get("criteria", [])
    inputs = [{"product": p, "criteria": crit} for p in state.get("products", [])]

    # Create fallback that returns error state instead of failing
    def error_fallback(input_data):
        return {
            "final_output": f"Error: Unable to evaluate {input_data.get('product', {}).get('name', 'Unknown')} after retries",
            "product": input_data.get("product", {}),
            "criteria": input_data.get("criteria", [])
        }

    # Create resilient graph with retry and fallbacks
    resilient_graph = research_graph_with_pattern.with_retry(
        retry_if_exception_type=(Exception,),
        wait_exponential_jitter=True,
        stop_after_attempt=2
    )

    # Add fallback to prevent individual failures from killing the batch
    graph_with_fallback = RunnableWithFallbacks(
        runnable=resilient_graph,
        fallbacks=[RunnableLambda(error_fallback)]
    )

    # Execute single batch operation with concurrency - fallbacks handle individual failures
    try:
        state_list = graph_with_fallback.batch(inputs, concurrency=len(inputs))
    except Exception as e:
        print(f"Critical batch failure: {str(e)}")
        # Create error states for all products if complete failure
        state_list = [error_fallback(inp) for inp in inputs]

    eval_results = [s.get("final_output") for s in state_list]
    results = []
    for product, eval_result in zip(state.get("products", []), eval_results):
        if isinstance(eval_result, str):
            results.append({
                "product_id": product.get("id", "Unknown Product"),
                "evaluation": eval_result,
                "status": "error" if eval_result.startswith("Error:") else "success"
            })
    
    return {"research_results": results}





graph_builder = StateGraph(State)

# Dynamic tool node that creates tools based on search_limits from state
def tool_node_explore(state: State):
    """Tool node that creates tools dynamically based on search_limits from state"""
    search_limits = state.get("search_limits")
    return tools_orchestrator.tool_node(search_limits)(state)

graph_builder.add_node("tools_explore", tool_node_explore)  # Renamed to match router expectation
graph_builder.add_node("chatbot_explore", chatbot_explore)
graph_builder.add_node("format_result_explore", format_products)
graph_builder.add_node("call_product_research_tool", call_product_research_tool)

graph_builder.add_edge(START, "chatbot_explore")
graph_builder.add_conditional_edges(
    "chatbot_explore",
    route_tools,
    {"tools": "tools_explore", END: "format_result_explore"},
)
graph_builder.add_edge("tools_explore", "chatbot_explore")
graph_builder.add_edge("format_result_explore", "call_product_research_tool")
graph_builder.add_edge("call_product_research_tool", END)


graph_explore = graph_builder.compile()

if __name__ == "__main__":

    def stream_graph_updates():
        for event in graph_explore.stream(
            
            {"query": "useful sleep tracker", 
        "criteria": ["price","accuracy of total sleep time", 
                     "accuracy of deep sleep stage", 
                     "IOS app insights and interpretability"],
        "queries": [        
            "how to track my sleep with app if i am on a budge?",  
        #"are sleep tracking rings worth buying?",  
        #"are high end sleep tracking rings worth the price?"  
        ],
        "max_explore_products": 2
        }
        ):
            print("Event", event.keys())
            



    stream_graph_updates()