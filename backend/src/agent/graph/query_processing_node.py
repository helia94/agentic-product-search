from langchain_core.runnables import RunnableConfig
from agent.graph.state_V2 import OverallState, QueryBreakDown, QueryTips, Criteria
from agent.configuration import Configuration
from agent.configuration.llm_setup import get_llm
from agent.tracing.node_progress import track_node_progress
from agent.prompts.query_processing.query_parser_instructions import QUERY_PARSER_PROMPT
from agent.prompts.query_processing.query_enrichment_instructions import QUERY_ENRICHMENT_PROMPT
from agent.prompts.query_processing.use_case_selection_instruction import USE_CASE_SELECTION_PROMPT
from agent.prompts.query_processing.criteria_instructions import CRITERIA_PROMPT


@track_node_progress("pars_query")
def pars_query(state: OverallState, config: RunnableConfig) -> OverallState:
    configurable = Configuration.from_runnable_config(config)

    structured_llm = get_llm("query_breakdown").with_structured_output(QueryBreakDown)
    user_query = state.get("user_query") 
    query_parser_instructions = QUERY_PARSER_PROMPT
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


@track_node_progress("enrich_query")
def enrich_query(state: OverallState, config: RunnableConfig) -> OverallState:
    configurable = Configuration.from_runnable_config(config)

    structured_llm = get_llm("query_tips").with_structured_output(QueryTips)
    user_query = state.get("user_query") 
    query_parser_instructions = QUERY_ENRICHMENT_PROMPT,
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


@track_node_progress("human_ask_for_use_case")
def human_ask_for_use_case(state: OverallState, config: RunnableConfig) -> dict:
    # Check if we already have a human answer to process
    if state.get("human_answer"):
        answer = state.get("human_answer")
        question = state.get("human_question", "")
        
        instruction = USE_CASE_SELECTION_PROMPT
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


@track_node_progress("find_criteria")
def find_criteria(state: OverallState, config: RunnableConfig) -> OverallState:
    configurable = Configuration.from_runnable_config(config)

    structured_llm = get_llm("buying_criteria").with_structured_output(Criteria)

    product = state.get("query_breakdown", {}).get("product", "")
    use_case = state.get("query_breakdown", {}).get("use_case", "")
    conditions = state.get("query_breakdown", {}).get("conditions", "")

    instructions = CRITERIA_PROMPT
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