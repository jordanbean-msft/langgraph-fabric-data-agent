"""FastAPI application surface."""

import base64
import json
import logging
from collections.abc import AsyncIterator
from functools import lru_cache

from azure.core.exceptions import ClientAuthenticationError
from azure.identity.aio import OnBehalfOfCredential
from fastapi import FastAPI, HTTPException, Request
from langgraph_fabric_core.fabric.auth import FabricTokenProvider
from langgraph_fabric_core.fabric.mcp_client import FabricMcpClient
from langgraph_fabric_core.graph.orchestrator import AgentOrchestrator
from langgraph_fabric_core.llm.factory import create_chat_model
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from langgraph_fabric_api.config import ApiSettings, get_settings

logger = logging.getLogger(__name__)


def _extract_bearer_token(request: Request) -> str:
    """Extract Bearer token from Authorization header.

    Raises HTTP 401 if the header is absent or not in 'Bearer <token>' form.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header. Expected: Authorization: Bearer <token>",
        )
    return auth_header[len("Bearer ") :]


def _extract_user_id(token: str) -> str:
    """Extract user identity from JWT claims for correlation logging.

    The token is not validated here; it will be validated during the OBO
    exchange. This extracts only the identity claim needed for structured
    log correlation.
    """
    try:
        payload_part = token.split(".")[1]
        padding = (4 - len(payload_part) % 4) % 4
        payload = json.loads(base64.b64decode(payload_part + "=" * padding))
        return (
            payload.get("preferred_username")
            or payload.get("upn")
            or payload.get("sub")
            or "unknown"
        )
    except Exception:
        logger.debug("Could not extract user identity from token", exc_info=True)
        return "unknown"


async def _get_fabric_token_obo(bearer_token: str, settings: ApiSettings) -> str:
    """Exchange the caller's JWT for a Fabric-scoped token via the OBO flow.

    Requires MICROSOFT_APP_ID, MICROSOFT_APP_PASSWORD, and MICROSOFT_TENANT_ID
    to be configured in the server's environment.

    Raises HTTP 500 when server OBO credentials are not configured, and
    HTTP 401 when the OBO exchange is rejected by Microsoft Entra ID.
    """
    if (
        not settings.microsoft_app_id
        or not settings.microsoft_app_password
        or not settings.microsoft_tenant_id
    ):
        raise HTTPException(
            status_code=500,
            detail=(
                "Server is not configured for OBO token exchange. "
                "Set MICROSOFT_APP_ID, MICROSOFT_APP_PASSWORD, and MICROSOFT_TENANT_ID."
            ),
        )
    try:
        async with OnBehalfOfCredential(
            tenant_id=settings.microsoft_tenant_id,
            client_id=settings.microsoft_app_id,
            client_secret=settings.microsoft_app_password,
            user_assertion=bearer_token,
        ) as credential:
            token = await credential.get_token(settings.fabric_data_agent_scope)
        return token.token
    except ClientAuthenticationError as exc:
        logger.warning("OBO token exchange failed: %s", exc)
        raise HTTPException(
            status_code=401,
            detail="Token exchange failed. This may indicate an invalid or expired caller token, insufficient Fabric delegated permissions, or a server-side credential misconfiguration.",
        ) from exc


@lru_cache(maxsize=1)
def get_orchestrator() -> AgentOrchestrator:
    """Build and cache the default orchestrator instance."""
    settings = get_settings()
    token_provider = FabricTokenProvider(settings)
    fabric_client = FabricMcpClient(settings, token_provider)
    chat_model = create_chat_model(settings)
    return AgentOrchestrator(chat_model, fabric_client)


app = FastAPI(title="LangGraph Fabric Data Agent")


class ChatRequest(BaseModel):
    prompt: str


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat/stream")
async def chat_stream(http_request: Request, body: ChatRequest) -> StreamingResponse:
    # Auth check first — raises 401 before touching settings
    bearer_token = _extract_bearer_token(http_request)
    settings = get_settings()
    fabric_token = await _get_fabric_token_obo(bearer_token, settings)
    user_id = _extract_user_id(bearer_token)
    orchestrator = get_orchestrator()

    async def event_stream() -> AsyncIterator[bytes]:
        async for chunk in orchestrator.stream(
            prompt=body.prompt,
            channel="api",
            auth_mode="api",
            user_id=user_id,
            fabric_user_token=fabric_token,
        ):
            if chunk.startswith("\n[tool]"):
                yield f"event: tool_status\ndata: {chunk.strip()}\n\n".encode()
            else:
                yield f"event: text\ndata: {chunk}\n\n".encode()
        yield b"event: done\ndata: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
