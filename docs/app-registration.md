---
title: App Registration
description: Entra ID app registration reference for the LangGraph Fabric Data Agent API and M365 interfaces
ms.date: 2026-04-02
---

## Overview

Use one or more Entra ID app registrations depending on which interface you run.

| Registration | Used by | Purpose |
| --- | --- | --- |
| API server app registration | `langgraph-fabric-api` | Accepts a user token for this API and performs On-Behalf-Of (OBO) exchange to downstream MCP scopes |
| Calling app registration | Notebook example, REST Client example, or your own frontend | Signs in the user and requests a token whose audience is the API server |
| M365 bot app registration | `langgraph-fabric-m365` | Identifies the bot in Teams or Copilot Chat and exposes the bot scope |

## API server app registration

Use this registration when you run `langgraph-fabric-api`. It is a confidential client because the API server stores a client secret and uses it during the OBO exchange.

| Property | Value |
| --- | --- |
| Display name (suggested) | `api-langgraph-fabric-data-agent` |
| Application (client) ID | `<YOUR_API_CLIENT_ID>` |
| Application ID URI | `api://<YOUR_API_CLIENT_ID>` |
| Supported account types | Single tenant (`AzureADMyOrg`) or multi-tenant if your callers span tenants |
| Redirect URI | None required for this sample |
| Client secret | Required |
| Exposed API scope | `api://<YOUR_API_CLIENT_ID>/access_as_user` |

Create or verify the API server registration with these steps:

1. Register a new application in Entra ID for the API server.
2. In Expose an API, set the Application ID URI to `api://<YOUR_API_CLIENT_ID>`.
3. Add a delegated scope named `access_as_user`. The examples and guides in this repo assume that scope name.
4. In Certificates & secrets, create a client secret for the API server.
5. In API permissions, grant the delegated permissions required by each MCP backend your API will call. For Fabric, request the Fabric delegated permissions your agent needs, such as `Item.Read.All`.

Map the API server registration into `packages/langgraph-fabric-api/.env` like this:

| Variable | Value |
| --- | --- |
| `MICROSOFT_APP_ID` | `<YOUR_API_CLIENT_ID>` |
| `MICROSOFT_APP_PASSWORD` | Client secret value from the API server registration |
| `MICROSOFT_TENANT_ID` | Your Entra tenant ID |

## Calling app registration for API examples

Use a separate public client registration for anything that signs the user in and then calls `POST /chat/stream`. This includes the notebook example, the REST Client example, and most desktop or browser-based developer tools.

| Property | Value |
| --- | --- |
| Display name (suggested) | `client-langgraph-fabric-api-local` |
| Application (client) ID | `<YOUR_CALLER_CLIENT_ID>` |
| Supported account types | Match the tenant model used by the API server |
| Platform | Mobile and desktop applications |
| Redirect URIs | `http://localhost:3000/callback` for the REST Client example (not required for notebook device code flow) |
| Client secret | Not used |
| Delegated API permission | `api://<YOUR_API_CLIENT_ID>/access_as_user` |

Configure the calling app registration with these steps:

1. Register a new application for the calling client.
2. In Authentication, add the Mobile and desktop applications platform.
3. Add `http://localhost:3000/callback` if you want to run the REST Client example.
4. In API permissions, add a delegated permission to your API server app registration by selecting My APIs, choosing the API server registration, and selecting `access_as_user`.
5. Recommended: in the API server app registration, open Expose an API, add the caller app under Authorized client applications, and grant the `access_as_user` scope. That suppresses an extra consent prompt for trusted local clients. If you skip this step, the first sign-in may still work, but the user or an admin will need to consent to the API permission.

Use these IDs in the examples:

| Example variable | Value |
| --- | --- |
| `API_CLIENT_ID` | Client ID of the API server app registration |
| `CALLER_CLIENT_ID` | Client ID of the public calling app registration |

When the caller signs the user in, request this delegated API scope:

