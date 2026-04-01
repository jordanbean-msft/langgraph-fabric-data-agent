---
title: LangGraph Fabric Data Agent Sample
description: Python monorepo sample showing a LangGraph agent calling a Fabric Data Agent through MCP, structured as independent packages for core logic and each client interface
ms.date: 2026-04-01
---

## Overview

This repository demonstrates a LangGraph-based AI agent that calls a Fabric Data Agent via MCP.

The sample is organized as a **uv workspace** with four independent Python packages:

| Package | Description |
| --- | --- |
| [`langgraph-fabric-core`](packages/langgraph-fabric-core/) | Interface-agnostic: graph, orchestrator, Fabric MCP client, auth, LLM factory |
| [`langgraph-fabric-api`](packages/langgraph-fabric-api/) | FastAPI streaming endpoint |
| [`langgraph-fabric-console`](packages/langgraph-fabric-console/) | Interactive terminal with streamed responses |
| [`langgraph-fabric-m365`](packages/langgraph-fabric-m365/) | Teams / Copilot Chat via M365 Agents SDK |

`langgraph-fabric-core` has **no** dependency on FastAPI, aiohttp, or the M365 Agents SDK. Each interface package depends only on core.

## Architecture

### langgraph-fabric-core

- [`core/config.py`](packages/langgraph-fabric-core/src/langgraph_fabric_core/core/config.py): centralized environment settings via pydantic-settings.
- [`core/logging.py`](packages/langgraph-fabric-core/src/langgraph_fabric_core/core/logging.py): structured logs with correlation context.
- [`fabric/auth.py`](packages/langgraph-fabric-core/src/langgraph_fabric_core/fabric/auth.py): local and hosted token strategies for Fabric.
- [`fabric/mcp_client.py`](packages/langgraph-fabric-core/src/langgraph_fabric_core/fabric/mcp_client.py): strict JSON-RPC MCP client wrapper.
- [`fabric/tools.py`](packages/langgraph-fabric-core/src/langgraph_fabric_core/fabric/tools.py): LangGraph tool integration over MCP.
- [`graph/workflow.py`](packages/langgraph-fabric-core/src/langgraph_fabric_core/graph/workflow.py): graph definition and tool routing.
- [`graph/orchestrator.py`](packages/langgraph-fabric-core/src/langgraph_fabric_core/graph/orchestrator.py): shared run and stream orchestration.
- [`llm/factory.py`](packages/langgraph-fabric-core/src/langgraph_fabric_core/llm/factory.py): Azure OpenAI / Foundry chat model factory.

### langgraph-fabric-api

- [`app.py`](packages/langgraph-fabric-api/src/langgraph_fabric_api/app.py): FastAPI surface with `/health` and `/chat/stream`.
- [`main.py`](packages/langgraph-fabric-api/src/langgraph_fabric_api/main.py): API entrypoint (`langgraph-fabric-api` script).

### langgraph-fabric-console

- [`console.py`](packages/langgraph-fabric-console/src/langgraph_fabric_console/console.py): interactive terminal surface with streaming.
- [`main.py`](packages/langgraph-fabric-console/src/langgraph_fabric_console/main.py): console entrypoint (`langgraph-fabric-console` script).

### langgraph-fabric-m365

- [`app.py`](packages/langgraph-fabric-m365/src/langgraph_fabric_m365/app.py): hosted M365 adapter bridge and route wiring.
- [`oauth.py`](packages/langgraph-fabric-m365/src/langgraph_fabric_m365/oauth.py): hosted OAuth card flow, magic code handling, and hosted token resolution.
- [`runtime.py`](packages/langgraph-fabric-m365/src/langgraph_fabric_m365/runtime.py): hosted runtime environment and SDK configuration builders.
- [`main.py`](packages/langgraph-fabric-m365/src/langgraph_fabric_m365/main.py): M365 adapter entrypoint (`langgraph-fabric-m365` script).

## Prerequisites

Base prerequisites:

