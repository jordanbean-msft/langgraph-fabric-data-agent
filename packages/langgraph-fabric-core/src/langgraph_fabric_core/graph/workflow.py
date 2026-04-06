"""LangGraph definition for the MCP-enabled agent."""

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition


class AgentState(TypedDict):
    """State object passed across graph nodes."""

    messages: Annotated[list[BaseMessage], add_messages]
    auth_mode: str
    user_id: str
    mcp_user_tokens: dict[str, str]


def build_graph(chat_model, tools):
    """Create a tool-enabled ReAct-like graph."""
    tool_calling_llm = chat_model.bind_tools(tools) if tools else chat_model

    async def assistant(state: AgentState):
        response = await tool_calling_llm.ainvoke(state["messages"])
        return {"messages": [response]}

    async def finalize(state: AgentState):
        user_prompt = ""
        tool_outputs: list[str] = []

        for message in state["messages"]:
            if isinstance(message, HumanMessage):
                user_prompt = str(message.content)
            elif isinstance(message, ToolMessage):
                tool_outputs.append(str(message.content))

        synthesized_prompt = (
            "You are a helpful analytics assistant. "
            "Use the MCP tool result below to answer the user's request. "
            "Do not mention internal tool calls. If the result is empty or indicates an error, "
            "explain that clearly and suggest a next step.\n\n"
            f"User request:\n{user_prompt}\n\n"
            f"MCP tool result:\n{'\n\n'.join(tool_outputs).strip()}"
        )

        response = await chat_model.ainvoke([HumanMessage(content=synthesized_prompt)])
        return {"messages": [response]}

    workflow = StateGraph(AgentState)
    workflow.add_node("assistant", assistant)
    workflow.set_entry_point("assistant")

    if not tools:
        workflow.add_edge("assistant", END)
        return workflow.compile()

    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("finalize", finalize)
    workflow.add_conditional_edges("assistant", tools_condition, {"tools": "tools", "__end__": END})
    workflow.add_edge("tools", "finalize")
    workflow.add_edge("finalize", END)
    return workflow.compile()
