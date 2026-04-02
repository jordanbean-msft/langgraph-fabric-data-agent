import asyncio
import json

import pytest
import respx
from httpx import Response
from langgraph_fabric_core.fabric.auth import AuthContext
from langgraph_fabric_core.fabric.mcp_client import FabricMcpClient


class FakeTokenProvider:
    async def get_token(self, _context: AuthContext) -> str:
        return "fake-token"


def _sse_response(message: dict) -> Response:
    payload = f"data: {json.dumps(message)}\n\n"
    return Response(
        200,
        headers={"content-type": "text/event-stream"},
        content=payload.encode("utf-8"),
    )


@pytest.mark.asyncio
@respx.mock
async def test_list_and_call_tool(settings_fixture):
    client = FabricMcpClient(settings_fixture, FakeTokenProvider())
    auth = AuthContext(mode="local", user_id="u1")

    route = respx.post(settings_fixture.fabric_data_agent_mcp_url).mock(
        side_effect=[
            _sse_response({"jsonrpc": "2.0", "id": 1, "result": {}}),
            _sse_response({"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "query"}]}}),
            _sse_response(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "result": {"content": [{"type": "text", "text": "hello"}]},
                }
            ),
        ]
    )

    await client.initialize(auth)
    tools = await client.list_tools(auth)
    text = await client.call_tool(tool_name="query", arguments={"query": "hi"}, auth_context=auth)

    assert tools[0]["name"] == "query"
    assert text == "hello"
    assert all(
        "text/event-stream" in call.request.headers.get("accept", "") for call in route.calls
    )


@pytest.mark.asyncio
@respx.mock
async def test_list_and_call_tool_with_sse(settings_fixture):
    client = FabricMcpClient(settings_fixture, FakeTokenProvider())
    auth = AuthContext(mode="local", user_id="u1")

    respx.post(settings_fixture.fabric_data_agent_mcp_url).mock(
        side_effect=[
            _sse_response({"jsonrpc": "2.0", "id": 1, "result": {}}),
            _sse_response({"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "query"}]}}),
            _sse_response(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "result": {"content": [{"type": "text", "text": "hello from sse"}]},
                }
            ),
        ]
    )

    await client.initialize(auth)
    tools = await client.list_tools(auth)
    text = await client.call_tool(tool_name="query", arguments={"query": "hi"}, auth_context=auth)

    assert tools[0]["name"] == "query"
    assert text == "hello from sse"


@pytest.mark.asyncio
@respx.mock
async def test_json_response_is_supported(settings_fixture):
    client = FabricMcpClient(settings_fixture, FakeTokenProvider())
    auth = AuthContext(mode="local", user_id="u1")

    respx.post(settings_fixture.fabric_data_agent_mcp_url).mock(
        return_value=Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {}})
    )

    await client.initialize(auth)


@pytest.mark.asyncio
@respx.mock
async def test_unsupported_content_type_raises(settings_fixture):
    client = FabricMcpClient(settings_fixture, FakeTokenProvider())
    auth = AuthContext(mode="local", user_id="u1")

    respx.post(settings_fixture.fabric_data_agent_mcp_url).mock(
        return_value=Response(
            200,
            headers={"content-type": "text/plain"},
            content=b"ok",
        )
    )

    with pytest.raises(RuntimeError, match="application/json or text/event-stream"):
        await client.initialize(auth)


@pytest.mark.asyncio
@respx.mock
async def test_json_response_id_mismatch_raises(settings_fixture):
    client = FabricMcpClient(settings_fixture, FakeTokenProvider())
    auth = AuthContext(mode="local", user_id="u1")

    respx.post(settings_fixture.fabric_data_agent_mcp_url).mock(
        return_value=Response(200, json={"jsonrpc": "2.0", "id": 999, "result": {}})
    )

    with pytest.raises(RuntimeError, match="MCP response id mismatch"):
        await client.initialize(auth)


@pytest.mark.asyncio
async def test_concurrent_requests_keep_distinct_request_ids(settings_fixture, monkeypatch):
    client = FabricMcpClient(settings_fixture, FakeTokenProvider())
    auth = AuthContext(mode="local", user_id="u1")

    captured_request_ids: list[int] = []

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

    class _FakeStream:
        async def __aenter__(self) -> _FakeResponse:
            # Yield control so two requests can overlap inside _rpc.
            await asyncio.sleep(0)
            return _FakeResponse()

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        def stream(self, *_args, **_kwargs) -> _FakeStream:
            return _FakeStream()

    async def _fake_read_streamable_http_response(_response, request_id: int):
        captured_request_ids.append(request_id)
        await asyncio.sleep(0)
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": []}}

    monkeypatch.setattr(
        "langgraph_fabric_core.fabric.mcp_client.httpx.AsyncClient", _FakeAsyncClient
    )
    monkeypatch.setattr(
        client, "_read_streamable_http_response", _fake_read_streamable_http_response
    )

    await asyncio.gather(client.list_tools(auth), client.list_tools(auth))

    assert sorted(captured_request_ids) == [1, 2]
