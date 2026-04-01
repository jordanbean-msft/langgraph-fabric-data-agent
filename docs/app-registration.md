---
title: App Registration
description: Entra ID app registration reference for the LangGraph Fabric Data Agent hosted adapter
ms.date: 2026-04-01
---

# App Registration

The hosted adapter authenticates via the `bot-langgraph-fabric-data-agent` Entra ID app registration.
Use the details below when configuring your `.env` file and Bot Service OAuth connection.

| Property | Value |
| --- | --- |
| Display name | `bot-langgraph-fabric-data-agent` |
| Application (client) ID | `3d79b6ed-2103-4b7e-9214-a4c6b9ad11ae` |
| Application ID URI | `api://botId-3d79b6ed-2103-4b7e-9214-a4c6b9ad11ae` |
| Sign-in audience | Single tenant (`AzureADMyOrg`) |
| Redirect URI | `https://token.botframework.com/.auth/web/redirect` |

## Required API permissions

All permissions are delegated (user context). Admin consent is required for the Power BI Service scopes.

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

## Exposed API scope

The app exposes an `access_as_user` scope:

```text
api://botId-3d79b6ed-2103-4b7e-9214-a4c6b9ad11ae/access_as_user
```

Standard Microsoft Teams and Office client IDs are pre-authorized for this scope so users are not prompted for additional consent inside Teams or Copilot Chat.

## Client secrets

Two secrets exist for this registration. Retrieve and rotate them using the Azure CLI:

```bash
# List existing credentials
az ad app credential list --id 3d79b6ed-2103-4b7e-9214-a4c6b9ad11ae

# Add a new secret (append keeps existing secrets intact)
az ad app credential reset \
  --id 3d79b6ed-2103-4b7e-9214-a4c6b9ad11ae \
  --append \
  --display-name langgraph-fabric-data-agent \
  --years 1
```

Copy the `password` value from the output and set it as `MICROSOFT_APP_PASSWORD` in your `.env` file.

## Environment variable mapping

| `.env` variable | Value |
| --- | --- |
| `MICROSOFT_APP_ID` | `3d79b6ed-2103-4b7e-9214-a4c6b9ad11ae` |
| `MICROSOFT_APP_PASSWORD` | Client secret value from the registration |
| `MICROSOFT_TENANT_ID` | Your Entra tenant ID |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID` | `3d79b6ed-2103-4b7e-9214-a4c6b9ad11ae` |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET` | Client secret value from the registration |
