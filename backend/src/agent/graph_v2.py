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

from agent.state_V2 import OverallState, QueryBreakDown, QueryTips, Criteria, Queries
from agent.configuration import Configuration

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from langgraph.types import interrupt, Command


from typing import List
from pydantic import BaseModel, Field

from langgraph.checkpoint.memory import InMemorySaver
from agent.explore_agent_graph import graph_explore
from langchain.globals import set_debug, set_verbose
from langchain_core.rate_limiters import InMemoryRateLimiter

set_debug(True)
#set_verbose(True)

load_dotenv()

if os.getenv("GEMINI_API_KEY") is None:
    raise ValueError("GEMINI_API_KEY is not set")

# Used for Google Search API
#genai_client = Client(api_key=os.getenv("GEMINI_API_KEY"))

rate_limiter = InMemoryRateLimiter(
    requests_per_second=0.2,  # 1 request every 5 seconds
    check_every_n_seconds=0.1,
    max_bucket_size=1  # No burst requests
)

llm_llama3 = ChatGroq(
    model="llama3-8b-8192",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

llm_gemini = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=10,
    rate_limiter=rate_limiter,
)

#llm_gemini = llm_llama3

# Nodes
def pars_query(state: OverallState, config: RunnableConfig) -> OverallState:
    configurable = Configuration.from_runnable_config(config)

    structured_llm = llm_gemini.with_structured_output(QueryBreakDown)
    user_query = state.get("user_query") 
    query_parser_instructions = """
    I want to buy: {user_query} 
    Agent are gonna search step by step for it. 
    For that break down the query to these parts. 
    The Product, Use case, Conditions, and finally other is any other specification or tips, but only informative info not blant stuff like find best .
    Example: "Dummbles for strength training at home under 100 euros"
    The Product: "Dummbles"
    Use case: "strength training at home"
    Conditions: ["under 100 euros"]
    other: ""
    """
    formatted_prompt = query_parser_instructions.format(
        user_query=user_query
    )

    query_breakdown: QueryBreakDown = structured_llm.invoke(formatted_prompt)
    return {
            "query_breakdown": {
                "product": query_breakdown.product,
                "use_case": query_breakdown.use_case,
                "conditions": query_breakdown.conditions,
                "other": query_breakdown.other
            }
    }


# Nodes
def enrich_query(state: OverallState, config: RunnableConfig) -> OverallState:
    configurable = Configuration.from_runnable_config(config)

    structured_llm = llm_gemini.with_structured_output(QueryTips)
    user_query = state.get("user_query") 
    query_parser_instructions = """
        I want to buy something. Agent are gonna search step by step for it.
        For that reason about this extra information.

        Relevant search time: If very high tech, fast evolving field or AI based then last year is relevant, for stable stuff like dumbbells, leave empty "".

        Sources hint: Where do nerdy users of this product hang out? Reddit for apps, country-specific price comparison platforms like Geizhals, Hacker News for niche tech, Amazon for simple retail, and the best local source you can think of.

        How many products to show: When product is undifferentiated and depend highly on taste show 10, like shoes. If product is niche and really differentiated show 3, like e-reading device.

        Use cases and customer segments list: One product category serves many customer segments and many use cases, if not completely clear by user query list possible segments max 4 so the user can choose.

        Example query "best noise cancelling device"
        Relevant search time: 2 years
        Sources hint: reddit, wired, youtube,
        how many products to show: 4
        use cases and customer segments list: [Travelers, Office worker, Sleep aid, Factory Workers]

        Example query "Dumbbells for strength training at home under 100 euros up to 4 kilo"
        Relevant search time: None
        sources hint: amazon
        how many products to show: 6
        use cases and customer segments list: None

        what i want to buy is: {user_query}
    """
    formatted_prompt = query_parser_instructions.format(
        user_query=user_query
    )
    query_tips: QueryTips = structured_llm.invoke(formatted_prompt)

    return {
            "query_tips": {
                "timeframe": query_tips.timeframe,
                "sources": query_tips.sources,
                "how_many": query_tips.how_many,
                "potential_use_cases_to_clarify": query_tips.potential_use_cases_to_clarify
            }
    }

def should_ask_for_use_case(state: OverallState, config: RunnableConfig) -> bool:
    """Check if we need to ask the user for a use case based on the query tips."""
    use_cases = state.get("query_tips", {}).get("potential_use_cases_to_clarify", [])
    return len(use_cases) > 0

