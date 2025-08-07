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
from typing import List
from typing import Annotated

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

import json


from langchain.globals import set_debug, set_verbose
from agent.state_V2 import ProductSimple
from agent.basic_tools import llm_gemini, llm_with_tools, route_tools_by_messages, tools, BasicToolNode, tavily

#set_debug(True)
#set_verbose(True)

load_dotenv()



class State(TypedDict):
    query: str
    criteria: List[str]
    products: List[ProductSimple]
    messages_research: Annotated[list, add_messages]


 
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
                    "fitbit-charge-6": {{
                        "price": "$160",
                        "accuracy_of_total_sleep_time": "Good (within 17-20min vs PSG, clinically acceptable <30min bias)",
                        "accuracy_of_deep_sleep_stage": "Poor (70.5% accuracy, tends to overestimate at low amounts)",
                        "ios_app_insights_and_interpretability": "Premium required for sleep score breakdown, sleep profile analysis, restoration details"
                    }},
                    "fitbit-inspire-3": {{
                        "price": "$99", 
                        "accuracy_of_total_sleep_time": "Good (within clinical acceptable range vs PSG)",
                        "accuracy_of_deep_sleep_stage": "Poor (tends to overestimate, inconsistent vs medical grade)",
                        "ios_app_insights_and_interpretability": "Premium required for sleep score breakdown, sleep profile analysis, restoration details"
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



def route_tools(state: State):
    return route_tools_by_messages(state.get("messages_research", []))





def print_node(state: State):
    print("Current state:")
    print(state.get("messages_research", [])[-1].content)
    return state

graph_builder = StateGraph(State)
tool_node_research = BasicToolNode(tools=[tavily], message_field="messages_research")

graph_builder.add_node("tool_node_research", tool_node_research)
graph_builder.add_node("chatbot_research", chatbot_research)
graph_builder.add_node("print_node", print_node)



graph_builder.add_edge(START, "chatbot_research")

graph_builder.add_conditional_edges(
    "chatbot_research",
    route_tools,
    {"tools": "tool_node_research", END: "print_node"},
)
graph_builder.add_edge("tool_node_research", "chatbot_research")
graph_builder.add_edge("print_node", END)



graph = graph_builder.compile()


if __name__ == "__main__":

    def stream_graph_updates():
        for event in graph.stream(
            {
            "query": "useful sleep tracker", 
            "criteria": [
                "price",
                "accuracy of total sleep time",
                "accuracy of deep sleep stage",
                "IOS app insights and interpretability"
            ],

            "products": [
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
            }
        ):
            print("Event", event.keys())
            


    stream_graph_updates()