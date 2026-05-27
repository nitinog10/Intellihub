# Azure Setup Guide for ClosedLoop OS

This guide explains how to provision Azure for ClosedLoop OS, how each Azure resource is used, how to configure secrets, and how to deploy the app safely.

## What ClosedLoop OS Uses in Azure

ClosedLoop OS currently relies on these Azure services:

- `Resource Group`: `closedloop-os-rg`
- `Azure Cosmos DB`: `closedloop-events`
- `Cosmos SQL Database`: `closedloop-os`
- `Cosmos Containers`:
  - `events`
  - `relationships` (required for graph queries in Phase 4+)
- `Azure Key Vault`: `closedloop-secrets`
- `Azure Service Bus Namespace`: `closedloop-bus`
- `Service Bus Queue`: `raw-events`
- `Azure Container Apps Environment`: `closedloop-env`
- `Azure OpenAI Account`: `closedloop-openai`
- `Azure OpenAI Deployments`:
  - `gpt-4o-mini`
  - `text-embedding-3-small`
- `Azure AI Search Service`: `closedloop-search`
- `Azure Functions`: hosts the API endpoints, Service Bus trigger, and Notion polling timer

## What Each Azure Resource Does

### `closedloop-events` Cosmos DB

Used to store normalized canonical events from all connectors.

Current containers:

- `events`
  Used for GitHub, Slack, Linear, Jira, Confluence, Notion, Zendesk, and meeting-derived events.
- `relationships`
  Used for graph edges like `BLOCKED_BY`, `IMPLEMENTS`, `DISCUSSED_IN`, and `MENTIONED_IN`.

The `events` container uses partition key `/source_tool`.

### `closedloop-secrets` Key Vault

Used to store connector secrets and tokens so they do not live in source code or plain config files.

### `closedloop-bus` Service Bus

Used as the raw ingestion bus.

Flow:

1. A connector receives a webhook or upload.
2. It publishes a raw event to `raw-events`.
3. Azure Functions consumes the queue.
4. The classification pipeline normalizes, classifies, stores, and indexes the event.

### `closedloop-openai`

Used for:

- classification with `gpt-4o-mini`
- embeddings with `text-embedding-3-small`

### `closedloop-search`

Used for:

- semantic search
- Jira and Linear overlap detection
- intelligence retrieval

Index name:

- `closedloop-knowledge`

### `closedloop-env`

Container Apps environment reserved for app hosting or future workload expansion. The current repo primarily uses Azure Functions, but keeping this environment provisioned is reasonable for later API/container hosting.

## Prerequisites

Install and verify:

```powershell
az --version
python --version
git --version
```

You also need:

- an Azure subscription
- permission to create resource groups and cognitive/search resources
- access to create or manage Azure OpenAI deployments in the target region

## Recommended Azure Region

The Bicep defaults to `eastus`.

Before provisioning, confirm that your selected region supports:

- Azure OpenAI
- Azure AI Search
- Cosmos DB serverless
- Service Bus Standard
- Azure Functions

## Infrastructure Files in This Repo

- [infra/main.bicep](D:/Intellihub/infra/main.bicep:1)
- [infra/modules/closedloop-resources.bicep](D:/Intellihub/infra/modules/closedloop-resources.bicep:1)

## Step 1: Sign In to Azure

```powershell
az login
az account show
```

If you have multiple subscriptions:

```powershell
az account set --subscription "<YOUR_SUBSCRIPTION_ID_OR_NAME>"
```

## Step 2: Review the Default Resource Names

The Bicep template currently defaults to:

- resource group: `closedloop-os-rg`
- Cosmos account: `closedloop-events`
- Cosmos database: `closedloop-os`
- Key Vault: `closedloop-secrets`
- Service Bus namespace: `closedloop-bus`
- queue: `raw-events`
- Container Apps environment: `closedloop-env`
- Azure OpenAI account: `closedloop-openai`
- Azure AI Search service: `closedloop-search`

If any of these names are globally unavailable, pass overrides during deployment.

## Step 3: Validate the Bicep Template

```powershell
az deployment sub validate `
  --location eastus `
  --template-file infra/main.bicep
```

If you want custom names:

```powershell
az deployment sub validate `
  --location eastus `
  --template-file infra/main.bicep `
  --parameters resourceGroupName="closedloop-os-rg" `
               cosmosAccountName="closedloop-events" `
               keyVaultName="closedloop-secrets" `
               serviceBusNamespaceName="closedloop-bus" `
               azureOpenAIAccountName="closedloop-openai" `
               azureSearchServiceName="closedloop-search"
```

## Step 4: Deploy the Infrastructure

```powershell
az deployment sub create `
  --location eastus `
  --template-file infra/main.bicep
```

After deployment, capture outputs:

```powershell
az deployment sub show `
  --name <DEPLOYMENT_NAME> `
  --query properties.outputs
```

You should get values like:

- `cosmosEndpoint`
- `keyVaultUri`
- `serviceBusNamespace`
- `azureOpenAIEndpoint`
- `azureSearchEndpoint`

## Step 5: Create the Missing Cosmos `relationships` Container

