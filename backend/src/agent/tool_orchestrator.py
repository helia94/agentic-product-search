"""
Simple Tool Utilities for LangGraph

Minimal, focused tool execution and routing.
"""

from typing import Dict, List, Any
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END
import json


def create_tool_node(tools: List[BaseTool], input_field: str = "ai_queries", output_field: str = "tool_last_output"):
    """Create a tool execution node"""
    tools_by_name = {tool.name: tool for tool in tools}
    
    def tool_node(state: Dict[str, Any]) -> Dict[str, Any]:
        messages = state.get(input_field, [])
        if not messages:
            return {output_field: []}
        
        last_message = messages[-1]
        if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
            return {output_field: []}
        
        tool_messages = []
        for tool_call in last_message.tool_calls:
            tool_result = tools_by_name[tool_call["name"]].invoke(tool_call["args"])
            tool_messages.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {output_field: tool_messages}
    
    return tool_node


def create_tool_router(input_field: str = "ai_queries", tool_node_name: str = "tools"):
    """Create a routing function for conditional edges"""
    def router(state: Dict[str, Any]) -> str:
        messages = state.get(input_field, [])
        if not messages:
            return END
        
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return tool_node_name
        return END
    
    return router


class SimpleToolOrchestrator:
    """Simple tool setup for agents"""
    def __init__(self, tools: List[BaseTool], input_field: str = "ai_queries", output_field: str = "tool_last_output"):
        self.tools = tools
        self.input_field = input_field
        self.output_field = output_field
    
    def bind_tools_to_llm(self, llm):
        return llm.bind_tools(self.tools)
    
    def tool_node(self):
        return create_tool_node(self.tools, self.input_field, self.output_field)
    
    def router(self, tool_node_name: str = "tools"):
        return create_tool_router(self.input_field, tool_node_name)


# Legacy compatibility
def create_basic_tool_node(tools, input_field, output_field):
    return create_tool_node(tools, input_field, output_field)

AgentToolOrchestrator = SimpleToolOrchestrator  # Alias for backward compatibility