- Python 3.12 or later
- `uv`
- Azure CLI 2.55.0 or later
- Access to an Azure OpenAI / Foundry project with a `gpt-5.4` deployment
- Access to a Fabric Data Agent MCP endpoint
- A signed-in user account that can authenticate to Azure and Fabric

Hosted-mode prerequisites:

- A Microsoft Entra app registration for the bot
- An Azure Bot resource with a Bot Service OAuth connection
- Access to a Microsoft 365 tenant where you can test in Teams or Copilot Chat

Optional local tooling:

- `devtunnel` CLI for exposing the hosted adapter from your machine
- `zip` for the `build-m365-app-package` task

## App Registration

The hosted adapter authenticates via the `bot-langgraph-fabric-data-agent` Entra ID app registration. Use the details below when configuring your `.env` file and Bot Service OAuth connection.

| Property                | Value                                               |
| ----------------------- | --------------------------------------------------- |
| Display name            | `bot-langgraph-fabric-data-agent`                   |
| Application (client) ID | `3d79b6ed-2103-4b7e-9214-a4c6b9ad11ae`              |
| Application ID URI      | `api://botId-3d79b6ed-2103-4b7e-9214-a4c6b9ad11ae`  |
| Sign-in audience        | Single tenant (`AzureADMyOrg`)                      |
| Redirect URI            | `https://token.botframework.com/.auth/web/redirect` |

### Required API permissions

All permissions are delegated (user context). Admin consent is required for the Power BI Service scopes.

**Power BI Service** (`00000009-0000-0000-c000-000000000000`):

| Permission              | Purpose                                          |
| ----------------------- | ------------------------------------------------ |
| `DataAgent.Execute.All` | Execute Fabric Data Agents on behalf of the user |
| `DataAgent.Read.All`    | Read Fabric Data Agent metadata                  |
| `Item.Execute.All`      | Execute Fabric items                             |
| `Item.Read.All`         | Read Fabric items                                |
| `Lakehouse.Read.All`    | Read Fabric Lakehouse data                       |
| `Workspace.Read.All`    | Read Fabric workspaces                           |

**Microsoft Graph** (`00000003-0000-0000-c000-000000000000`):

| Permission       | Purpose                                        |
| ---------------- | ---------------------------------------------- |
| `email`          | Read user email address                        |
| `offline_access` | Maintain delegated access with a refresh token |
| `openid`         | Sign users in with OIDC                        |
| `profile`        | Read basic user profile                        |
| `User.Read`      | Read the signed-in user's profile              |

### Exposed API scope

The app exposes an `access_as_user` scope:

```text
api://botId-3d79b6ed-2103-4b7e-9214-a4c6b9ad11ae/access_as_user
```

Standard Microsoft Teams and Office client IDs are pre-authorized for this scope so users are not prompted for additional consent inside Teams or Copilot Chat.

### Client secrets

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

### Environment variable mapping

| `.env` variable                                           | Value                                     |
| --------------------------------------------------------- | ----------------------------------------- |
| `MICROSOFT_APP_ID`                                        | `3d79b6ed-2103-4b7e-9214-a4c6b9ad11ae`    |
| `MICROSOFT_APP_PASSWORD`                                  | Client secret value from the registration |
| `MICROSOFT_TENANT_ID`                                     | Your Entra tenant ID                      |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID`     | `3d79b6ed-2103-4b7e-9214-a4c6b9ad11ae`    |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET` | Client secret value from the registration |

## Setup

1. Copy [.env.example](.env.example) to `.env` and fill your values.
2. Install all workspace packages and dev dependencies:

```bash
uv sync --all-packages --extra dev
```

3. Fill the Azure OpenAI and Fabric MCP values in `.env`.
4. For hosted mode, also set `MICROSOFT_APP_ID`, `MICROSOFT_APP_PASSWORD`, `MICROSOFT_TENANT_ID`, `FABRIC_OAUTH_CONNECTION_NAME`, and the `CONNECTIONS__SERVICE_CONNECTION__*` values from the app registration section above.

