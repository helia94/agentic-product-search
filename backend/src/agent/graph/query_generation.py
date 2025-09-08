from langchain_core.runnables import RunnableConfig

from agent.graph.state_V2 import OverallState, Queries
from agent.configuration import Configuration
from agent.configuration.llm_setup import get_llm
from agent.configuration.search_limits import SEARCH_LIMITS
from agent.tracing.node_progress import track_node_progress

@track_node_progress("query_generator")
def query_generator(state: OverallState, config: RunnableConfig) -> OverallState:
    configurable = Configuration.from_runnable_config(config)

    structured_llm = get_llm("query_generation").with_structured_output(Queries)

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
    
    max_explore_queries = SEARCH_LIMITS.max_explore_queries
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