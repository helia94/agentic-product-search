"""
Simple Tool Utilities for LangGraph

Minimal, focused tool execution and routing.
"""

from typing import Dict, List, Any
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END
from langgraph.prebuilt import ToolNode
import json


def create_tool_node(tools: List[BaseTool], input_field: str = "ai_queries", output_field: str = "tool_last_output"):
    """Create a tool execution node using LangGraph's built-in ToolNode for parallel execution"""
    
    # Use LangGraph's built-in ToolNode which automatically executes tools in parallel
    langgraph_tool_node = ToolNode(tools)
    
    def tool_node_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
        """Wrapper to adapt LangGraph ToolNode to our state structure"""
        messages = state.get(input_field, [])
        if not messages:
            return {output_field: []}
        
        last_message = messages[-1]
        if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
            return {output_field: []}
        
        # Log parallel execution info
        if len(last_message.tool_calls) > 1:
            print(f"LangGraph ToolNode executing {len(last_message.tool_calls)} tool calls in parallel")
        
        # Create input in the format expected by ToolNode (MessagesState)
        tool_node_input = {"messages": [last_message]}
        
        # Execute using LangGraph's built-in parallel tool execution
        result = langgraph_tool_node.invoke(tool_node_input)
        
        # Extract the tool messages from the result
        tool_messages = []
        for msg in result.get("messages", []):
            if hasattr(msg, 'type') and msg.type == 'tool':
                tool_messages.append(msg)
        
        return {output_field: tool_messages}
    
    return tool_node_wrapper


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
        return llm.bind_tools(self.tools, parallel_tool_calls=True)
    
    def tool_node(self):
        return create_tool_node(self.tools, self.input_field, self.output_field)
    
    def router(self, tool_node_name: str = "tools"):
        return create_tool_router(self.input_field, tool_node_name)


# Legacy compatibility
def create_basic_tool_node(tools, input_field, output_field):
    return create_tool_node(tools, input_field, output_field)

AgentToolOrchestrator = SimpleToolOrchestrator  # Alias for backward compatibility