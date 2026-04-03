---
title: API Examples
description: How to run the API package examples for bearer-token and REST Client streaming calls
ms.date: 2026-04-03
---

## Overview

This folder contains runnable examples for calling the API streaming endpoint.

## Files

* `api_client_with_api_token.ipynb`: Jupyter notebook that uses MSAL device code flow to acquire a user token for the API and call `/chat/stream`
* `chat_stream.http`: REST Client sequence showing OAuth authorization code flow with PKCE and a final API call

## Prerequisites

* Run the API server.
* Configure the API server app registration and `packages/langgraph-fabric-api/.env` as described in [../../../docs/app-registration.md#api-server-app-registration](../../../docs/app-registration.md#api-server-app-registration).
* Create a separate public calling app registration as described in [../../../docs/app-registration.md#calling-app-registration-for-api-examples](../../../docs/app-registration.md#calling-app-registration-for-api-examples).
* In the calling app registration, set **Allow public client flows** to **Yes** (Authentication).
* Add `http://localhost:3000/callback` to the calling app registration if you want to run the REST Client example.
* Grant the calling app delegated permission to `api://<API_CLIENT_ID>/access_as_user`.
* Recommended: on the API server app registration, add the calling app under Authorized client applications for the `access_as_user` scope.
* Configure API environment variables in `../.env`.
* Use the correct client IDs in the examples:
  * `API_CLIENT_ID`: client ID of the API server app registration.
  * `CALLER_CLIENT_ID`: client ID of the public calling app registration.

The calling app signs the user in and sends `Authorization: Bearer <user-jwt>` to the API. The API server then performs the downstream OBO exchange for MCP scopes such as Fabric.

## Run The Notebook Example

1. Start the API server from the repository root:

```bash
uv run langgraph-fabric-api
```

2. Open `api_client_with_api_token.ipynb` in VS Code.
3. Set environment variables for the notebook process:
   * `CHAT_API_BASE_URL` (default: `http://localhost:8000`)
   * `API_CLIENT_ID`: client ID of the API server app registration
   * `CALLER_CLIENT_ID`: client ID of the public calling app registration
   * `TENANT_ID` (optional, default: `common`)
   * `API_SCOPE` (optional): delegated scope to request for the API. If omitted, defaults to `api://<API_CLIENT_ID>/access_as_user`

   Linux/macOS shell example:

```bash
export CHAT_API_BASE_URL="http://localhost:8000" API_CLIENT_ID="<api-client-id>" CALLER_CLIENT_ID="<caller-client-id>" TENANT_ID="common" API_SCOPE="api://<api-client-id>/access_as_user"
```

4. Run all cells in order.
5. Follow the device code prompt in notebook output and complete sign-in in your browser.

## Run The REST Client Example

1. Install the VS Code REST Client extension if needed.
2. Add a `local` REST Client environment to your **User Settings** (`Preferences: Open User Settings (JSON)`).
   This is the recommended location because user settings are never committed to git and apply across
   all workspace folders in multi-root workspaces. Merge the following into your existing
   `rest-client.environmentVariables` block:

```json
{
   "rest-client.environmentVariables": {
      "local": {
         "entraAuthority": "https://login.microsoftonline.com",
         "tenantId": "<your-tenant-id>",
         "apiBaseUrl": "http://localhost:8000",
         "redirectUri": "http://localhost:3000/callback",
         "apiClientId": "<your-api-app-client-id>",
         "callerClientId": "<your-caller-public-client-id>",
         "apiScope": "api://<your-api-app-client-id>/access_as_user"
      }
   }
}
```

3. Create a local test copy and use it for requests:

```bash
cp packages/langgraph-fabric-api/examples/chat_stream.http packages/langgraph-fabric-api/examples/chat_stream.local.http
```

4. Add `packages/langgraph-fabric-api/examples/chat_stream.local.http` to `.git/info/exclude` and open `chat_stream.local.http` for local testing.
5. Select the `local` REST Client environment in VS Code.
6. Keep real authorization codes and access tokens only in local test files or request prompts. Do not place them in `chat_stream.http`.
7. Execute requests in order:
   1. Authorization request
   2. Token exchange request
   3. API stream request

## Troubleshooting

* `401 Unauthorized`: Verify the bearer token audience is the API app registration, not Fabric
* `403 Forbidden`: Verify app registration pre-authorization and delegated permissions
* Connection errors: Verify the API is running on the expected host and port