The hosted runtime reads these settings in [`langgraph_fabric_core/core/config.py`](packages/langgraph-fabric-core/src/langgraph_fabric_core/core/config.py) and passes them to the Microsoft Agents SDK via [`langgraph_fabric_m365/runtime.py`](packages/langgraph-fabric-m365/src/langgraph_fabric_m365/runtime.py).

## Azure Bot Service

This repository is currently wired to the following Azure Bot resource:

- Subscription: `0ec6c427-01d3-4462-ae56-fd9656157157`
- Resource group: `rg-langgraph-fabric-data-agent`
- Bot resource: `bot-langgraph-fabric-data-agent`
- Microsoft app ID: `3d79b6ed-2103-4b7e-9214-a4c6b9ad11ae`
- Tenant ID: `66beb9f0-9df6-4ded-8e48-126b39813500`
- OAuth connection: `FabricOAuth2`

Review of the current Azure Bot resource:

- The bot is an `azurebot` resource on the `S1` SKU in `global`.
- The bot is configured as `SingleTenant` and currently points at `https://fz8h9xmv-8000.usw3.devtunnels.ms/api/messages`.
- `msteams`, `m365extensions`, `webchat`, and `directline` are enabled.
- The `FabricOAuth2` connection already exists and uses `Azure Active Directory v2` with the Fabric scope `https://api.fabric.microsoft.com/.default`.
- Application Insights is not configured on the bot resource.
- [appPackage/manifest.json](appPackage/manifest.json) still contains placeholder website URLs and `validDomains`, so update that file before packaging the Microsoft 365 app.

> [!IMPORTANT]
> The current messaging endpoint uses a dev tunnel URL. That is appropriate for local development, but you should expect to update the endpoint whenever the tunnel hostname changes.

### Sign in and set shell variables

```bash
az login
az account set --subscription 0ec6c427-01d3-4462-ae56-fd9656157157

BOT_RESOURCE_GROUP="rg-langgraph-fabric-data-agent"
BOT_NAME="bot-langgraph-fabric-data-agent"
BOT_APP_ID="3d79b6ed-2103-4b7e-9214-a4c6b9ad11ae"
BOT_TENANT_ID="66beb9f0-9df6-4ded-8e48-126b39813500"
OAUTH_CONNECTION_NAME="FabricOAuth2"
FABRIC_SCOPE="https://api.fabric.microsoft.com/.default"
```

### Create or rotate the bot app secret

Create a new secret and keep the existing secrets in place:

```bash
BOT_APP_PASSWORD="$(az ad app credential reset \
  --id "$BOT_APP_ID" \
  --append \
  --display-name "langgraph-fabric-data-agent" \
  --years 1 \
  --query password \
  -o tsv)"
```

Azure only returns the new secret once. Save it immediately and set it in `.env` as both `MICROSOFT_APP_PASSWORD` and `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET`.

### Create the bot if you need to recreate it

If the resource already exists, skip this step and move to the endpoint update.

```bash
az bot create \
  --resource-group "$BOT_RESOURCE_GROUP" \
  --name "$BOT_NAME" \
  --appid "$BOT_APP_ID" \
  --app-type SingleTenant \
  --tenant-id "$BOT_TENANT_ID" \
  --sku S1 \
  --endpoint "https://<public-hostname>/api/messages"
```

### Run the hosted adapter and update the messaging endpoint

Start the hosted adapter:

```bash
uv run langgraph-fabric-m365
```

Expose port `8000` through your preferred tunnel and then update the bot endpoint:

```bash
BOT_ENDPOINT="https://<public-hostname>/api/messages"

az bot update \
  --resource-group "$BOT_RESOURCE_GROUP" \
  --name "$BOT_NAME" \
  --endpoint "$BOT_ENDPOINT" \
  --display-name "$BOT_NAME" \
  --sku S1
```

Verify the endpoint:

