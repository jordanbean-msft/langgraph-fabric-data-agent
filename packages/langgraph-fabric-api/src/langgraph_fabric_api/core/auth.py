"""Authentication and authorization utilities."""

import base64
import json
import logging

from azure.core.exceptions import ClientAuthenticationError
from azure.identity.aio import OnBehalfOfCredential
from fastapi import HTTPException

from langgraph_fabric_api.config import ApiSettings

logger = logging.getLogger(__name__)


def extract_bearer_token(auth_header: str) -> str:
    """Extract Bearer token from Authorization header.

    Args:
        auth_header: The value of the Authorization HTTP header.

    Returns:
        The extracted bearer token.

    Raises:
        HTTPException: If the header is absent or not in 'Bearer <token>' form.
    """
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header. Expected: Authorization: Bearer <token>",
        )
    return auth_header[len("Bearer ") :]


def extract_user_id(token: str) -> str:
    """Extract user identity from JWT claims for correlation logging.

    The token is not validated here; it will be validated during the OBO
    exchange. This extracts only the identity claim needed for structured
    log correlation.

    Args:
        token: The JWT token string.

    Returns:
        The user identifier (preferred_username, upn, sub, or "unknown").
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


async def get_token_obo(bearer_token: str, settings: ApiSettings, scope: str) -> str:
    """Exchange the caller's JWT for a scope-specific token via the OBO flow.

    Requires MICROSOFT_APP_ID, MICROSOFT_APP_PASSWORD, and MICROSOFT_TENANT_ID
    to be configured in the server's environment.

    Args:
        bearer_token: The caller's JWT token.
        settings: API settings containing OBO credentials.
        scope: The resource scope to request a token for.

    Returns:
        The obtained access token.

    Raises:
        HTTPException: On credential misconfiguration (status 500) or token exchange failure (status 401).
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
            token = await credential.get_token(scope)
        return token.token
    except ClientAuthenticationError as exc:
        logger.warning("OBO token exchange failed: %s", exc)
        raise HTTPException(
            status_code=401,
            detail="Token exchange failed. This may indicate an invalid or expired caller token, insufficient Fabric delegated permissions, or a server-side credential misconfiguration.",
        ) from exc
