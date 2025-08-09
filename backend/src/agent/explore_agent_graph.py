import os
import json
from typing import List
from datetime import datetime


from dotenv import load_dotenv

load_dotenv()
from langchain_core.messages import AIMessage
from langgraph.types import Send
from langgraph.graph import StateGraph
from langgraph.graph import START, END
from langchain_core.runnables import RunnableConfig
from google.genai import Client
import tiktoken  # Ensure tiktoken is installed in the environment

from agent.state_V2 import  ProductSimple, ProductSimpleList
from agent.configuration import Configuration

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from langgraph.types import interrupt, Command


from typing import List
from pydantic import BaseModel, Field

from langgraph.checkpoint.memory import InMemorySaver

from langchain_tavily import TavilySearch
from typing import Annotated

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

import json

from langchain_core.messages import ToolMessage
from langchain.globals import set_debug, set_verbose
from agent.basic_tools import llm_gemini, tavily
from agent.tool_orchestrator import SimpleToolOrchestrator
from agent.search_pattern import BaseSearchState, execute_search_pattern_flexible, SearchConfig
from agent.research_with_pattern import research_graph_with_pattern

#set_debug(True)
#set_verbose(True)




class State(BaseSearchState):
    query: str
    queries: List[str]
    criteria: List[str]
    messages_explore: Annotated[list, add_messages]
    products: List[ProductSimple]
    research_results: List[str]
    max_explore_products: int
    max_research_products: int
    
    # BaseSearchState provides:
    # ai_queries: Annotated[List[AIMessage], add_messages]
    # tool_saved_info: Annotated[List[str], add_messages]
    # tool_last_output: List[AIMessage]
    # final_output: str

# Tool setup
tools_setup = SimpleToolOrchestrator([tavily], "ai_queries", "tool_last_output")


def create_product_explore_config() -> SearchConfig:
    """Configuration for product exploration search pattern"""
    
    return SearchConfig(
        analyze_prompt="""
        <SYSTEM>
        You are a product discovery expert who extracts specific product information from search results.
        You focus on finding concrete, specific product models with clear specifications.
        </SYSTEM>
        
        <INSTRUCTIONS>
        Analyze the search results and extract specific products mentioned:
        - Look for specific product models, not just categories or brands
        - Extract key details: brand, model name, key features, pricing if available
        - Focus on products that match the search query: {query}
        - Ignore vague or general information
        
        Return your findings as a list of insights about specific products found.
        </INSTRUCTIONS>
        
        <INPUT>
        query: {query}
        queries_remaining: {queries}
        last_tool_call_arguments: {last_tool_call_arguments}
        last_tool_call_output: {last_tool_call_output}
        max_products: {max_explore_products}
        </INPUT>
        """,
        
        search_prompt="""
        <SYSTEM>
        You are a product discovery expert searching for specific products based on user queries.
        Your goal is to find concrete, purchasable products that match the user's needs.
        </SYSTEM>
        
        <INSTRUCTIONS>
        Search for products based on the remaining queries:
        - Process queries one by one: {queries}
        - Search for specific products, models, and brands
        - You have already searched {len_ai_queries} times
        - Don't repeat previous searches: {ai_queries}
        - Focus on finding purchasable, specific product models
        - Stop when you have enough products ({max_explore_products}) or no more queries
        
        Use the search tool to find products or return nothing if done.
        </INSTRUCTIONS>
        
        <INPUT>
        query: {query}
        queries: {queries}
        max_explore_products: {max_explore_products}
        tool_saved_info: {tool_saved_info}
        ai_queries: {ai_queries}
        </INPUT>
        """,
        
        format_prompt="""
        <SYSTEM>
        You are a product discovery expert who formats found products into a structured list.
        </SYSTEM>
        
        <INSTRUCTIONS>
        Format all discovered products into a JSON list with this exact structure:
        
        [
            {{
                "id": "product-model-name",
                "name": "Brand Product Model",
                "USP": "Key selling point",
                "use_case": "Primary use case",
                "other_info": "Price, battery, specs"
            }}
        ]
        
        Requirements:
        - Maximum {max_explore_products} products
        - Only specific, purchasable product models
        - Deduplicate similar products
        - Focus on products matching query: {query}
        </INSTRUCTIONS>
        
        <INPUT>
        query: {query}
        queries: {queries}
        max_explore_products: {max_explore_products}
        tool_saved_info: {tool_saved_info}
        </INPUT>
        """,
        
        state_field_mapping={
            "query": "query",
            "queries": "queries",
            "max_explore_products": "max_explore_products"
        },
        
        max_searches=2
    )


def chatbot_explore(state: State):
    """
    Product exploration using the search pattern
    """
    config = create_product_explore_config()
    
    return execute_search_pattern_flexible(
        state=state,
        llm=llm_gemini,
        llm_with_tools=tools_setup.bind_tools_to_llm(llm_gemini),
        config=config
    )

 


def route_tools(state: State):
    """Route based on ai_queries for search pattern"""
    return tools_setup.router("tools")(state)


def format_products(state: State):
    """Format final_output from search pattern into structured products"""
    final_output = state.get("final_output", "")
    print(f"Final explore output: {final_output}")
    
    llm_with_structured_output = llm_gemini.with_structured_output(ProductSimpleList)
    max_products = state.get("max_explore_products", 15)
    
    result = llm_with_structured_output.invoke(f"""
    Extract and format the product list from this text into the required structure.
    Deduplicate and keep maximum {max_products} products based on relevance to query: {state.get("query", "")}
    
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
    crit = state.get("criteria", [])
    inputs = [{"product": p, "criteria": crit} for p in state.get("products", [])]

    state_list = research_graph_with_pattern.batch(inputs, concurrency=len(inputs))
    eval_results = [ s.get("final_output") for s in state_list]
    results = []
    for product, eval_result in zip(state.get("products", []), eval_results):
        if isinstance(eval_result, str):
            results.append({
                "product_id": product.get("id", "Unknown Product"),
                "evaluation": eval_result
            })
    return {"research_results": results}





graph_builder = StateGraph(State)

# Use new tool orchestration
tool_node_explore = tools_setup.tool_node()

graph_builder.add_node("tools", tool_node_explore)  # Renamed to match router expectation
graph_builder.add_node("chatbot_explore", chatbot_explore)
graph_builder.add_node("format_products", format_products)
graph_builder.add_node("call_product_research_tool", call_product_research_tool)

graph_builder.add_edge(START, "chatbot_explore")
graph_builder.add_conditional_edges(
    "chatbot_explore",
    route_tools,
    {"tools": "tools", END: "format_products"},
)
graph_builder.add_edge("tools", "chatbot_explore")
graph_builder.add_edge("format_products", "call_product_research_tool")
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