```bash
az bot show \
  --resource-group "$BOT_RESOURCE_GROUP" \
  --name "$BOT_NAME" \
  --query properties.endpoint \
  -o tsv
```

### Create or recreate the `FabricOAuth2` connection

Inspect the current connection:

```bash
az bot authsetting show \
  --resource-group "$BOT_RESOURCE_GROUP" \
  --name "$BOT_NAME" \
  --setting-name "$OAUTH_CONNECTION_NAME" \
  -o json
```

If you rotate the client secret, delete and recreate the connection so Bot Service uses the new secret:

```bash
az bot authsetting delete \
  --resource-group "$BOT_RESOURCE_GROUP" \
  --name "$BOT_NAME" \
  --setting-name "$OAUTH_CONNECTION_NAME"

az bot authsetting create \
  --resource-group "$BOT_RESOURCE_GROUP" \
  --name "$BOT_NAME" \
  --setting-name "$OAUTH_CONNECTION_NAME" \
  --service "Azure Active Directory v2" \
  --client-id "$BOT_APP_ID" \
  --client-secret "$BOT_APP_PASSWORD" \
  --provider-scope-string "$FABRIC_SCOPE" \
  --parameters tenantId="$BOT_TENANT_ID" tokenExchangeUrl="api://botId-$BOT_APP_ID"
```

Verify the recreated connection:

```bash
az resource show \
  --ids "/subscriptions/0ec6c427-01d3-4462-ae56-fd9656157157/resourceGroups/rg-langgraph-fabric-data-agent/providers/Microsoft.BotService/botServices/bot-langgraph-fabric-data-agent/connections/FabricOAuth2" \
  --query "properties.{provider:serviceProviderDisplayName,scope:scopes,tenant:parameters[?key=='tenantId'].value | [0]}" \
  -o json
```

### Verify channel configuration

The current bot already has Teams, Direct Line, Web Chat, and Microsoft 365 Extensions enabled.

```bash
az bot show \
  --resource-group "$BOT_RESOURCE_GROUP" \
  --name "$BOT_NAME" \
  --query properties.enabledChannels \
  -o json
```

If you need to enable the Teams channel on a new bot, run:

```bash
az bot msteams create \
  --resource-group "$BOT_RESOURCE_GROUP" \
  --name "$BOT_NAME"
```

You can inspect the Teams channel afterward with:

```bash
az bot msteams show \
  --resource-group "$BOT_RESOURCE_GROUP" \
  --name "$BOT_NAME" \
  -o json
```

> [!NOTE]
> The Azure CLI exposes `msteams`, `directline`, and `webchat` command groups, but it does not currently expose a dedicated `m365extensions` command group. The current bot already has `m365extensions` enabled, so verify that channel in the portal if you recreate the resource from scratch.

### Update the Microsoft 365 app package

Before uploading the package, update [appPackage/manifest.json](appPackage/manifest.json) so these values match your public hostname and bot registration:

- `developer.websiteUrl`
- `developer.privacyUrl`
- `developer.termsOfUseUrl`
- `validDomains`
- `bots[0].botId`
- `copilotAgents.customEngineAgents[0].id`

Build the package after updating the manifest:

```bash
mkdir -p appPackage/build && rm -f appPackage/build/langgraph-fabric-data-agent-m365.zip && zip -j appPackage/build/langgraph-fabric-data-agent-m365.zip appPackage/manifest.json appPackage/color.png appPackage/outline.png
```

## VS Code Tasks

This repository includes workspace tasks in [.vscode/tasks.json](.vscode/tasks.json) so you can run the common development and hosted-adapter flows directly from VS Code.

Open the task picker with **Terminal: Run Task** in VS Code, then choose one of these tasks:

