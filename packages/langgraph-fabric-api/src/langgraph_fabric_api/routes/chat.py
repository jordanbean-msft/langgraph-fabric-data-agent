"""Chat streaming endpoint."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from langgraph_fabric_core.graph.orchestrator import AgentOrchestrator
from starlette.responses import StreamingResponse

from langgraph_fabric_api.config import get_settings
from langgraph_fabric_api.core.auth import extract_bearer_token, extract_user_id, get_token_obo
from langgraph_fabric_api.core.dependencies import get_orchestrator
from langgraph_fabric_api.core.formatting import format_ndjson_event, format_sse_event
from langgraph_fabric_api.schemas import ChatRequest

router = APIRouter(tags=["chat"])


def _prefers_ndjson(request: Request) -> bool:
    """Return True when the caller explicitly requests NDJSON streaming.

    Args:
        request: The HTTP request object.

    Returns:
        True if Accept header includes application/x-ndjson.
    """
    accept = request.headers.get("accept", "")
    return "application/x-ndjson" in accept.lower()


@router.post("/chat/stream")
async def chat_stream(
    http_request: Request,
    body: ChatRequest,
    orchestrator: Annotated[AgentOrchestrator, Depends(get_orchestrator)],
) -> StreamingResponse:
    """Stream chat responses using LangGraph orchestrator.

    Requires a bearer token in the Authorization header. The token is exchanged
    for scope-specific MCP tokens via OBO flow.

    Args:
        http_request: The HTTP request object.
        body: The chat request payload.
        orchestrator: The AgentOrchestrator dependency.

    Returns:
        A StreamingResponse with either SSE or NDJSON formatted events.

    Raises:
        HTTPException: If authorization header is missing (401) or OBO exchange fails.
    """
    bearer_token = extract_bearer_token(http_request.headers.get("Authorization", ""))
    settings = get_settings()
    mcp_user_tokens: dict[str, str] = {}
    tokens_by_scope: dict[str, str] = {}
    for server in settings.mcp_servers:
        if server.scope not in tokens_by_scope:
            tokens_by_scope[server.scope] = await get_token_obo(
                bearer_token, settings, server.scope
            )
        mcp_user_tokens[server.name] = tokens_by_scope[server.scope]

    user_id = extract_user_id(bearer_token)
    use_ndjson = _prefers_ndjson(http_request)

    async def event_stream() -> AsyncIterator[bytes]:
        """Generate streaming events from orchestrator.

        Yields:
            Formatted event bytes (SSE or NDJSON).
        """
        formatter = format_ndjson_event if use_ndjson else format_sse_event
        async for chunk in orchestrator.stream(
            prompt=body.prompt,
            channel="api",
            auth_mode="api",
            user_id=user_id,
            mcp_user_tokens=mcp_user_tokens,
        ):
            if chunk.startswith("\n[tool]"):
                yield formatter("tool_status", chunk.strip())
            else:
                yield formatter("text", chunk)
        yield formatter("done", "[DONE]")

    media_type = "application/x-ndjson" if use_ndjson else "text/event-stream"
    return StreamingResponse(event_stream(), media_type=media_type)
