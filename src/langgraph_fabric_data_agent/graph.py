"""LangGraph definition for the Fabric-enabled agent."""

from typing import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition


class AgentState(TypedDict):
    """State object passed across graph nodes."""

    messages: list[BaseMessage]
    auth_mode: str
    user_id: str
    fabric_user_token: str | None


def build_graph(chat_model, fabric_tool):
    """Create a tool-enabled ReAct-like graph."""
    llm = chat_model.bind_tools([fabric_tool])

    async def assistant(state: AgentState):
        response = await llm.ainvoke(state["messages"])
        return {"messages": [response]}

    workflow = StateGraph(AgentState)
    workflow.add_node("assistant", assistant)
    workflow.add_node("tools", ToolNode([fabric_tool]))
    workflow.set_entry_point("assistant")
    workflow.add_conditional_edges("assistant", tools_condition, {"tools": "tools", "__end__": END})
    workflow.add_edge("tools", "assistant")
    return workflow.compile()
