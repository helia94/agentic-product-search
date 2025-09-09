from langchain_core.runnables import RunnableConfig

from agent.graph.state_V2 import OverallState, Queries
from agent.configuration import Configuration
from agent.configuration.llm_setup import get_llm
from agent.tracing.node_progress import track_node_progress
from agent.prompts.generation.query_generation_instructions import QUERY_GENERATION_PROMPT

@track_node_progress("query_generator")
def query_generator(state: OverallState, config: RunnableConfig) -> OverallState:
    configurable = Configuration.from_runnable_config(config)

    structured_llm = get_llm("query_generation").with_structured_output(Queries)

    product = state.get("query_breakdown", {}).get("product", "")
    use_case = state.get("query_breakdown", {}).get("use_case", "")
    conditions = " ".join(state.get("query_breakdown", {}).get("conditions", ""))
    criteria = " ".join(state.get("criteria", {}))

    instructions = QUERY_GENERATION_PROMPT
    
    max_explore_queries = state.get("search_limits").max_explore_queries
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