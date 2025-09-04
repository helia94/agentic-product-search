from typing import List
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from agent.state_V2 import OverallState, QueryBreakDown, QueryTips, Criteria
from agent.configuration import Configuration
from agent.llm_setup import get_llm
from agent.node_progress import track_node_progress


@track_node_progress("pars_query")
def pars_query(state: OverallState, config: RunnableConfig) -> OverallState:
    configurable = Configuration.from_runnable_config(config)

    structured_llm = get_llm("query_breakdown").with_structured_output(QueryBreakDown)
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


def enrich_query(state: OverallState, config: RunnableConfig) -> OverallState:
    configurable = Configuration.from_runnable_config(config)

    structured_llm = get_llm("query_tips").with_structured_output(QueryTips)
    user_query = state.get("user_query") 
    query_parser_instructions = """
        I want to buy something. Agent are gonna search step by step for it.
        For that reason about this extra information.

        Relevant search time: If very high tech, fast evolving field or AI based then last year is relevant, for stable stuff like dumbbells, leave empty "".

        Sources hint: Where do nerdy users of this product hang out? Reddit for apps, country-specific price comparison platforms like Geizhals, Hacker News for niche tech, Amazon for simple retail, and the best local source you can think of.

        How many products to show: When product is undifferentiated and depend highly on taste show 10, like shoes. If product is niche and really differentiated show 3, like e-reading device.

        Use cases and customer segments list: One product category serves many customer segments and many use cases, if not completely clear by user query list possible segments max 4 so the user can choose.

        offer usecases only if you think is really unclear and customer segments need different options. Do not be unreasonable/annoying in your suggestions. only if it helps the search significantly. 

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
    # Check if we already have a human answer to process
    if state.get("human_answer"):
        answer = state.get("human_answer")
        question = state.get("human_question", "")
        
        instruction = """ given the question and the answer, return the selected use case. Just the use case, no other text.
        Question: {question}
        Answer: {answer}"""
        formatted_prompt = instruction.format(
            question=question,
            answer=answer
        )
        selected_use_case = get_llm("use_case_selection").invoke(formatted_prompt).content.strip()

        print("Selected use case:", selected_use_case)

        return {
            "query_breakdown": {
                "product": state.get("query_breakdown", {}).get("product", ""),
                "use_case": selected_use_case,
                "conditions": state.get("query_breakdown", {}).get("conditions", ""),
                "other": state.get("query_breakdown", {}).get("other", "")
            },
            "human_question": None,
            "human_answer": None,
            "awaiting_human": False
        }
    
    # First time - prepare question for human
    use_cases = state.get("query_tips", {}).get("potential_use_cases_to_clarify", [])
    question = "Please describe the use case for your product. You can choose from the following examples or provide your own:\n"
    for i, use_case in enumerate(use_cases):
        question += f"{i + 1}. {use_case}\n"

    return {
        "human_question": question,
        "awaiting_human": True
    }


def find_criteria(state: OverallState, config: RunnableConfig) -> OverallState:
    configurable = Configuration.from_runnable_config(config)

    structured_llm = get_llm("buying_criteria").with_structured_output(Criteria)

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