```text
api://<API_CLIENT_ID>/access_as_user
```

The caller sends that access token to the API in the `Authorization` header. The API server then exchanges it for downstream MCP backend scopes, such as `https://api.fabric.microsoft.com/.default`. The calling app does not request the Fabric scope directly.

## M365 bot app registration

Use this registration when you run `langgraph-fabric-m365`. It is separate from the public calling app registration used by the API examples.

| Property | Value |
| --- | --- |
| Display name (suggested) | `bot-langgraph-fabric-data-agent` |
| Application (client) ID | `<YOUR_APP_CLIENT_ID>` |
| Application ID URI | `api://botId-<YOUR_APP_CLIENT_ID>` |
| Sign-in audience | Single tenant (`AzureADMyOrg`) |
| Redirect URI | `https://token.botframework.com/.auth/web/redirect` |

### Required API permissions

All permissions are delegated, in user context. Admin consent is required for the Power BI Service scopes.

**Power BI Service** (`00000009-0000-0000-c000-000000000000`):

| Permission | Purpose |
| --- | --- |
| `DataAgent.Execute.All` | Execute Fabric Data Agents on behalf of the user |
| `DataAgent.Read.All` | Read Fabric Data Agent metadata |
| `Item.Execute.All` | Execute Fabric items |
| `Item.Read.All` | Read Fabric items |
| `Lakehouse.Read.All` | Read Fabric Lakehouse data |
| `Workspace.Read.All` | Read Fabric workspaces |

**Microsoft Graph** (`00000003-0000-0000-c000-000000000000`):

| Permission | Purpose |
| --- | --- |
| `email` | Read user email address |
| `offline_access` | Maintain delegated access with a refresh token |
| `openid` | Sign users in with OIDC |
| `profile` | Read basic user profile |
| `User.Read` | Read the signed-in user's profile |

### Exposed API scope

The M365 bot app exposes an `access_as_user` scope:

```text
api://botId-<YOUR_APP_CLIENT_ID>/access_as_user
```

Standard Microsoft Teams and Office client IDs are pre-authorized for this scope so users are not prompted for additional consent inside Teams or Copilot Chat.

Add these authorized client applications as pre-authorized for the `access_as_user` scope:

| Application | Client ID |
| --- | --- |
| Microsoft Teams (Desktop & Mobile) | `1fec8e78-bce4-4aaf-ab1b-5451cc387264` |
| Microsoft Teams (Web) | `5e3ce6c0-2b1f-4285-8d4b-75ee78787346` |
| Microsoft Office | `4765445b-32c6-49b0-83e6-1d93765276ca` |
| Microsoft 365 Copilot (Web) | `0ec893e0-5785-4de6-99da-4ed124e5296c` |
| Microsoft 365 Copilot (Desktop) | `c0ab8ce9-e9a0-42e7-b064-33d422df41f1` |

## Client secrets for confidential registrations

The API server app registration and the M365 bot app registration are confidential clients. The calling app registration for the API examples is a public client and does not use a client secret.

Retrieve or rotate a client secret with Azure CLI:

```bash
# List existing credentials
az ad app credential list --id <YOUR_APP_CLIENT_ID>

# Add a new secret and keep existing secrets intact
az ad app credential reset \
  --id <YOUR_APP_CLIENT_ID> \
  --append \
  --display-name langgraph-fabric-data-agent \
  --years 1
```

Copy the `password` value from the output and set it as `MICROSOFT_APP_PASSWORD` in the package-local `.env` file for the interface you are configuring.

## M365 environment variable mapping

| `.env` variable | Value |
| --- | --- |
| `MICROSOFT_APP_ID` | `<YOUR_APP_CLIENT_ID>` |
| `MICROSOFT_APP_PASSWORD` | Client secret value from the registration |
| `MICROSOFT_TENANT_ID` | Your Entra tenant ID |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID` | `<YOUR_APP_CLIENT_ID>` |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET` | Client secret value from the registration |
