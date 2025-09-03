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
from agent.basic_tools import llm_with_tools, route_tools_by_messages, tools, BasicToolNode, tavily
from agent.llm_setup import get_llm
from agent.search_pattern import retry_llm_tool_call
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

class ToolCallAnalysis(BaseModel):
    insights: List[str] = Field(description="List of key insights extracted from the tool call")


set_debug(True)
#set_verbose(True)


class State(TypedDict):
    query: str
    criteria: List[str]
    product: ProductSimple
    ai_queries: Annotated[List[AIMessage],add_messages]
    tool_saved_info: Annotated[List[str],add_messages]
    tool_last_output: List[AIMessage]
    final_output: str


 
def chatbot_research(state: State):
    product = state.get("product", "")
    criteria = " ,".join(state.get("criteria", []))
    last_tool_call_output = state.get("tool_last_output", [None])[-1]
    tool_saved_info = state.get("tool_saved_info", [])
    ai_queries = state.get("ai_queries", [])
    ai_queries_short = [q.tool_calls[0].get("args", {}).get("query", "") for q in ai_queries]

    instructions_1 = """
    <SYSTEM>
    You are a hyper-skeptical, detail-obsessed research expert with a nose for digging up truth in a swamp of marketing hype. 
    You question everything, detect promotional fluff instantly, and obsess over the credibility of every source.

    You:
    - ANALYZE the last tool call to a search engine, take useful info and ignore the junk.
    - LOVE user reviews, expert breakdowns (especially on YouTube), and deep dives—not marketing blurbs.
    - NEVER trust subjective claims from sellers or retailers—only take objective data (e.g., dimensions, price).

    </SYSTEM>

    <INSTRUCTIONS>
    Your task is to read product information and criteria, and analyze the last tool call output to extract useful information.:

    - Identify key details about the product's performance, features, limitations, especially related to the list of criteria we are looking at.
    - Cross-reference findings with user reviews and expert opinions to validate claims.
    - Highlight any discrepancies or uncertainties in the information gathered.
    - WRITE like you’re texting a sharp best friend: quick, blunt, clear.

    Return your output using this format:
        List[str]

    </INSTRUCTIONS>

    <EXAMPLES>

    Example output 1 : 
    [
        "price $129 from official website",
        "no clinical validation for deep sleep accuracy found in seller claims"
    ],

    Example output 2:
     [
        "price: $159.95",
        "sleep score explained in Fitbit Premium, but breakdown info not on free version"
    ]
    </EXAMPLES>


    <INPUT>
    product: {product}
    criteria: {criteria}
    last_tool_call_arguments: {last_tool_call_arguments}
    last_tool_call_output: {last_tool_call_output}
    </INPUT>
    """



    instructions_2 = """
    <SYSTEM>
    You are a hyper-skeptical, detail-obsessed research expert with a nose for digging up truth in a swamp of marketing hype. 
    You question everything, detect promotional fluff instantly, and obsess over the credibility of every source.

    You:
    - ANALYZE every last tool call before doing anything—if it’s junk, you IGNORE it.
    - LOVE user reviews, expert breakdowns (especially on YouTube), and deep dives—not marketing blurbs.
    - NEVER trust subjective claims from sellers or retailers—only take objective data (e.g., dimensions, price).
    - FORMULATE surgical search queries to extract real-life performance, specific problems, and edge-case details.
    - DON’T stop at vague answers—search until the truth is nailed down or marked “unknown.”

    </SYSTEM>

    <INSTRUCTIONS>
    Your task is to evaluate each product based on these criteria:

    - Write surgical search queries to evaluate the product based on the criteria.
    - Use a MAX of 5 searches per product, ideally fewer.
    - START with obvious facts from seller pages (only if objective).
    - MOVE QUICKLY into digging for real-world evidence: reviews, Reddit threads, forums, expert opinions.
    - COMPARE products when possible, make judgments.
    - BE EXPLICIT about uncertainty—use "unknown" if unclear.
    - DO NOTHING if product model is missing or ambiguous—return empty.
    - DO NOT search for the information you already have, only search for the information you need.
    - DO NOT repeat queries in past_ai_queries.
    - New search query should be significantly different from the last ones in past_ai_queries.

    your output should be a searching tool call or nothing if you have enough information already.
    </INSTRUCTIONS>

    <INPUT>
    product: {product}
    criteria: {criteria}
    past_saved_info: {tool_saved_info}
    past_ai_queries: {ai_queries}
    </INPUT>
    """

    instructions_3 = """
    <SYSTEM>
    You are a hyper-skeptical, detail-obsessed research expert with a nose for digging up truth in a swamp of marketing hype. 
    You question everything, detect promotional fluff instantly, and obsess over the credibility of every source.

    You:
    - LOVE user reviews, expert breakdowns (especially on YouTube), and deep dives—not marketing blurbs.
    - NEVER trust subjective claims from sellers or retailers—only take objective data (e.g., dimensions, price).
    - WRITE like you’re texting a sharp best friend: quick, blunt, clear.
    </SYSTEM>

    <INSTRUCTIONS>
    Your task is to evaluate each product based on fixed criteria:

    - Look at all the facts we have gathered by searching the web and formulate them to criteria assessments.
    - If answer to a criteria is not found, return "unknown" for that criteria.

    Return your output using this format:

    {{
        "criteria_name": "answer to the criteria",
        "criteria_name_2": "answer to the criteria 2",
        ...
    }}
    

    Example:
    {{
    "price": "$99",
    "accuracy_of_total_sleep_time": "Good (within clinical acceptable range vs PSG)",
    "accuracy_of_deep_sleep_stage": "Poor (tends to overestimate, inconsistent vs medical grade)",
    "ios_app_insights_and_interpretability": "Premium required for sleep score breakdown, sleep profile analysis, restoration details"
    }}

    </INSTRUCTIONS>

    <INPUT>
    product: {product}
    criteria: {criteria}
    gathered_facts: {tool_saved_info}
    </INPUT>
    """


    if last_tool_call_output:
        print ( "analyzing last tool call output")

        formatted_instructions_1 = instructions_1.format(
            product=product,
            criteria=criteria,
            last_tool_call_arguments=json.dumps(ai_queries[-1].tool_calls[0].get("args", {}).get("query", "")),
            last_tool_call_output=last_tool_call_output.content if hasattr(last_tool_call_output, 'content') else str(last_tool_call_output),
        )

        result = get_llm("tool_call_analysis").with_structured_output(ToolCallAnalysis).invoke(
            formatted_instructions_1,
        )
        result_tool_call_analysis = result.insights
    else: 
        print ( "no last tool call output, skipping analysis")
        result_tool_call_analysis = []

    # Convert any message objects to strings for JSON serialization
    serializable_tool_info = []
    for item in tool_saved_info:
        if hasattr(item, 'content'):
            serializable_tool_info.append(item.content)
        else:
            serializable_tool_info.append(str(item))

    if len(ai_queries) < 5:
    
        formatted_instructions_2 = instructions_2.format(
            product=product,
            criteria=criteria,
            tool_saved_info=json.dumps(serializable_tool_info + result_tool_call_analysis),
            ai_queries=json.dumps([msg.tool_calls[0].get("args", {}).get("query", "") for msg in ai_queries]),
        )

        llm_with_bound_tools = get_llm("search_query_generation").bind_tools(tools, parallel_tool_calls=True)
        result_search_query = retry_llm_tool_call(llm_with_bound_tools, formatted_instructions_2)
    
    else:
        print("Skipping search query generation, reached maximum number of queries")
        result_search_query = None

    if result_search_query and result_search_query.tool_calls:

        print ( "we have a search query to run")
        return {
            "ai_queries": [result_search_query],
            "tool_saved_info": result_tool_call_analysis

        }
    
    else:
        print ( "no search query to run, formatting criteria evaluation")
        formatted_instructions_3 = instructions_3.format(
            product=product,
            criteria=criteria,
            tool_saved_info=json.dumps(serializable_tool_info + result_tool_call_analysis)
        )

        final_result = get_llm("search_result_analysis").invoke(
            formatted_instructions_3,
        )

        return {
            "final_output": final_result.content,
            "ai_queries": [AIMessage(content="no more searches")],
        }


