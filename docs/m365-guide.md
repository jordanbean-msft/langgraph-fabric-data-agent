---
title: Teams and Copilot Chat Guide
description: How to set up and run the LangGraph MCP sample in Microsoft Teams and Copilot Chat
ms.date: 2026-04-01
---

## Teams and Copilot Chat Guide

The `langgraph-fabric-m365` package is an M365 adapter that bridges the LangGraph agent to Microsoft Teams and Microsoft 365 Copilot Chat. It uses the M365 Agents SDK to handle Bot Framework messaging, validates the incoming Teams/Copilot JWT at the `/api/messages` endpoint, and uses Azure Bot Service OAuth connections for MCP-backed tools when needed.

## Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/) installed.
- An Azure Bot resource configured with a Bot Service OAuth connection pointing at your Entra app — see [app-registration.md](app-registration.md) and [azure-bot-service.md](azure-bot-service.md).
- A `.env` file in `packages/langgraph-fabric-m365/` with all required variables (see [Environment variables](#environment-variables) below).
- A public HTTPS URL for the bot messaging endpoint. For local development, use `devtunnel` or a similar tool.
- Access to a Microsoft 365 tenant where you can install the app in Teams or test in Copilot Chat.

## Authentication

The M365 channel is protected by the Teams/Copilot JWT validated at the HTTP layer. If you configure MCP servers with `oauth_connection_name`, tool access is additionally user-delegated through the Azure Bot Service OAuth connection:

1. A user sends a message in Teams or Copilot Chat.
2. The adapter attempts to exchange the Bot Service OAuth connection token for a Fabric access token.
3. If no token is available, the adapter sends an Adaptive Card sign-in prompt with a link to complete the OAuth flow.
4. The user clicks **Sign in**, authenticates with their organizational account, and may be prompted to paste a numeric verification code back into the chat.
5. On subsequent messages the cached token is used directly and no further sign-in prompts appear.

Even if `MCP_SERVERS` is empty, the adapter still requires an authenticated Teams or Copilot Chat user because `/api/messages` is protected by JWT validation middleware. Chat-only mode means no MCP tool calls, not an anonymous channel.

Each MCP server entry in `MCP_SERVERS` can specify its own `oauth_connection_name` (for example, `FabricOAuth2`). The OAuth connection must target the server's API scope. For Fabric, use `https://api.fabric.microsoft.com/.default`.

See [azure-bot-service.md](azure-bot-service.md) for step-by-step instructions on creating the OAuth connection in the Azure portal.

## Setup

### 1. Configure the .env file

Copy `packages/langgraph-fabric-m365/.env.example` to `packages/langgraph-fabric-m365/.env` and fill in the M365 adapter values:

```ini
# Azure Bot / M365 settings
MICROSOFT_APP_ID=<your-bot-app-client-id>
MICROSOFT_APP_PASSWORD=<your-bot-app-client-secret>
MICROSOFT_TENANT_ID=<your-tenant-id>

# MCP servers (optional, set oauth_connection_name per server)
MCP_SERVERS=[{"name":"fabric","description":"Fabric analytics MCP server","url":"https://api.fabric.microsoft.com/v1/mcp/workspaces/<workspace-id>/dataagents/<agent-id>/agent","scope":"https://api.fabric.microsoft.com/.default","oauth_connection_name":"FabricOAuth2","timeout_seconds":120,"poll_interval_seconds":2}]

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

```text
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
   cd packages/langgraph-fabric-m365
   cp appPackage/manifest.sample.json appPackage/manifest.json
   # Edit appPackage/manifest.json and replace the placeholder values (see azure-bot-service.md)
   mkdir -p appPackage/build
   zip -j appPackage/build/langgraph-fabric-data-agent-m365.zip \
     appPackage/manifest.json appPackage/color.png appPackage/outline.png
   ```

   Or use the VS Code task **`build-m365-app-package`** after updating `appPackage/manifest.json`.

2. In Teams, go to **Apps → Manage your apps → Upload an app → Upload a custom app** and select `appPackage/build/langgraph-fabric-data-agent-m365.zip`.

3. Open the app in Teams and send a message to trigger the sign-in flow.

See [azure-bot-service.md](azure-bot-service.md) for the full app package reference and channel configuration steps.

## Official publish in Microsoft 365 admin center

Use this flow when you want to publish the agent through your tenant admin process instead of sideloading only in Teams.

1. Build or download the agent ZIP package for publishing.
2. For this sample, use `packages/langgraph-fabric-m365/appPackage/build/langgraph-fabric-data-agent-m365.zip`.
3. Open [Microsoft 365 admin center](https://admin.microsoft.com/).
4. Select **Agents** > **All agents** > **Registry** > **Add agent** (you may have to click on the ellipsis button on the right-hand side of the screen to see this).
5. Select **Choose File** and upload the ZIP file, then wait for validation to complete.
6. Verify package metadata (name, icon, and supported host products), then select **Next**.
7. Assign users for rollout. Start with **Just me** or a test security group for pilot validation, then expand assignment after smoke testing sign-in and tool calls.
8. Review permissions and capabilities, then select **Next**.
9. Select **Finish deployment** to complete publishing.

After upload, manage assignment and deployment from the same agent entry in the admin center. For official lifecycle guidance, see [Upload Microsoft 365 Copilot custom agents](https://learn.microsoft.com/en-us/microsoft-365/copilot/agent-essentials/agent-lifecycle/agent-upload-agents).

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

All settings are read from `packages/langgraph-fabric-m365/.env` via the M365 settings model. The following variables are required for the M365 adapter:

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `AZURE_OPENAI_ENDPOINT` | Yes | — | Azure OpenAI / Foundry project endpoint |
| `AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME` | Yes | — | Chat model deployment name (e.g. `gpt-4o`) |
| `AZURE_OPENAI_API_VERSION` | No | `2025-11-15-preview` | Azure OpenAI API version |
| `MCP_SERVERS` | No | `[]` | JSON array of MCP servers with `name`, `description`, `url`, `scope`, `oauth_connection_name`, `timeout_seconds`, `poll_interval_seconds` |
| `MICROSOFT_APP_ID` | Yes | — | Bot Entra app Application (client) ID |
| `MICROSOFT_APP_PASSWORD` | Yes | — | Bot Entra app client secret |
| `MICROSOFT_TENANT_ID` | Yes | — | Azure tenant ID |
| `CONNECTIONS__SERVICE_CONNECTION__ID` | Yes | — | M365 Agents SDK service connection ID |
| `CONNECTIONS__SERVICE_CONNECTION__NAME` | No | `Default Service Connection` | Service connection display name |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID` | Yes | — | Service connection client ID (same as `MICROSOFT_APP_ID`) |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID` | Yes | — | Service connection tenant ID |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__AUTHTYPE` | No | `ClientSecret` | Service connection auth type |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET` | Yes | — | Service connection client secret (same as `MICROSOFT_APP_PASSWORD`) |
| `PORT` | No | `8000` | Port the adapter listens on |
| `LOG_LEVEL` | No | `INFO` | Root log level |

See [packages/langgraph-fabric-m365/.env.example](../packages/langgraph-fabric-m365/.env.example) for a full template.
