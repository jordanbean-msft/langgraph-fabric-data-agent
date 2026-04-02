---
title: Azure Bot Service
description: Azure Bot Service setup, operations, and channel configuration for the LangGraph Fabric Data Agent
ms.date: 2026-04-01
---

# Azure Bot Service

Fill in the details below with your own Azure resource identifiers before running any commands. The values shown are placeholders.

| Property         | Value                    |
| ---------------- | ------------------------ |
| Subscription     | `<YOUR_SUBSCRIPTION_ID>` |
| Resource group   | `<YOUR_RESOURCE_GROUP>`  |
| Bot resource     | `<YOUR_BOT_NAME>`        |
| Microsoft app ID | `<YOUR_APP_CLIENT_ID>`   |
| Tenant ID        | `<YOUR_TENANT_ID>`       |
| OAuth connection | `FabricOAuth2`           |

Current configuration notes:

- The bot is an `azurebot` resource on the `S1` SKU in `global`.
- The bot is configured as `SingleTenant` and currently points at a dev tunnel messaging endpoint.
- `msteams`, `m365extensions`, `webchat`, and `directline` channels are enabled.
- The `FabricOAuth2` connection uses `Azure Active Directory v2` with the Fabric scope `https://api.fabric.microsoft.com/.default`.
- Application Insights is not configured on the bot resource.
- [appPackage/manifest.sample.json](../appPackage/manifest.sample.json) contains placeholder website URLs and `validDomains` — copy it to `manifest.json` and update the values before packaging the Microsoft 365 app.

> [!IMPORTANT]
> The messaging endpoint uses a dev tunnel URL by default. Update the endpoint whenever the tunnel hostname changes.

## Sign in and set shell variables

```bash
az login
az account set --subscription <YOUR_SUBSCRIPTION_ID>

BOT_RESOURCE_GROUP="<YOUR_RESOURCE_GROUP>"
BOT_NAME="<YOUR_BOT_NAME>"
BOT_APP_ID="<YOUR_APP_CLIENT_ID>"
BOT_TENANT_ID="<YOUR_TENANT_ID>"
OAUTH_CONNECTION_NAME="FabricOAuth2"
FABRIC_SCOPE="https://api.fabric.microsoft.com/.default"
```

## Create or rotate the bot app secret

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

Azure only returns the new secret once. Save it immediately and set it in `packages/langgraph-fabric-m365/.env` as both `MICROSOFT_APP_PASSWORD` and `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET`.

## Create the bot resource

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

## Run the M365 adapter and update the messaging endpoint

Start the M365 adapter:

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

## Create or recreate the FabricOAuth2 connection

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
  --ids "/subscriptions/<YOUR_SUBSCRIPTION_ID>/resourceGroups/<YOUR_RESOURCE_GROUP>/providers/Microsoft.BotService/botServices/<YOUR_BOT_NAME>/connections/FabricOAuth2" \
  --query "properties.{provider:serviceProviderDisplayName,scope:scopes,tenant:parameters[?key=='tenantId'].value | [0]}" \
  -o json
```

## Verify channel configuration

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

## Update the Microsoft 365 app package

Before uploading the package, copy [appPackage/manifest.sample.json](../appPackage/manifest.sample.json) to `appPackage/manifest.json` and update these values to match your public hostname and bot registration:

- `developer.websiteUrl`
- `developer.privacyUrl`
- `developer.termsOfUseUrl`
- `validDomains`
- `bots[0].botId`
- `copilotAgents.customEngineAgents[0].id`

Build the package after updating the manifest:

```bash
mkdir -p appPackage/build && \
  rm -f appPackage/build/langgraph-fabric-data-agent-m365.zip && \
  zip -j appPackage/build/langgraph-fabric-data-agent-m365.zip \
    appPackage/manifest.json appPackage/color.png appPackage/outline.png
```