Important: the current application code expects a Cosmos container named `relationships`, but the Bicep currently provisions only `events`.

Create it manually until the infra template is updated:

```powershell
az cosmosdb sql container create `
  --account-name closedloop-events `
  --resource-group closedloop-os-rg `
  --database-name closedloop-os `
  --name relationships `
  --partition-key-path "/relationship_type"
```

Recommended partition key:

- `/relationship_type`

Alternative acceptable choice:

- `/source_node`

## Step 6: Fetch Keys and Connection Strings

### Cosmos DB

```powershell
az cosmosdb keys list `
  --name closedloop-events `
  --resource-group closedloop-os-rg
```

You will need:

- `COSMOS_ENDPOINT`
- `COSMOS_KEY`

### Service Bus

```powershell
az servicebus namespace authorization-rule keys list `
  --resource-group closedloop-os-rg `
  --namespace-name closedloop-bus `
  --name RootManageSharedAccessKey
```

You will need:

- `SERVICE_BUS_CONNECTION_STRING`

### Azure AI Search

```powershell
az search admin-key show `
  --resource-group closedloop-os-rg `
  --service-name closedloop-search
```

You will need:

- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_API_KEY`

### Azure OpenAI

```powershell
az cognitiveservices account keys list `
  --name closedloop-openai `
  --resource-group closedloop-os-rg
```

You will need:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`

## Step 7: Populate Azure Key Vault

Set the secrets that the app expects. You do not need every connector secret on day one, only the connectors you plan to activate.

### Core app secrets

```powershell
az keyvault secret set --vault-name closedloop-secrets --name github-webhook-secret --value "<VALUE>"
az keyvault secret set --vault-name closedloop-secrets --name slack-signing-secret --value "<VALUE>"
az keyvault secret set --vault-name closedloop-secrets --name slack-bot-token --value "<VALUE>"
az keyvault secret set --vault-name closedloop-secrets --name linear-webhook-secret --value "<VALUE>"
az keyvault secret set --vault-name closedloop-secrets --name jira-access-token --value "<VALUE>"
az keyvault secret set --vault-name closedloop-secrets --name jira-webhook-secret --value "<VALUE>"
az keyvault secret set --vault-name closedloop-secrets --name confluence-access-token --value "<VALUE>"
az keyvault secret set --vault-name closedloop-secrets --name confluence-webhook-secret --value "<VALUE>"
az keyvault secret set --vault-name closedloop-secrets --name notion-access-token --value "<VALUE>"
az keyvault secret set --vault-name closedloop-secrets --name zendesk-webhook-secret --value "<VALUE>"
```

### Notes by connector

- GitHub:
  set the webhook shared secret.
- Slack:
  set the Slack signing secret and bot token.
- Linear:
  set the webhook secret.
- Jira:
  current code assumes the OAuth flow is handled outside the service and stores an access token here.
- Confluence:
  same model as Jira.
- Notion:
  store the integration token.
- Zendesk:
  store the webhook verification secret.

## Step 8: Configure Application Settings

The app reads settings from environment variables. For Azure deployment, map these into Azure Functions application settings.

Start from [local.settings.sample.json](D:/Intellihub/local.settings.sample.json:1).

Minimum recommended settings:

```text
COSMOS_ENDPOINT
COSMOS_KEY
COSMOS_DATABASE_NAME=closedloop-os
COSMOS_CONTAINER_NAME=events
KEY_VAULT_URI=https://closedloop-secrets.vault.azure.net/
SERVICE_BUS_CONNECTION_STRING
SERVICE_BUS_QUEUE_NAME=raw-events
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_OPENAI_EMBEDDING_DIMENSIONS=1536
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_SEARCH_ENDPOINT
AZURE_SEARCH_API_KEY
AZURE_SEARCH_INDEX_NAME=closedloop-knowledge
```

Optional connector settings:

```text
GITHUB_WEBHOOK_SECRET
SLACK_SIGNING_SECRET
SLACK_BOT_TOKEN
LINEAR_WEBHOOK_SECRET
JIRA_ACCESS_TOKEN
JIRA_WEBHOOK_SECRET
CONFLUENCE_ACCESS_TOKEN
CONFLUENCE_WEBHOOK_SECRET
NOTION_ACCESS_TOKEN
NOTION_API_VERSION
NOTION_DATABASE_ID
ZENDESK_WEBHOOK_SECRET
```

If you rely on Key Vault instead of direct env values, keep:

- `KEY_VAULT_URI`
- the relevant `*_NAME` entries

## Step 9: Deploy the Python App to Azure Functions

This repo is structured around Azure Functions using [function_app.py](D:/Intellihub/function_app.py:1).

Typical deployment flow:

1. Create a Function App in Azure.
2. Set app settings.
3. Deploy the code.

Example Function App creation:

```powershell
az functionapp create `
  --resource-group closedloop-os-rg `
  --consumption-plan-location eastus `
  --runtime python `
  --runtime-version 3.11 `
  --functions-version 4 `
  --name <YOUR_FUNCTION_APP_NAME> `
  --storage-account <YOUR_STORAGE_ACCOUNT_NAME>