def human_ask_for_use_case(state: OverallState, config: RunnableConfig) -> dict:

    use_cases = state.get("query_tips", {}).get("potential_use_cases_to_clarify", [])
    question = "Please describe the use case for your product. You can choose from the following examples or provide your own:\n"
    for i, use_case in enumerate(use_cases):
        question += f"{i + 1}. {use_case}\n"

    answer = interrupt(question)

    instruction = """ given the question and the answer, return the selected use case. Just the use case, no other text.
    Question: {question}
    Answer: {answer}"""
    formatted_prompt = instruction.format(
        question=question,
        answer=answer
    )
    selected_use_case = llm_llama3.invoke(formatted_prompt).content.strip()

    print("Selected use case:", selected_use_case)

    return {
            "query_breakdown": {
                "product": state.get("query_breakdown", {}).get("product", ""),
                "use_case": selected_use_case,
                "conditions": state.get("query_breakdown", {}).get("conditions", ""),
                "other": state.get("query_breakdown", {}).get("other", "")
            }
    }


# Nodes
def find_criteria(state: OverallState, config: RunnableConfig) -> OverallState:
    configurable = Configuration.from_runnable_config(config)

    structured_llm = llm_gemini.with_structured_output(Criteria)

    product = state.get("query_breakdown", {}).get("product", "")
    use_case = state.get("query_breakdown", {}).get("use_case", "")
    conditions = state.get("query_breakdown", {}).get("conditions", "")


    instructions = """
        Give me the main criteria that matter the most when buying {product} for {use_case}, sort them by impact and how differentiated the top products are on it. 
        My extra conditions are {conditions}. 
        Max 5 criteria. But only very critical ones, do not just make a list. 
        this is not school. you will be rewarded by critical  thinking and quality of judgement, not number of words, what would a no bullshit expert say to his friend as advice.
        intentionally decide how specific or general the criteria should be.

        Task: I want to buy headphones for daily remote work calls in shared spaces, and I have these conditions: must be wireless, work with Mac, not over-ear
        Output:
        "buying_criteria": ["mic clarity in noisy environments", "latency with MacOS apps", "fit comfort for 4h+ wear", "stable Bluetooth connection", "battery life with mic use"]


        Task: I want to buy smart ring for stress tracking, and I have these conditions: must be comfortable to wear at night and discreet
        Output:
        "buying_criteria": ["HRV tracking accuracy", "real-time stress alerts", "sleep data quality", "ring size comfort", "battery life in continuous mode"]

        4.
        Task: I want to buy app-based budgeting tool for freelancer income tracking, and I have these conditions: needs EU bank integration and VAT tagging
        Output:
        "buying_criteria": ["multi-bank syncing reliability", "income/expense tagging flexibility", "VAT & invoice support", "report exports for tax filing", "mobile UX for quick edits"]

        5.
        Task: I want to buy robot vacuum for pet hair removal, and I have these conditions: must avoid poop, work with dark floors, auto-empty optional
        Output:
        "buying_criteria": ["hair pickup efficiency on hard floors", "object recognition and poop-avoidance", "suction vs noise tradeoff", "carpet edge transitions", "maintenance hassle"]

        6.
        Task: I want to buy note-taking app for daily idea capture and link-based research, and I have these conditions: must work offline, exportable to markdown
        Output:
        "buying_criteria": ["speed of quick capture", "linking and backlink UX", "offline stability", "search relevance", "export structure quality"]

       
        the current task is for:
        I want to buy {product} for {use_case}, and I have these conditions: {conditions}.

        now give list of "buying_criteria": 
    """
    formatted_prompt = instructions.format(
        product=product,
        use_case=use_case,
        conditions=conditions
    )
    llm_result: Criteria = structured_llm.invoke(formatted_prompt)

    try:
        result = llm_result.buying_criteria
    except AttributeError:
        result = llm_result.get("buying_criteria", [])

    return {
            "criteria": result + ["price", "brand credibility"], 
    }


