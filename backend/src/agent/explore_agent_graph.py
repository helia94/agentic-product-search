import os
import json
from typing import List
from datetime import datetime


from dotenv import load_dotenv

from agent.basic_tools import route_tools_by_messages
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
from agent.basic_tools import llm_gemini, llm_with_tools, route_tools_by_messages, BasicToolNode, tavily
from agent.research_agent_graph import product_research_tool

#set_debug(True)
#set_verbose(True)



class State(TypedDict):
    query: str
    queries: List[str]
    criteria: List[str]
    messages_explore: Annotated[list, add_messages]
    products: List[ProductSimple]
    research_results: List[str]
    max_explore_products: int
    max_research_products: int

 
def chatbot_explore(state: State):
    queries = " ".join(state.get("queries", []))
    max_explore_products = state.get("max_explore_products", 15)

    instructions = """
        your task is to go through a list of search queries, call search tool on each, and then extract products from the search results.
        Search for this query using your tools and convert whatever response you find in them into a list of mentioned products with [brand, product_name, unique_selling_point, any_other_product_info]. 
        the first response should be a tool call, after getting the results you have two tasks. Discover and format products from the search results, call the search tool again with the next query. 
        When you have no more queries, or you reach {max_explore_products} products without duplicates, return the list of products you found. The product should be super specific model name, not just category or brand, fully unique and pricable .

        here is an example of the product list you should return:

        [
            {{
                "id": "fitbit-charge-6",
                "name": "Fitbit Charge 6",
                "USP": "GPS, Google, ECG",
                "use_case": "Serious fitness tracking",
                "other_info": "40+ modes, 7-day battery, $160"
            }},
            {{
                "id": "fitbit-inspire-3",
                "name": "Fitbit Inspire 3",
                "USP": "Long battery, cheap",
                "use_case": "Basic daily tracking",
                "other_info": "20+ modes, SpO2, $99"
            }}
        ]


        here is the list of queries you should search for:
        {queries}

        here are are the past messages:

        """
    system_prompt = instructions.format(
        queries=queries, 
        max_explore_products=max_explore_products)

    return {"messages_explore": [llm_with_tools.invoke([system_prompt] + state["messages_explore"])]}

 


def route_tools(state: State):
    return route_tools_by_messages(state.get("messages_explore", []))


def format_products(State: State):
    final_message = State.get("messages_explore", [])[-1].content
    print(f"Final explore message: {final_message}")
    llm_with_structured_output = llm_gemini.with_structured_output(ProductSimpleList)
    max_products = State.get("max_explore_products", 15)
    result = llm_with_structured_output.invoke([
        """
        return just the product list in desired format. deduplicate the list and keep maximum {max_products} based on usp relevance to the query {query}.
        """.format(query=State.get("query", ""), max_products=max_products) + final_message])

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

    eval_results = product_research_tool.batch(inputs, concurrency=len(inputs))
    results = []
    for product, eval_result in zip(state.get("products", []), eval_results):
        if isinstance(eval_result, str):
            results.append({
                "product": product.get("id", "Unknown Product"),
                "evaluation": eval_result
            })
    return {"research_results": results}





graph_builder = StateGraph(State)
tool_node_explore = BasicToolNode(tools=[tavily], message_field="messages_explore")

graph_builder.add_node("tool_node_explore", tool_node_explore)
graph_builder.add_node("chatbot_explore", chatbot_explore)
graph_builder.add_node("format_products", format_products)
graph_builder.add_node("call_product_research_tool", call_product_research_tool)


graph_builder.add_edge(START, "chatbot_explore")
graph_builder.add_conditional_edges(
    "chatbot_explore",
    route_tools,
    # The following dictionary lets you tell the graph to interpret the condition's outputs as a specific node
    # It defaults to the identity function, but if you
    # want to use a node named something else apart from "tools",
    # You can update the value of the dictionary to something else
    # e.g., "tools": "my_tools"
    {"tools": "tool_node_explore", END: "format_products"},
)
graph_builder.add_edge("tool_node_explore", "chatbot_explore")
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