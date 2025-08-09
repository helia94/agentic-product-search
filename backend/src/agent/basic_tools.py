
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from agent.tool_orchestrator import create_tool_node, create_tool_router


llm_gemini = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-lite",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=10,
)

llm_llama3 = ChatGroq(
    model="llama3-8b-8192",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)


#llm_gemini = llm_llama3

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
llm_with_tools = llm_gemini.bind_tools(tools)

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