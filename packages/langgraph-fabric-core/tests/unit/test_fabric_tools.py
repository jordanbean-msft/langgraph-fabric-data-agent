from unittest.mock import AsyncMock

import pytest
from langgraph_fabric_core.mcp.tools import _resolve_query_argument_name, build_mcp_tool


class _Server:
    name = "fabric"
    description = "Fabric MCP"
    scope = "https://api.fabric.microsoft.com/.default"


@pytest.mark.asyncio
async def test_build_mcp_tool_invokes_mcp_tool_with_state_auth_context() -> None:
    client = AsyncMock()
    client.server_config = _Server()
    client.list_tools.return_value = [
        {
            "name": "fabric_query",
            "inputSchema": {
                "type": "object",
                "properties": {"userQuestion": {"type": "string"}},
                "required": ["userQuestion"],
            },
        }
    ]
    client.call_tool.return_value = "customer results"

    tool = build_mcp_tool(client)
    state = {
        "auth_mode": "local",
        "user_id": "console-user",
        "mcp_user_tokens": {},
    }

    assert tool.coroutine is not None
    result = await tool.coroutine(query="top 5 customers", state=state)

    assert result == "customer results"
    client.initialize.assert_awaited_once()
    client.list_tools.assert_awaited_once()
    client.call_tool.assert_awaited_once_with(
        tool_name="fabric_query",
        arguments={"userQuestion": "top 5 customers"},
        auth_context=client.call_tool.await_args.kwargs["auth_context"],
    )
    auth_context = client.call_tool.await_args.kwargs["auth_context"]
    assert auth_context.mode == "local"
    assert auth_context.user_id == "console-user"
    assert auth_context.scope == _Server.scope
    assert auth_context.user_token is None


@pytest.mark.asyncio
async def test_build_mcp_tool_defaults_tool_name_when_mcp_list_is_empty() -> None:
    client = AsyncMock()
    client.server_config = _Server()
    client.list_tools.return_value = []
    client.call_tool.return_value = "ok"

    tool = build_mcp_tool(client)
    state = {
        "auth_mode": "m365",
        "user_id": "m365-user",
        "mcp_user_tokens": {"fabric": "token-123"},
    }

    assert tool.coroutine is not None
    await tool.coroutine(query="sales", state=state)

    client.call_tool.assert_awaited_once_with(
        tool_name="query",
        arguments={"query": "sales"},
        auth_context=client.call_tool.await_args.kwargs["auth_context"],
    )
    auth_context = client.call_tool.await_args.kwargs["auth_context"]
    assert auth_context.mode == "m365"
    assert auth_context.user_id == "m365-user"
    assert auth_context.user_token == "token-123"


@pytest.mark.asyncio
async def test_build_mcp_tool_returns_error_message_on_mcp_failure() -> None:
    client = AsyncMock()
    client.server_config = _Server()
    client.list_tools.return_value = [
        {"name": "fabric_query", "inputSchema": {"properties": {"query": {}}}}
    ]
    client.call_tool.side_effect = RuntimeError("upstream failure")

    tool = build_mcp_tool(client)
    state = {
        "auth_mode": "local",
        "user_id": "console-user",
        "mcp_user_tokens": {},
    }

    assert tool.coroutine is not None
    result = await tool.coroutine(query="sales", state=state)

    assert "MCP server 'fabric' query failed:" in result
    assert "upstream failure" in result


# ---------------------------------------------------------------------------
# _resolve_query_argument_name edge cases
# ---------------------------------------------------------------------------


def test_resolve_query_argument_name_returns_preferred_name_userquestion() -> None:
    tool_def = {"inputSchema": {"properties": {"userQuestion": {}, "other": {}}}}
    assert _resolve_query_argument_name(tool_def) == "userQuestion"


def test_resolve_query_argument_name_returns_preferred_name_query() -> None:
    tool_def = {"inputSchema": {"properties": {"query": {}, "extra": {}}}}
    assert _resolve_query_argument_name(tool_def) == "query"


def test_resolve_query_argument_name_returns_preferred_name_prompt() -> None:
    tool_def = {"inputSchema": {"properties": {"prompt": {}}}}
    assert _resolve_query_argument_name(tool_def) == "prompt"


def test_resolve_query_argument_name_returns_preferred_name_question() -> None:
    tool_def = {"inputSchema": {"properties": {"question": {}}}}
    assert _resolve_query_argument_name(tool_def) == "question"


def test_resolve_query_argument_name_returns_query_when_no_input_schema() -> None:
    """Falls back to 'query' when inputSchema is absent."""
    assert _resolve_query_argument_name({"name": "fabric_query"}) == "query"


def test_resolve_query_argument_name_returns_query_when_properties_missing() -> None:
    """Falls back to 'query' when inputSchema has no properties dict."""
    tool_def = {"inputSchema": {"type": "object"}}
    assert _resolve_query_argument_name(tool_def) == "query"


def test_resolve_query_argument_name_falls_back_to_required_field() -> None:
    """Falls back to required field when no preferred name is present."""
    tool_def = {
        "inputSchema": {
            "properties": {"customField": {"type": "string"}},
            "required": ["customField"],
        }
    }
    assert _resolve_query_argument_name(tool_def) == "customField"


def test_resolve_query_argument_name_falls_back_to_first_property() -> None:
    """Falls back to first property when no preferred name and no required list."""
    tool_def = {
        "inputSchema": {
            "properties": {"someField": {"type": "string"}},
        }
    }
    assert _resolve_query_argument_name(tool_def) == "someField"


def test_resolve_query_argument_name_returns_query_for_empty_properties() -> None:
    """Falls back to 'query' when properties dict has no string keys."""
    tool_def = {"inputSchema": {"properties": {}}}
    assert _resolve_query_argument_name(tool_def) == "query"
