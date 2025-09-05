
from agent.configuration.llm_setup import get_llm
from langchain_tavily import TavilySearch
from agent.utils.tool_orchestrator import create_tool_node, create_tool_router
from langchain_core.tools import tool
from langgraph.cache.memory import InMemoryCache
from langgraph.types import default_cache_key

# Use centralized LLM configuration
# Individual LLM instances can be fetched as needed

tavily = TavilySearch(
    max_results=2,  # 10
    topic="general",
)

# Simple in-memory cache for tool results
_tool_cache = InMemoryCache()


@tool
def tavily_cached(query: str):
    """Search Tavily with caching to avoid duplicate API calls."""
    key = default_cache_key(query)
    full_key = ("tavily_search", key)
    cached = _tool_cache.get([full_key])
    if full_key in cached:
        return cached[full_key]
    result = tavily.invoke(query)
    _tool_cache.set({full_key: (result, None)})
    return result


tools = [tavily_cached]

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