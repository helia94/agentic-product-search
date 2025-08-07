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

#set_debug(True)
#set_verbose(True)

load_dotenv()

llm_gemini = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)


tavily = TavilySearch(
    max_results=1, #10
    topic="general",
    #include_answer="advanced",
    #include_raw_content=True,
    # include_images=False,
    # include_image_descriptions=False,
    # search_depth="basic",
    # time_range="day",
    #include_domains=["reddit.com/"],
    #exclude_domains=["*/blog/*"],
)

tools = [tavily]

# Modification: tell the LLM which tools it can call
llm_with_tools = llm_gemini.bind_tools(tools)

class State(TypedDict):
    query: str
    queries: List[str]
    criteria: List[str]
    messages_explore: Annotated[list, add_messages]
    products: List[ProductSimple]
    messages_research: Annotated[list, add_messages]
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
            {
                "id": "fitbit-charge-6",
                "name": "Fitbit Charge 6",
                "USP": "GPS, Google, ECG",
                "use_case": "Serious fitness tracking",
                "other_info": "40+ modes, 7-day battery, $160"
            },
            {
                "id": "fitbit-inspire-3",
                "name": "Fitbit Inspire 3",
                "USP": "Long battery, cheap",
                "use_case": "Basic daily tracking",
                "other_info": "20+ modes, SpO2, $99"
            }
        ]


        here is the list of queries you should search for:
        {queries}

        here are are the past messages:

        """
    system_prompt = instructions.format(
        queries=queries, 
        max_explore_products=max_explore_products)

    return {"messages_explore": [llm_with_tools.invoke([system_prompt] + state["messages_explore"])]}

 
def chatbot_research(state: State):
    products_list = state.get("products", [])
    products = " ,".join([f"{product['id']}: {product['name']}" for product in products_list])
    criteria = " ,".join(state.get("criteria", []))


    instructions = """
            for every product find all relevant criteria and check all conditions by using your search tool. 
            Start with easy objective criteria that is obvious by seller webpage and then move on to search user reviews and deep dives for subjective and hard to define criteria. 
            use your search tool but no more than 5 searches per product, best to get it all with only one shot. 
            i am counting on your unfiltered expert opinion, do not just take what the seller claims, but what the users say and what you can find in the reviews.
            be super direct, no fluff, no generic statements, all words should count, limited space in the ui to show the results, imagine the shortest message to deliver to a best friend.
            criteria should be relative if a is better than b in some aspect, make sure it shows in the wordings, if you do not know the criteria value, use "unknown" as a placeholder.
            if the model of product is not clear do not do anything, just return empty list, do not write things depend, maybe you are the info source, do not send the user to do work, you do all the work.
            when you have all the info return the list of criteria for each product in the following format.:

            {{
                "product_id_1": {{
                    "criteria_id_1" : "value of criteria",
                    "criteria_id_2" : "unknown"
                }},
                "product_id_2": {{
                    "criteria_id_1" : "value of criteria 1",
                    "criteria_id_2" : "value of criteria 2"
                }}
            }}

            here are the products you should research:
            {products1}
            here are the criteria you should evaluate for each product:
            {criteria}

        """
    system_prompt = instructions.format(
        products1=products,
        criteria=criteria,
    )

    return {"messages_research": [llm_with_tools.invoke([system_prompt] + state["messages_research"])]}





class BasicToolNode:
    """A node that runs the tools requested in the last AIMessage."""

    def __init__(self, tools: list) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}

    

    def __call__(self, inputs: dict):
        research_mode = False
        if messages := inputs.get("messages_explore", []):
            message = messages[-1]
        elif message := inputs.get("message_research", []):
            message = messages[-1]
            research_mode = True
        else:
            raise ValueError("No message found in input")
        outputs = []
        for tool_call in message.tool_calls:
            tool_result = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )
            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        if research_mode:
            return {"message_research": outputs}
        else :
            return {"messages_explore": outputs}


def route_tools(
    state: State,
):
    """
    Use in the conditional_edge to route to the ToolNode if the last message
    has tool calls. Otherwise, route to the end.
    """
    list_of_ms = []
    if messages := state.get("messages_explore", []):
        list_of_ms += [messages[-1]]
    if messages := state.get("messages_research", []):
        list_of_ms += [messages[-1]]

    for ai_message in list_of_ms:
        if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
            return "tools"
    return END


def format_products(State: State):
    final_message = State.get("messages_explore", [])[-1].content
    print(f"Final explore message: {final_message}")
    llm_with_structured_output = llm_gemini.with_structured_output(ProductSimpleList)
    result = llm_with_structured_output.invoke([
        """
        return just the product list in desired format. deduplicate the list and keep maximum 25 based on usp relevance to the query {query}.
        """.format(query=State.get("query", "")) + final_message])
        
    return {
        "products": [{
            "id": product["id"],
            "name": product["name"],
            "USP": product["USP"],
            "use_case": product["use_case"],
            "other_info": product["other_info"]
        } for product in result.get("products", [])],
    }



def print_node(state: State):
    print("Current state:")
    print(state.get("messages_research", [])[-1].content)
    return state

graph_builder = StateGraph(State)
tool_node_explore = BasicToolNode(tools=[tavily])
tool_node_research = BasicToolNode(tools=[tavily])

graph_builder.add_node("tool_node_explore", tool_node_explore)
graph_builder.add_node("tool_node_research", tool_node_research)
graph_builder.add_node("chatbot_explore", chatbot_explore)
graph_builder.add_node("format_products", format_products)
graph_builder.add_node("chatbot_research", chatbot_research)
graph_builder.add_node("print_node", print_node)

# The `tools_condition` function returns "tools" if the chatbot asks to use a tool, and "END" if
# it is fine directly responding. This conditional routing defines the main agent loop.

# Any time a tool is called, we return to the chatbot to decide the next step

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
graph_builder.add_edge("format_products", END)




graph = graph_builder.compile()

if __name__ == "__main__":

    def stream_graph_updates(user_input: str):
        for event in graph.stream(
            
            {"query": "useful sleep tracker", 
        "criteria": ["price","accuracy of total sleep time", 
                     "accuracy of deep sleep stage", 
                     "IOS app insights and interpretability"],
        "queries": [        
            "how to track my sleep with app if i am on a budge?",  
        #"are sleep tracking rings worth buying?",  
        #"are high end sleep tracking rings worth the price?"  
        ], 
        "messages_explore": [{"role": "user", "content": user_input}]}
        ):
            print("Event", event.keys())
            

    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        stream_graph_updates(user_input)