---
title: Teams and Copilot Chat Guide
description: How to set up and run the LangGraph Fabric Data Agent in Microsoft Teams and Copilot Chat
ms.date: 2026-04-01
---

# Teams and Copilot Chat Guide

The `langgraph-fabric-m365` package is a hosted adapter that bridges the Fabric Data Agent to Microsoft Teams and Microsoft 365 Copilot Chat. It uses the M365 Agents SDK to handle Bot Framework messaging and an Azure Bot Service OAuth connection to authenticate users against Fabric.

## Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/) installed.
- An Azure Bot resource configured with a Bot Service OAuth connection pointing at your Entra app — see [app-registration.md](app-registration.md) and [azure-bot-service.md](azure-bot-service.md).
- A `.env.m365` file at the repository root with all required variables (see [Environment variables](#environment-variables) below).
- A public HTTPS URL for the bot messaging endpoint. For local development, use `devtunnel` or a similar tool.
- Access to a Microsoft 365 tenant where you can install the app in Teams or test in Copilot Chat.

## Authentication

Authentication in the hosted adapter is user-delegated and flows through the Azure Bot Service OAuth connection:

1. A user sends a message in Teams or Copilot Chat.
2. The adapter attempts to exchange the Bot Service OAuth connection token for a Fabric access token.
3. If no token is available, the adapter sends an Adaptive Card sign-in prompt with a link to complete the OAuth flow.
4. The user clicks **Sign in**, authenticates with their organizational account, and may be prompted to paste a numeric verification code back into the chat.
5. On subsequent messages the cached token is used directly — no further sign-in prompts appear.

The OAuth connection must be named `FabricOAuth2` (default) or the name configured in `FABRIC_OAUTH_CONNECTION_NAME`. It must target the Fabric API scope (`https://api.fabric.microsoft.com/.default`).

See [azure-bot-service.md](azure-bot-service.md) for step-by-step instructions on creating the OAuth connection in the Azure portal.

## Setup

### 1. Configure the .env.m365 file

Copy `.env.m365.example` to `.env.m365` and fill in the M365 adapter values:

```ini
# Azure Bot / M365 settings
MICROSOFT_APP_ID=<your-bot-app-client-id>
MICROSOFT_APP_PASSWORD=<your-bot-app-client-secret>
MICROSOFT_TENANT_ID=<your-tenant-id>
FABRIC_OAUTH_CONNECTION_NAME=FabricOAuth2

# M365 Agents SDK service connection
CONNECTIONS__SERVICE_CONNECTION__ID=service_connection
CONNECTIONS__SERVICE_CONNECTION__NAME=Default Service Connection
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID=<your-bot-app-client-id>
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID=<your-tenant-id>
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__AUTHTYPE=ClientSecret
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET=<your-bot-app-client-secret>
```

`MICROSOFT_APP_ID` and the `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID` should both be set to the **Application (client) ID** of your bot's Entra app registration.

### 2. Expose a public HTTPS endpoint

The Azure Bot Service must be able to POST messages to your adapter. For local development, use `devtunnel`:

```bash
devtunnel host -p 8000 --allow-anonymous
```

Copy the HTTPS tunnel URL (e.g., `https://<tunnel-id>.devtunnels.ms`).

### 3. Update the bot messaging endpoint

In the Azure portal, navigate to your Bot resource → **Settings → Configuration** and update the **Messaging endpoint** to:

```
https://<tunnel-id>.devtunnels.ms/api/messages
```

### 4. Start the adapter

```bash
uv run langgraph-fabric-m365
```

The server listens on port `8000` by default. Override it with `PORT=<number>` in `.env`.

## Install in Teams

1. Build the Teams app package:

   ```bash
   cp appPackage/manifest.sample.json appPackage/manifest.json
   # Edit appPackage/manifest.json and replace <YOUR_APP_ID> with MICROSOFT_APP_ID
   cd appPackage && zip -r ../teams-app-package.zip manifest.json color.png outline.png
   ```

2. In Teams, go to **Apps → Manage your apps → Upload an app → Upload a custom app** and select `teams-app-package.zip`.

3. Open the app in Teams and send a message to trigger the sign-in flow.

See [azure-bot-service.md](azure-bot-service.md) for the full app package reference and channel configuration steps.

## Sign-in flow walkthrough

| Step | What happens |
| --- | --- |
| User sends a message | Adapter checks the Bot Service OAuth connection for an existing token |
| No token available | Adapter sends an Adaptive Card with a **Sign in** button |
| User clicks Sign in | Browser opens the Entra sign-in page |
| Sign-in completes | User may receive a numeric verification code |
| User pastes the code | Adapter redeems the code for a Fabric access token |
| Token acquired | Adapter runs the original prompt and sends the response |
| Subsequent messages | Adapter reuses the cached token; no sign-in prompt is shown |

> [!NOTE]
> The sign-in card's **Sign in** button is disabled after the user clicks it to prevent duplicate authentication flows. If a verification code prompt appears, paste the code directly into the chat.

## Environment variables

All settings are read from `.env.m365` via the M365 settings model. The following variables are required for the M365 adapter:

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `AZURE_OPENAI_ENDPOINT` | Yes | — | Azure OpenAI / Foundry project endpoint |
| `AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME` | Yes | — | Chat model deployment name (e.g. `gpt-4o`) |
| `AZURE_OPENAI_API_VERSION` | No | `2025-11-15-preview` | Azure OpenAI API version |
| `FABRIC_DATA_AGENT_MCP_URL` | Yes | — | Fabric Data Agent MCP endpoint URL |
| `FABRIC_DATA_AGENT_SCOPE` | No | `https://api.fabric.microsoft.com/.default` | OAuth scope for Fabric token |
| `FABRIC_DATA_AGENT_TIMEOUT_SECONDS` | No | `120` | Maximum seconds to wait for an MCP response |
| `MICROSOFT_APP_ID` | Yes | — | Bot Entra app Application (client) ID |
| `MICROSOFT_APP_PASSWORD` | Yes | — | Bot Entra app client secret |
| `MICROSOFT_TENANT_ID` | Yes | — | Azure tenant ID |
| `FABRIC_OAUTH_CONNECTION_NAME` | No | `FabricOAuth2` | Name of the Bot Service OAuth connection for Fabric |
| `CONNECTIONS__SERVICE_CONNECTION__ID` | Yes | — | M365 Agents SDK service connection ID |
| `CONNECTIONS__SERVICE_CONNECTION__NAME` | No | `Default Service Connection` | Service connection display name |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID` | Yes | — | Service connection client ID (same as `MICROSOFT_APP_ID`) |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID` | Yes | — | Service connection tenant ID |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__AUTHTYPE` | No | `ClientSecret` | Service connection auth type |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET` | Yes | — | Service connection client secret (same as `MICROSOFT_APP_PASSWORD`) |
| `PORT` | No | `8000` | Port the adapter listens on |
| `LOG_LEVEL` | No | `INFO` | Root log level |

See [.env.m365.example](../.env.m365.example) for a full template.
