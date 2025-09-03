
from agent.llm_setup import get_llm
from langchain_tavily import TavilySearch
from langchain_core.rate_limiters import InMemoryRateLimiter
from agent.tool_orchestrator import create_tool_node, create_tool_router
from langchain_google_vertexai import ChatVertexAI

import os

# Rate limiter for Gemini API to avoid rate limits
rate_limiter = InMemoryRateLimiter(
    requests_per_second=0.2,  # 1 request every 5 seconds
    check_every_n_seconds=0.1,
    max_bucket_size=1  # No burst requests
)

# Use centralized LLM configuration
llm_gemini = get_llm("search_query_generation")
llm_llama3 = get_llm("use_case_selection")

tavily = TavilySearch(
    max_results=2, #10
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
llm_with_tools = get_llm("pattern_tool_calls").bind_tools(tools, parallel_tool_calls=True)

# Simple wrappers
def BasicToolNode(tools, message_field_input, message_field_output):
    return create_tool_node(tools, message_field_input, message_field_output)

def route_tools_by_messages(messages, end_node="END"):
    from langgraph.graph import END as LANGGRAPH_END
    
    if not messages:
        return end_node if end_node != "END" else LANGGRAPH_END
        
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    return end_node if end_node != "END" else LANGGRAPH_END