| Task                            | Purpose                                                                                  |
| ------------------------------- | ---------------------------------------------------------------------------------------- |
| `sync-venv`                     | Install and sync the project and dev dependencies with `uv sync --extra dev`.            |
| `lint`                          | Run Ruff across the repository.                                                          |
| `test-unit`                     | Run the unit test suite with verbose output.                                             |
| `test-integration`              | Run the integration test suite with verbose output.                                      |
| `test-all`                      | Run the full test suite.                                                                 |
| `run-api`                       | Start the FastAPI surface on the configured port as a background task.                   |
| `run-console`                   | Start the interactive console surface.                                                   |
| `run-hosted`                    | Start the hosted M365 adapter as a background task in a new terminal panel.              |
| `devtunnel-login`               | Sign in to the Dev Tunnel CLI.                                                           |
| `devtunnel-create`              | Create or reuse a named dev tunnel for the hosted adapter.                               |
| `devtunnel-show`                | Show the current dev tunnel configuration.                                               |
| `devtunnel-port-configure`      | Recreate the HTTP port mapping for the hosted adapter port.                              |
| `devtunnel-host`                | Start hosting the dev tunnel as a background task in a new panel.                        |
| `run-hosted-and-devtunnel-host` | Start the hosted adapter and the dev tunnel host in parallel.                            |
| `run-hosted-with-devtunnel`     | Configure the tunnel port first, then start both the hosted adapter and the tunnel host. |
| `build-m365-app-package`        | Build the Microsoft 365 app zip from the manifest and icon assets.                       |

### Task inputs

The dev tunnel tasks prompt for these inputs:

| Input                 | Default                            | Purpose                                                                 |
| --------------------- | ---------------------------------- | ----------------------------------------------------------------------- |
| `devTunnelId`         | `langgraph-fabric-data-agent-m365` | Reusable dev tunnel name for the hosted endpoint.                       |
| `hostedPort`          | `8000`                             | Local port exposed by the hosted adapter.                               |
| `devTunnelExpiration` | `7d`                               | Lifetime of the dev tunnel. Available choices are `4h`, `1d`, and `7d`. |

### Recommended task flows

For a normal first-time local setup in VS Code:

1. Run `sync-venv`.
2. Run `lint` and `test-unit`.
3. Run `run-console`, `run-api`, or `run-hosted` depending on the surface you want to test.

For hosted Microsoft 365 testing with a dev tunnel:

1. Run `devtunnel-login` once on your machine.
2. Run `devtunnel-create` if you have not created the named tunnel yet.
3. Run `run-hosted-with-devtunnel` to configure port `8000`, start the hosted adapter, and host the tunnel.
4. Copy the public dev tunnel URL into the Azure Bot endpoint with `az bot update` as described in the Azure Bot Service section.

> [!NOTE]
> `run-api`, `run-hosted`, and `devtunnel-host` are background tasks. Stop them from the VS Code terminal panel when you are finished.

## Run

API surface:

```bash
uv run langgraph-fabric-api
```

Console surface:

```bash
uv run langgraph-fabric-console
```

Hosted adapter initialization:

```bash
uv run langgraph-fabric-m365
```

## Validate

```bash
uv run ruff check .
uv run pytest tests/unit
uv run pytest tests/integration
```

## Notes

- FastAPI endpoints are intentionally unauthenticated for this demo.
- Fabric tool calls always require user authentication.
- Local mode uses DefaultAzureCredential with interactive fallback.
- Hosted mode expects Bot Service user tokens.
- Hosted OAuth behavior sends an Adaptive Card sign-in prompt, disables the sign-in action after flow initiation, and supports pasting OAuth magic codes back in chat.
- Hosted runtime state access uses helper functions in [src/langgraph_fabric_data_agent/hosted/oauth.py](src/langgraph_fabric_data_agent/hosted/oauth.py) instead of direct TurnState get_value and set_value calls for SDK compatibility.
- Logging supports a base `LOG_LEVEL` plus optional `LOG_LEVEL_OVERRIDE` values such as `langgraph_fabric_data_agent.graph:DEBUG,azure.core:WARNING`.
- DEBUG logs can include large configuration payloads from dependencies. Redact secrets before sharing logs outside your machine.
