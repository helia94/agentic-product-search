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
from agent.state_V2 import ProductFull
from agent.basic_tools import llm_gemini, llm_with_tools, route_tools_by_messages, tools, BasicToolNode, tavily

#set_debug(True)
#set_verbose(True)



class State(TypedDict):
    product: str
    messages: List[AIMessage]
    product_output_string: str
    product_output_formatted: ProductFull


 
def chatbot_research(state: State):
    product = state.get("product", "")
    criteria = " ,".join(state.get("criteria", []))


    instructions = """
    <SYSTEM_PROMPT>
    You are a product research agent.

    <TASK>
    For the given product, FILL all remaining fields in the `ProductFull` class.
    Use the SEARCH TOOL if any field is missing (except: `criteria`, `USP`, `use_case` — these are already provided).
    Return either:
    - a search tool call (with precise query string), OR
    - a fully completed ProductFull dictionary.
    </TASK>

    <CONSTRAINTS>
    - Max 5 searches per product. Prefer getting everything in 1 or 2 searches.
    - Be concise, avoid fluff. Use info-dense, direct language.
    - If a value is unknown or unverifiable, write `"unknown"` (never guess).
    - Review summaries = keyword-only, no generic opinions (e.g., say “short battery, clean app” not “great product”).
    - Image URLs: 1–3, from official or reputable retailers.
    - Product URL must be live and specific to given country; if not available, include original URL + warning.
    - Stop and return empty if product model is unclear.
    </CONSTRAINTS>

    <INPUT FORMAT>
    Product:
    - name: str
    - criteria: Dict[str, str]
    - USP: str
    - use_case: str

    <OUTPUT FORMAT>
    Return one of:
    1. `search("your_query_here")`
    2. `ProductFull` with all fields completed

    <EXAMPLES>

    # ✅ EXAMPLE 1

    Input:
    product = "Withings Sleep Analyzer"
    criteria = {
        "price": "$129",
        "accuracy_of_total_sleep_time": "Acceptable (within ~20 min bias vs PSG in clinical studies)",
        "accuracy_of_sleep_stages": "Fair (good for light/deep, but struggles with REM detection)"
    }
    USP = "non-wearable apnea tracking"
    use_case = "at-home sleep diagnostics"

    search_queries = [
        search("Withings Sleep Analyzer release year, design/manufacture country, user rating, reviews count, Amazon URL, review summary, official product images")
    ]

    Final Output:
    {
        "id": "withings_sleep_analyzer_2020",
        "name": "Withings Sleep Analyzer – Advanced Sleep Tracking Pad",
        "criteria": {
            "price": "$129",
            "accuracy_of_total_sleep_time": "Acceptable (within ~20 min bias vs PSG in clinical studies)",
            "accuracy_of_sleep_stages": "Fair (good for light/deep, but struggles with REM detection)"
        },
        "USP": "non-wearable apnea tracking",
        "use_case": "at-home sleep diagnostics",
        "price": 129.0,
        "country": "Designed in France, produced in China",
        "year": 2020,
        "review_summary": "non-intrusive, accurate apnea detection, app sync issues",
        "rating": "4.2/5 on Amazon",
        "reviews_count": "1563",
        "image_url": [
            "https://www.withings.com/us/en/sleep-analyzer/img1.jpg"
        ],
        "product_url": "https://www.withings.com/fr/en/sleep-analyzer"
    }

    # ✅ EXAMPLE 2

    Input:
    product = "Oura Ring Gen3"
    criteria = {
        "price": "$299",
        "accuracy_of_total_sleep_time": "Good (within 10-15 min bias vs PSG)",
        "accuracy_of_deep_sleep_stage": "Moderate (overestimates in short duration sleepers)"
    }
    USP = "smart ring with sleep recovery insights"
    use_case = "daily personal wellness tracking"

    search_queries = [
        search("Oura Ring Gen3 release year, design/manufacture origin, user rating, review summary, reviews count, official retailer link, product image")
    ]

    Final Output:
    {
        "id": "oura_ring_gen3_2021",
        "name": "Oura Ring Gen3 Heritage – Titanium Smart Ring",
        "criteria": {
            "price": "$299",
            "accuracy_of_total_sleep_time": "Good (within 10-15 min bias vs PSG)",
            "accuracy_of_deep_sleep_stage": "Moderate (overestimates in short duration sleepers)"
        },
        "USP": "smart ring with sleep recovery insights",
        "use_case": "daily personal wellness tracking",
        "price": 299.0,
        "country": "Designed in Finland, produced in China",
        "year": 2021,
        "review_summary": "sleek, accurate sleep, costly subscription, small size complaints",
        "rating": "4.5/5 on Amazon",
        "reviews_count": "3820",
        "image_url": [
            "https://ouraring.com/images/product-gen3-heritage-front.jpg"
        ],
        "product_url": "https://ouraring.com/product/gen3"
    }
    </EXAMPLES>
    </SYSTEM_PROMPT>

        """
    system_prompt = instructions.format(
        product=product,
        criteria=criteria,
    )

    return {"messages_research": [llm_with_tools.invoke([system_prompt] + state["messages_research"])]}



def route_tools(state: State):
    return route_tools_by_messages(state.get("messages_research", []))



def print_node(state: State):
    print("Current state:")
    result = state.get("messages_research", [])[-1].content
    print(result)
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



research_graph = graph_builder.compile()


from langchain_core.tools import tool
from typing import Annotated, List




if __name__ == "__main__":

    def stream_graph_updates():
        for event in research_graph.stream(
            {
            "criteria": [
                "price",
                "accuracy of total sleep time",
                "accuracy of deep sleep stage",
                "IOS app insights and interpretability"
            ],

            "product": 
                {
                    "id": "fitbit-charge-6",
                    "name": "Fitbit Charge 6",
                    "USP": "GPS, Google, ECG",
                    "use_case": "Serious fitness tracking",
                    "other_info": "40+ modes, 7-day battery, $160"
                }
                
            }
            ):
            product_research = print("Event", event.keys())
            return product_research
            

    stream_graph_updates()