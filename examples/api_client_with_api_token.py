"""Example client that calls the API with a bearer token for this API.

This sample demonstrates the standard deployed pattern:
1. Your application signs the user in with Microsoft Entra ID
2. Your application acquires a token for THIS API (not for Fabric)
3. Your application calls this API with the token in the Authorization header
4. The API validates the token and exchanges it for a Fabric token via on-behalf-of (OBO) flow

Security note:
- This is a PUBLIC client (no client secret needed)
- The API app registration pre-authorizes this client for the API scope
- Pre-authorization means the user is never prompted for consent
- The API's client secret never leaves the API server
- Only the API uses its credentials to do OBO with the Fabric Data Agent

For this sample to work:
- Set API_CLIENT_ID to your API app registration's Client ID (resource/audience)
- Set CALLER_CLIENT_ID to your calling application's Client ID (public client)
- TENANT_ID should be your Azure tenant ID (optional, defaults to common)
"""

from __future__ import annotations

import os

import httpx
import msal

API_BASE_URL = os.getenv("CHAT_API_BASE_URL", "http://localhost:8000")
API_CLIENT_ID = os.getenv("API_CLIENT_ID", "")
CALLER_CLIENT_ID = os.getenv("CALLER_CLIENT_ID", "")
TENANT_ID = os.getenv("TENANT_ID", "common")


def acquire_api_token() -> str:
    """Acquire a token for the API as a public client.

    Uses device code flow so no browser is required. The API app registration
    pre-authorizes this client for the api://{API_CLIENT_ID}/.default scope,
    so the user is not prompted for consent.

    The acquired token will be sent to the API in the Authorization header.
    The API validates the token and uses its own credentials to do OBO
    (on-behalf-of) to exchange it for a Fabric token.

    Returns:
        An access token whose audience is this API
    """
    if not API_CLIENT_ID:
        raise ValueError("Set API_CLIENT_ID to your API app registration's Client ID")
    if not CALLER_CLIENT_ID:
        raise ValueError("Set CALLER_CLIENT_ID to your public calling application's Client ID")

    # PublicClientApplication: no client secret needed
    app = msal.PublicClientApplication(
        CALLER_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    )

    # Device code flow: user signs in on another device or browser
    flow = app.initiate_device_flow(
        scopes=[f"api://{API_CLIENT_ID}/.default"],
    )
    print(flow["message"])

    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise ValueError(
            f"Failed to acquire token: {result.get('error_description', result.get('error'))}"
        )

    return result["access_token"]


def stream_chat(api_token: str, prompt: str) -> None:
    """Send a streaming chat request to the API.

    Args:
        api_token: Bearer token with audience set to this API
        prompt: The user's question
    """
    request_body = {
        "prompt": prompt,
    }

    with httpx.stream(
        "POST",
        f"{API_BASE_URL}/chat/stream",
        json=request_body,
        headers={
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {api_token}",
        },
        timeout=120,
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                print(line)


if __name__ == "__main__":
    try:
        print("Acquiring API token as a public client (no client secret needed)...\n")
        token = acquire_api_token()
        print("\nStreaming response:\n")
        stream_chat(token, "Summarize yesterday's sales by region")
    except ValueError as e:
        print(f"Error: {e}", file=__import__("sys").stderr)
        exit(1)
