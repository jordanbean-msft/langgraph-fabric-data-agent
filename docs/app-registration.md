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

The following authorized client applications should be added as pre-authorized for the `access_as_user` scope:

| Application | Client ID |
| --- | --- |
| Microsoft Teams (Desktop & Mobile) | `1fec8e78-bce4-4aaf-ab1b-5451cc387264` |
| Microsoft Teams (Web) | `5e3ce6c0-2b1f-4285-8d4b-75ee78787346` |
| Microsoft Office | `4765445b-32c6-49b0-83e6-1d93765276ca` |
| Microsoft 365 Copilot (Web) | `0ec893e0-5785-4de6-99da-4ed124e5296c` |
| Microsoft 365 Copilot (Desktop) | `c0ab8ce9-e9a0-42e7-b064-33d422df41f1` |

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
