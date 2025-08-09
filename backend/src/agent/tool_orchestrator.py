"""
Enhanced Tool Orchestration System

Provides clean, reusable patterns for tool calling in LangGraph agents.
Separates tool configuration, execution, and routing logic.
"""

from typing import Dict, List, Any, Callable, Optional, Protocol
from abc import ABC, abstractmethod
from langchain_core.messages import ToolMessage, AIMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END
import json


class StateFieldAccessor(Protocol):
    """Protocol for accessing state fields dynamically"""
    def get_input_messages(self, state: Dict[str, Any]) -> List[AIMessage]:
        ...
    
    def format_output(self, tool_messages: List[ToolMessage]) -> Dict[str, Any]:
        ...


class DefaultStateAccessor:
    """Default implementation for common state field patterns"""
    
    def __init__(self, input_field: str = "ai_queries", output_field: str = "tool_last_output"):
        self.input_field = input_field
        self.output_field = output_field
    
    def get_input_messages(self, state: Dict[str, Any]) -> List[AIMessage]:
        return state.get(self.input_field, [])
    
    def format_output(self, tool_messages: List[ToolMessage]) -> Dict[str, Any]:
        return {self.output_field: tool_messages}


class ToolExecutor:
    """Handles tool execution with configurable state access"""
    
    def __init__(self, tools: List[BaseTool], state_accessor: Optional[StateFieldAccessor] = None):
        self.tools_by_name = {tool.name: tool for tool in tools}
        self.state_accessor = state_accessor or DefaultStateAccessor()
    
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tools based on the last AI message"""
        messages = self.state_accessor.get_input_messages(state)
        
        if not messages:
            raise ValueError(f"No messages found in state for field: {self.state_accessor.input_field}")
        
        last_message = messages[-1]
        if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
            return self.state_accessor.format_output([])
        
        tool_messages = []
        for tool_call in last_message.tool_calls:
            if tool_call["name"] not in self.tools_by_name:
                raise ValueError(f"Tool '{tool_call['name']}' not found in available tools")
            
            tool_result = self.tools_by_name[tool_call["name"]].invoke(tool_call["args"])
            tool_messages.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        
        return self.state_accessor.format_output(tool_messages)


class ToolRouter:
    """Handles routing logic for tool execution"""
    
    def __init__(self, state_accessor: Optional[StateFieldAccessor] = None, end_node: str = END):
        self.state_accessor = state_accessor or DefaultStateAccessor()
        self.end_node = end_node
    
    def route(self, state: Dict[str, Any], tool_node_name: str = "tools") -> str:
        """Route to tool node if tools are called, otherwise to end"""
        messages = self.state_accessor.get_input_messages(state)
        
        if not messages:
            return self.end_node
        
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return tool_node_name
        
        return self.end_node


class AgentToolOrchestrator:
    """Complete tool orchestration for an agent"""
    
    def __init__(
        self, 
        tools: List[BaseTool],
        state_accessor: Optional[StateFieldAccessor] = None,
        llm_with_tools: Optional[Any] = None
    ):
        self.tools = tools
        self.state_accessor = state_accessor or DefaultStateAccessor()
        self.executor = ToolExecutor(tools, self.state_accessor)
        self.router = ToolRouter(self.state_accessor)
        self.llm_with_tools = llm_with_tools
    
    def get_llm_with_tools(self, base_llm):
        """Get LLM bound with tools"""
        if self.llm_with_tools:
            return self.llm_with_tools
        return base_llm.bind_tools(self.tools)
    
    def create_tool_node(self):
        """Create a tool execution node for LangGraph"""
        return self.executor.execute
    
    def create_router_function(self, tool_node_name: str = "tools"):
        """Create a routing function for LangGraph conditional edges"""
        return lambda state: self.router.route(state, tool_node_name)


# Convenience functions for backward compatibility
def create_basic_tool_node(tools: List[BaseTool], input_field: str, output_field: str):
    """Create a basic tool node with specified field names"""
    state_accessor = DefaultStateAccessor(input_field, output_field)
    executor = ToolExecutor(tools, state_accessor)
    return executor.execute


def create_message_router(input_field: str = "ai_queries", end_node: str = END):
    """Create a message-based router"""
    state_accessor = DefaultStateAccessor(input_field)
    router = ToolRouter(state_accessor, end_node)
    return router.route