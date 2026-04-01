"""LangGraph definition for the Fabric-enabled agent."""

from typing import TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
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
    tool_calling_llm = chat_model.bind_tools([fabric_tool])

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
            "Use the Fabric Data Agent result below to answer the user's request. "
            "Do not mention internal tool calls. If the result is empty or indicates an error, "
            "explain that clearly and suggest a next step.\n\n"
            f"User request:\n{user_prompt}\n\n"
            f"Fabric Data Agent result:\n{'\n\n'.join(tool_outputs).strip()}"
        )

        response = await chat_model.ainvoke([HumanMessage(content=synthesized_prompt)])
        return {"messages": [response]}

    workflow = StateGraph(AgentState)
    workflow.add_node("assistant", assistant)
    workflow.add_node("tools", ToolNode([fabric_tool]))
    workflow.add_node("finalize", finalize)
    workflow.set_entry_point("assistant")
    workflow.add_conditional_edges("assistant", tools_condition, {"tools": "tools", "__end__": END})
    workflow.add_edge("tools", "finalize")
    workflow.add_edge("finalize", END)
    return workflow.compile()