def route_tools(state: State):
    ai_queries = state.get("ai_queries", [])
    print(f"[DEBUG] route_tools called with {len(ai_queries)} ai_queries")
    if ai_queries:
        print(f"[DEBUG] Last ai_query has tool_calls: {hasattr(ai_queries[-1], 'tool_calls') and len(ai_queries[-1].tool_calls) > 0}")
    
    result = route_tools_by_messages(ai_queries)
    print(f"[DEBUG] route_tools returning: {result}")
    return result



graph_builder = StateGraph(State)
tool_node_research = BasicToolNode(tools=[tavily], message_field_input="ai_queries", message_field_output="tool_last_output")

graph_builder.add_node("tool_node_research", tool_node_research)
graph_builder.add_node("chatbot_research", chatbot_research)



graph_builder.add_edge(START, "chatbot_research")

graph_builder.add_conditional_edges(
    "chatbot_research",
    route_tools,
    {"tools": "tool_node_research", END: END}
)
graph_builder.add_edge("tool_node_research", "chatbot_research")

research_graph = graph_builder.compile()


from langchain_core.tools import tool
from typing import Annotated, List




if __name__ == "__main__":

    for event in research_graph.stream(
        {
        "criteria": [
            "price",
 #          "accuracy of total sleep time",
 #          "accuracy of deep sleep stage",
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
        print("Event", event.keys())
        # Don't return here - let the loop continue!

        if "final_output" in event:
            print("Final output:", event["final_output"])
            print(research_graph.get_state())
            