# Nodes
def query_generator(state: OverallState, config: RunnableConfig) -> OverallState:
    configurable = Configuration.from_runnable_config(config)

    structured_llm = llm_gemini.with_structured_output(Queries)

    product = state.get("query_breakdown", {}).get("product", "")
    use_case = state.get("query_breakdown", {}).get("use_case", "")
    conditions = " ".join(state.get("query_breakdown", {}).get("conditions", ""))
    criteria = " ".join(state.get("criteria", {}))



    instructions = """
        I want to buy {product} for {use_case}, and I have these criteria in mind: {criteria}. And these conditions: {conditions}.

        Now I want to outsource the search to my friend. 
        For each criteria formulate a straight forward queries, the less general and the more clear the better. 
        The goal right now is not to go deep on each product but to discover diverse product each excelling at one of the criteria. 
        Avoid the best, the cheapest, top and all SEO optimized queries formulate queries that hit personal blogs, forums, neutral reviews, not promotional pages.  

        example input :  

        sleep tracking hardware and software for sleep optimization.can detect sleep stages, works with ios, with criteria: 
        "fixed and subscription price", "deep sleep accuracy", "REM sleep accuracy", "battery life", "convenience", "app and insights quality"

        queries: 
        
        how to track my sleep with app if i am on a budge?  
        are sleep tracking rings worth buying?  
        are high end sleep tracking rings worth the price?  
        mattress sensors for sleep tracking do they work?  
        does anyone use a sleep tracker that does not force a subscription?
        
        can rings detect deep sleep? 
        can apple watch detect deep sleep?
        can garmin watch detect deep sleep? 
        does detecting deep sleep help you sleep better? 
        can mattress sensors to detect deep sleep? 
        what have you learned from detecting your deep sleep over a year? 
        
        ring says i am in REM sleep just because i am sitting on couch? 
        does your watch over estimate your sleep? 
        mattress sensor for sleep detection how does it work? 
        
        how long is your battery lasting for watches with sleep tracking? 
        is battery a problem for ring sleep tracking? 
        
        my fitness ring wakes me up at night
        I can feel my sleep detection ring at night will i get used to it? 
        the most non evasive sleep detection? 
        
        what does sleep detector actually show? 
        what do you guys think about readiness score? 
        do i just feel tired because i can look at the readiness score? 
        how do you guys use the app to have better sleep? 
        i tracked my sleep now what? 
        what did you learn about sleep tracking app? 
        the app insights really changed my sleep? 


    the current task is for:
        I want to buy {product} for {use_case}, and I have these criteria in mind: {criteria}. And these conditions: {conditions}. out put maximum of {max_explore_queries} queries.
    """
    
    max_explore_queries=state.get("max_explore_queries", 10)
    formatted_prompt = instructions.format(
        product=product,
        use_case=use_case,
        conditions=conditions,
        criteria=criteria,
        max_explore_queries=max_explore_queries)
    
    result: Queries = structured_llm.invoke(formatted_prompt)

    return {
            "queries": result.get("queries", [])[:max_explore_queries]
    }



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
            "max_explore_products": state.get("max_explore_products", 15),
            "max_research_products": state.get("max_research_products", 5),
        }
    )

    return {
        "explored_products": exploration_state.get("products", []),
        "researched_products": exploration_state.get("research_results", []),
    }


def select_final_products(state: OverallState) -> OverallState:
    """
    Select the final products based on the researched products.
    This function is used to finalize the product selection process.
    """

    query_str = json.dumps(state.get("query_breakdown", {}), indent=0, default=str)

    products_full_info = merge_product_info(state) 

    products_string = json.dumps(products_full_info, indent=0, default=str)

    instructions = """ 
        You are an expert product researcher. 
       based on all research and price keep the products that have a competetiive advantage at least in one dimension. 
       aim for maximum of {max_products_to_show} options, but less is also fine. 
       something you would consider buying for yourself, do not be intellectual use common sense.
       return a list of product ids you would consider buying. just the list, nothing else, no explanation, no text, no markdown, just the list of ids.
       example output:
       ["id1", "id2", "id3"]

       here is the query you are trying to solve:
       {query}

       here is the list of products you should consider:
        {products_string}
       """
    
    max_products_to_show = state.get("max_research_products", 5)
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

    llm_gemini_structured = llm_gemini.with_structured_output(ProductSelection)
    results    = llm_gemini_structured.invoke(instructions)

    return {
        "selected_product_ids": results.products,
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



# Create our Agent Graph
builder = StateGraph(OverallState, config_schema=Configuration)

# Define the nodes we will cycle between
builder.add_node("pars_query", pars_query) 
builder.add_node("enrich_query", enrich_query)
builder.add_node("human_ask_for_use_case", human_ask_for_use_case)
builder.add_node("find_criteria", find_criteria)
builder.add_node("query_generator", query_generator)
builder.add_node("call_product_search_graph", call_product_search_graph)
builder.add_node("select_final_products", select_final_products)


# Set the entrypoint as `planner`
builder.add_edge(START, "pars_query")
builder.add_edge("pars_query", "enrich_query")

builder.add_conditional_edges(
    "enrich_query",
    should_ask_for_use_case,
    {
        True: "human_ask_for_use_case",
        False: "find_criteria"
    }
)
builder.add_edge("human_ask_for_use_case", "find_criteria")
builder.add_edge("find_criteria", "query_generator")
builder.add_edge("query_generator", "call_product_search_graph")
builder.add_edge("call_product_search_graph", "select_final_products")
builder.add_edge("select_final_products", END)


checkpointer = InMemorySaver()

graph = builder.compile(name="product-search-agent", checkpointer=checkpointer)



if __name__ == "__main__":
    # Test the graph with a sample state
    initial_state = OverallState(
        user_query="Find the best smart home devices",
        max_explore_products=3,
        max_research_products=1,
        max_explore_queries=1,
    )

    config = {"configurable": {"thread_id": "some_id"}}
    result_state = graph.invoke(initial_state, config=config)

    result_state = graph.invoke(Command(resume="2"), config=config)
    print(json.dumps(result_state, indent=2, default=str))