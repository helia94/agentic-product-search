
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from langchain_core.messages import ToolMessage
from langgraph.graph import StateGraph, START, END
import json


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


class BasicToolNode:
    """A node that runs the tools requested in the last AIMessage."""

    def __init__(self, tools: list, message_field_input: str, message_field_output) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}
        self.message_field_input = message_field_input
        self.message_field_output = message_field_output

    
    def __call__(self, inputs: dict):
        print("Running BasicToolNode")
        if messages := inputs.get(self.message_field_input, []):
            message = messages[-1]
        else:
            raise ValueError("No message found in input")
        outputs = []

        for tool_call in message.tool_calls:
            print("Running tool call:", tool_call["name"])
            tool_result = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )
            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )

        return {self.message_field_output: outputs}
    

def route_tools_by_messages(
    messages
):
    """
    Use in the conditional_edge to route to the ToolNode if the last message
    has tool calls. Otherwise, route to the end.
    """
    list_of_ms = []
    if messages :
        list_of_ms += [messages[-1]]

    for ai_message in list_of_ms:
        if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
            return "tools"
    return END