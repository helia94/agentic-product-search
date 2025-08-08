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
from typing import Optional
from pydantic import BaseModel, Field

#set_debug(True)
#set_verbose(True)

class ResearchAgentOutput(BaseModel):
    usable_info_from_last_tool_call: Optional[List[str]] = Field(
        default=None,
        description="List of usable information extracted from the last tool call. Always presented together with field next_tool_call.",
    )
    next_tool_call: Optional[AIMessage] = Field(
        default=None,
        description="Message containing the next tool call to be made.")
    final_output: Optional[AIMessage]= Field(
        default=None,
        description="Final output message after all tool calls have been processed. If this field is set the other fields should not be set.",
    )


class State(TypedDict):
    query: str
    criteria: List[str]
    product: ProductSimple
    ai_queries: Annotated[List[AIMessage],add_messages]
    tool_saved_info: Annotated[List[str],add_messages]
    tool_last_output: List[AIMessage]
    final_output: Optional[AIMessage]


 
def chatbot_research(state: State):
    product = state.get("product", "")
    criteria = " ,".join(state.get("criteria", []))

    instructions = """
    <SYSTEM>
    You are a hyper-skeptical, detail-obsessed research expert with a nose for digging up truth in a swamp of marketing hype. 
    You question everything, detect promotional fluff instantly, and obsess over the credibility of every source.

    You:
    - ANALYZE every last tool call before doing anything—if it’s junk, you IGNORE it.
    - LOVE user reviews, expert breakdowns (especially on YouTube), and deep dives—not marketing blurbs.
    - NEVER trust subjective claims from sellers or retailers—only take objective data (e.g., dimensions, price).
    - FORMULATE surgical search queries to extract real-life performance, specific problems, and edge-case details.
    - DON’T stop at vague answers—search until the truth is nailed down or marked “unknown.”
    - WRITE like you’re texting a sharp best friend: quick, blunt, clear.

    </SYSTEM>

    <INSTRUCTIONS>
    Your task is to evaluate each product based on these criteria:

    - Use a MAX of 5 searches per product, ideally fewer.
    - START with obvious facts from seller pages (only if objective).
    - MOVE QUICKLY into digging for real-world evidence: reviews, Reddit threads, forums, expert opinions.
    - COMPARE products when possible, make judgments.
    - BE EXPLICIT about uncertainty—use "unknown" if unclear.
    - DO NOTHING if product model is missing or ambiguous—return empty.

    Return your output using this format:

    class ResearchAgentOutput:
        usable_info_from_last_tool_call: Optional[List[str]]
        next_tool_call: Optional[AIMessage]
        final_output: Optional[AIMessage]

    ⚠️IMPORTANT: If you set final_output, DO NOT set next_tool_call or usable_info_from_last_tool_call.
    If you set next_tool_call, DO NOT set final_output.

    Examples:

    Example 1 – with next_tool_call:
    {
    "usable_info_from_last_tool_call": [
        "price: $129 from official website",
        "no clinical validation for deep sleep accuracy found in seller claims"
    ],
    "next_tool_call": {
        "tool_name": "search",
        "tool_args": "Oura Ring Gen3 deep sleep accuracy site:reddit.com OR site:sleepfoundation.org"
    },
    "final_output": null
    }

    Example 2 – with next_tool_call:
    {
    "usable_info_from_last_tool_call": [
        "Product is Fitbit Charge 6",
        "price: $159.95",
        "sleep score explained in Fitbit Premium, but breakdown info not on free version"
    ],
    "next_tool_call": {
        "tool_name": "search",
        "tool_args": "Fitbit Charge 6 accuracy of deep sleep stage reddit OR site:pubmed.ncbi.nlm.nih.gov"
    },
    "final_output": null
    }

    Example 3 – with final_output:
    {
    "usable_info_from_last_tool_call": null,
    "next_tool_call": null,
    "final_output": {
        "price": "$99",
        "accuracy_of_total_sleep_time": "Good (within clinical acceptable range vs PSG)",
        "accuracy_of_deep_sleep_stage": "Poor (tends to overestimate, inconsistent vs medical grade)",
        "ios_app_insights_and_interpretability": "Premium required for sleep score breakdown, sleep profile analysis, restoration details"
        }
    }
    </INSTRUCTIONS>

    <INPUT>
    product: {product}
    criteria: {criteria}
    last_tool_call_output: {last_tool_call_output}
    tool_saved_info: {tool_saved_info}
    ai_queries: {ai_queries}
    </INPUT>
    """


    formatted_instructions = instructions.format(
        product=product,
        criteria=criteria,
        last_tool_call_output=json.dumps(state.get("tool_last_output", ["none so far"])[-1]),
        tool_saved_info=json.dumps(state.get("tool_saved_info", [])),
        ai_queries=json.dumps(state.get("ai_queries", [])),
    )

    structured_llm = llm_with_tools.with_structured_output(ResearchAgentOutput)
    response = structured_llm.invoke(formatted_instructions)

    if response.final_output:
        return { 
            "final_output" : response.final_output,
            "ai_queries": AIMessage(
                content="Final output received, no further tool calls needed.",
                tool_calls=[],
            )
                }
    elif response.next_tool_call and response.usable_info_from_last_tool_call:
        return { 
            "ai_queries": response.next_tool_call,
            "tool_saved_info": response.usable_info_from_last_tool_call,
            }
    else:
        raise ValueError("LLM response is missing both final_output and next_tool_call with usable_info_from_last_tool_call.")

def route_tools(state: State):
    return route_tools_by_messages(state.get("ai_queries", []))



def print_node(state: State):
    print("Current state:")
    result = state.get("messages_research", [])[-1].content
    print(result)
    return state

graph_builder = StateGraph(State)
tool_node_research = BasicToolNode(tools=[tavily], message_field_input="ai_queries", message_field_output="tool_last_output")

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