```

Set application settings:

```powershell
az functionapp config appsettings set `
  --resource-group closedloop-os-rg `
  --name <YOUR_FUNCTION_APP_NAME> `
  --settings `
    FUNCTIONS_WORKER_RUNTIME=python `
    COSMOS_ENDPOINT="<COSMOS_ENDPOINT>" `
    COSMOS_KEY="<COSMOS_KEY>" `
    COSMOS_DATABASE_NAME="closedloop-os" `
    COSMOS_CONTAINER_NAME="events" `
    KEY_VAULT_URI="https://closedloop-secrets.vault.azure.net/" `
    SERVICE_BUS_CONNECTION_STRING="<SERVICE_BUS_CONNECTION_STRING>" `
    SERVICE_BUS_QUEUE_NAME="raw-events" `
    AZURE_OPENAI_ENDPOINT="<AZURE_OPENAI_ENDPOINT>" `
    AZURE_OPENAI_API_KEY="<AZURE_OPENAI_API_KEY>" `
    AZURE_OPENAI_DEPLOYMENT="gpt-4o-mini" `
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT="text-embedding-3-small" `
    AZURE_OPENAI_EMBEDDING_DIMENSIONS="1536" `
    AZURE_OPENAI_API_VERSION="2024-10-21" `
    AZURE_SEARCH_ENDPOINT="<AZURE_SEARCH_ENDPOINT>" `
    AZURE_SEARCH_API_KEY="<AZURE_SEARCH_API_KEY>" `
    AZURE_SEARCH_INDEX_NAME="closedloop-knowledge"
```

Deploy code with Azure Functions Core Tools or your CI pipeline.

## Step 10: Grant Key Vault Access

The code uses `DefaultAzureCredential()` in [secrets.py](D:/Intellihub/src/closedloop_os/secrets.py:1).

That means your Azure-hosted app should use:

1. a system-assigned or user-assigned managed identity
2. Key Vault access through RBAC or access policies

Recommended approach:

1. enable managed identity on the Function App
2. grant `Key Vault Secrets User` on `closedloop-secrets`

Example:

```powershell
az functionapp identity assign `
  --resource-group closedloop-os-rg `
  --name <YOUR_FUNCTION_APP_NAME>
```

Then grant RBAC using the app principal id.

## Step 11: Verify Azure OpenAI Deployments

The app expects:

- classification deployment name: `gpt-4o-mini`
- embedding deployment name: `text-embedding-3-small`

If your Azure OpenAI deployment names differ from the model names, set:

- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`

to the exact deployment names in Azure.

## Step 12: Verify Azure AI Search Indexing

The code will create or update the `closedloop-knowledge` index at runtime when the knowledge store is used.

Important fields expected by the app:

- `id`
- `source_tool`
- `event_type`
- `title`
- `description`
- `actor`
- `importance_score`
- `timestamp`
- `content_vector`

The index is built in [search.py](D:/Intellihub/src/closedloop_os/search.py:159).

## Step 13: Verify Service Bus Retry and Dead-Letter Behavior

The queue trigger is in [function_app.py](D:/Intellihub/function_app.py:10).

Current behavior:

- Azure Functions fixed-delay retry is enabled
- Service Bus `maxDeliveryCount` handles poison-message routing
- expired or repeatedly failing messages should land in the dead-letter subqueue

Check queue state:

```powershell
az servicebus queue show `
  --resource-group closedloop-os-rg `
  --namespace-name closedloop-bus `
  --name raw-events
```

## Step 14: Webhook and Endpoint Mapping

After the app is deployed, configure these integrations to point to your Function App base URL:

- GitHub:
  `POST /api/connectors/github`
- Slack:
  `POST /api/connectors/slack`
- Linear:
  `POST /api/connectors/linear`
- Jira:
  `POST /api/connectors/jira`
- Confluence:
  `POST /api/connectors/confluence`
- Zendesk:
  `POST /api/connectors/zendesk`
- Meetings:
  `POST /api/connectors/meetings/upload`

Also expose:

- `GET /healthz`
- `/mcp`

## Step 15: Post-Deployment Validation Checklist

- `healthz` returns `{"status":"ok"}`
- GitHub webhook reaches the app and stores an event
- Slack signature verification works
- Service Bus receives raw events
- the queue trigger classifies and stores canonical events
- Azure AI Search index `closedloop-knowledge` exists
- `semantic_search()` returns results
- `ask_intelligence()` returns a cited answer
- meeting upload stores meeting-derived events
- `get_entity_graph()` returns relationship edges

## Known Gaps You Should Be Aware Of

- The current Bicep does not yet create the `relationships` Cosmos container.
- The app expects connector OAuth tokens to already exist. It does not yet run a full OAuth consent flow for Jira, Confluence, Slack, Notion, or Zendesk.
- The repo provisions a Container Apps environment, but the primary runtime path here is Azure Functions.

## Recommended Next Infra Improvements

1. Add the `relationships` Cosmos container to Bicep.
2. Add a Function App resource and app settings to Bicep.
3. Add managed identity + Key Vault RBAC to Bicep.
4. Add Azure Storage resource creation for the Function App.
5. Add deployment automation for Functions in GitHub Actions.
