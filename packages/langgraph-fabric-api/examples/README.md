---
title: API Examples
description: How to run the API package examples for bearer-token and REST Client streaming calls
ms.date: 2026-04-02
---

## Overview

This folder contains runnable examples for calling the API streaming endpoint.

## Files

* `api_client_with_api_token.ipynb`: Jupyter notebook that uses MSAL interactive auth code flow to acquire a user token for the API and call `/chat/stream`
* `chat_stream.http`: REST Client sequence showing OAuth authorization code flow with PKCE and a final API call

## Prerequisites

* Run the API server
* Configure app registrations as described in `../../../docs/app-registration.md`
* Configure API environment variables in `../.env`
* Configure the calling app registration with redirect URI `http://localhost` under Mobile and desktop applications

## Run The Notebook Example

1. Start the API server from the repository root:

```bash
uv run langgraph-fabric-api
```

2. Open `api_client_with_api_token.ipynb` in VS Code.
3. Set environment variables for the notebook process:
   * `CHAT_API_BASE_URL` (default: `http://localhost:8000`)
   * `API_CLIENT_ID`
   * `CALLER_CLIENT_ID`
   * `TENANT_ID` (optional, default: `common`)

   Linux/macOS shell example:

```bash
export CHAT_API_BASE_URL="http://localhost:8000" API_CLIENT_ID="<api-client-id>" CALLER_CLIENT_ID="<caller-client-id>" TENANT_ID="common"
```

4. Run all cells in order.
5. Complete the browser sign-in flow when prompted.

## Run The REST Client Example

1. Install the VS Code REST Client extension if needed.
2. Open `chat_stream.http`.
3. Fill in `apiClientId` and `callerClientId` in the Configuration section.
4. Execute requests in order:
   1. Authorization request
   2. Token exchange request
   3. API stream request

## Troubleshooting

* `401 Unauthorized`: Verify the bearer token audience is the API app registration, not Fabric
* `403 Forbidden`: Verify app registration pre-authorization and delegated permissions
* Connection errors: Verify the API is running on the expected host and port
