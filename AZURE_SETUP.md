# Azure Manual Setup Guide for ClosedLoop OS

This guide is written for manual setup in the Azure Portal. You do not need Azure CLI for these steps.

Before starting Azure setup, test locally first:

```powershell
cd D:\Intellihub
.\scripts\setup_local.ps1
.\scripts\test_all.ps1
.\scripts\run_local.ps1
```

Then, in a second PowerShell window:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/healthz
```

Only continue here after the health check returns:

```json
{"status":"ok"}
```

Use the names below unless Azure tells you a name is unavailable. Globally unique resources such as Cosmos DB, Key Vault, Service Bus, Azure OpenAI, AI Search, Storage, and Function Apps may need a short suffix.

## Azure Pieces in Plain English

- Resource Group: a folder for all Azure resources in this project.
- Cosmos DB: the permanent database for normalized events and relationships.
- Key Vault: a secure place for webhook secrets and API tokens.
- Service Bus: the queue that receives raw events before processing.
- Azure OpenAI: classification and embeddings.
- Azure AI Search: vector search for semantic retrieval.
- Storage Account: required by Azure Functions.
- Function App: the hosted Python app.

## What ClosedLoop OS Uses in Azure

- `Resource Group`: `closedloop-os-rg`
- `Azure Cosmos DB`: `closedloop-events`
- `Cosmos SQL Database`: `closedloop-os`
- `Cosmos Containers`:
  - `events`
  - `relationships`
- `Azure Key Vault`: `closedloop-secrets`
- `Azure Service Bus Namespace`: `closedloop-bus`
- `Service Bus Queue`: `raw-events`
- `Azure OpenAI Account`: `closedloop-openai`
- `Azure OpenAI Deployments`:
  - `gpt-4o-mini`
  - `text-embedding-3-small`
- `Azure AI Search Service`: `closedloop-search`
- `Storage Account`: required by Azure Functions
- `Azure Function App`: hosts the API endpoints, Service Bus trigger, and Notion polling timer

## Recommended Region

Start with `East US` unless your Azure OpenAI access requires another region.

Before creating resources, confirm the region supports:

- Azure OpenAI
- Azure AI Search
- Cosmos DB for NoSQL
- Service Bus Standard
- Azure Functions

## Keep This Notes Block While You Work

Copy this somewhere temporary and fill it in as you create resources:

```text
RESOURCE_GROUP=closedloop-os-rg
REGION=East US
COSMOS_ACCOUNT_NAME=
COSMOS_ENDPOINT=
COSMOS_KEY=
KEY_VAULT_NAME=
KEY_VAULT_URI=
SERVICE_BUS_NAMESPACE=
SERVICE_BUS_CONNECTION_STRING=
AZURE_OPENAI_ACCOUNT=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_SEARCH_SERVICE=
AZURE_SEARCH_ENDPOINT=
AZURE_SEARCH_API_KEY=
STORAGE_ACCOUNT=
FUNCTION_APP_NAME=
FUNCTION_APP_URL=
```

## Step 1: Create the Resource Group

In the Azure Portal:

1. Open **Resource groups**.
2. Select **Create**.
3. Set **Resource group** to `closedloop-os-rg`.
4. Set **Region** to your selected region.
5. Select **Review + create**, then **Create**.

Success check:

- You can open the resource group and it is empty or only contains resources you intentionally added.

## Step 2: Create Cosmos DB

Create the account:

1. Open **Azure Cosmos DB**.
2. Select **Create**.
3. Choose **Azure Cosmos DB for NoSQL**.
4. Use resource group `closedloop-os-rg`.
5. Set account name to `closedloop-events` or a unique variant.
6. Set capacity mode to **Serverless** if available.
7. Keep public network access enabled for first setup unless you are already configuring private networking.
8. Select **Review + create**, then **Create**.

Create the database and containers:

1. Open the Cosmos account.
2. Go to **Data Explorer**.
3. Select **New Database**.
4. Database id: `closedloop-os`.
5. Create container `events` with partition key `/source_tool`.
6. Create container `relationships` with partition key `/relationship_type`.

You will need these values later:

- `COSMOS_ENDPOINT`: Cosmos account URI from **Keys**
- `COSMOS_KEY`: primary key from **Keys**
- `COSMOS_DATABASE_NAME`: `closedloop-os`
- `COSMOS_CONTAINER_NAME`: `events`

Success check:

- **Data Explorer** shows database `closedloop-os`.
- Database `closedloop-os` contains containers `events` and `relationships`.
- Container `events` uses partition key `/source_tool`.
- Container `relationships` uses partition key `/relationship_type`.

## Step 3: Create Key Vault

1. Open **Key vaults**.
2. Select **Create**.
3. Use resource group `closedloop-os-rg`.
4. Set vault name to `closedloop-secrets` or a unique variant.
5. Keep **Permission model** as either **Azure role-based access control** or **Vault access policy**. RBAC is preferred.
6. Select **Review + create**, then **Create**.

Add only the connector secrets you plan to use:

- `github-webhook-secret`
- `slack-signing-secret`
- `slack-bot-token`
- `linear-webhook-secret`
- `jira-access-token`
- `jira-webhook-secret`
- `confluence-access-token`
- `confluence-webhook-secret`
- `notion-access-token`
- `zendesk-webhook-secret`

The app setting `KEY_VAULT_URI` should look like:

```text
https://closedloop-secrets.vault.azure.net/
```

If you used a unique Key Vault name, use that exact URI instead.

Success check:

- You can open the vault.
- **Secrets** contains the connector secrets you added.
- You copied the vault URI into your notes.

## Step 4: Create Service Bus

1. Open **Service Bus**.
2. Select **Create**.
3. Use resource group `closedloop-os-rg`.
4. Set namespace to `closedloop-bus` or a unique variant.
5. Choose pricing tier **Standard**.
6. Select **Review + create**, then **Create**.

Create the queue:

1. Open the Service Bus namespace.
2. Go to **Queues**.
3. Select **+ Queue**.
4. Name: `raw-events`.
5. Set max delivery count to `10`.
6. Enable dead-lettering on message expiration.
7. Create the queue.

Get the connection string:

1. Open **Shared access policies** on the namespace.
2. Select `RootManageSharedAccessKey`, or create a narrower policy with send/listen permissions.
3. Copy the primary connection string.

You will need:

- `SERVICE_BUS_CONNECTION_STRING`
- `SERVICE_BUS_QUEUE_NAME=raw-events`

Success check:

- Namespace exists.
- Queue `raw-events` exists.
- You copied a connection string.

## Step 5: Create Azure OpenAI

1. Open **Azure OpenAI** or **Azure AI services**.
2. Create an Azure OpenAI account in the selected region.
3. Use resource group `closedloop-os-rg`.
4. Set account name to `closedloop-openai` or a unique variant.
5. After creation, open **Model deployments** in Azure AI Foundry.

Create these deployments:

- Deployment name `gpt-4o-mini`, model `gpt-4o-mini`
- Deployment name `text-embedding-3-small`, model `text-embedding-3-small`

If you choose different deployment names, put those exact names in the Function App settings.

You will need:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini`
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small`
- `AZURE_OPENAI_EMBEDDING_DIMENSIONS=1536`
- `AZURE_OPENAI_API_VERSION=2024-10-21`

Success check:

- Deployment `gpt-4o-mini` exists.
- Deployment `text-embedding-3-small` exists.
- You copied the endpoint and key from the Azure OpenAI resource.

## Step 6: Create Azure AI Search

1. Open **AI Search**.
2. Select **Create**.
3. Use resource group `closedloop-os-rg`.
4. Set service name to `closedloop-search` or a unique variant.
5. Choose the **Basic** pricing tier for initial setup.
6. Create the service.

The app creates or updates the `closedloop-knowledge` index at runtime when the knowledge store is used.

You will need:

- `AZURE_SEARCH_ENDPOINT`, usually `https://<service-name>.search.windows.net`
- `AZURE_SEARCH_API_KEY`, from **Keys**
- `AZURE_SEARCH_INDEX_NAME=closedloop-knowledge`

Success check:

- Search service opens successfully.
- You copied the endpoint and an admin key.
- It is OK if the index does not exist yet. The app creates `closedloop-knowledge` at runtime.

## Step 7: Create Storage for Azure Functions

1. Open **Storage accounts**.
2. Select **Create**.
3. Use resource group `closedloop-os-rg`.
4. Pick a globally unique lowercase name, for example `closedloopfuncstorage01`.
5. Choose the same region.
6. Standard performance and locally redundant storage are fine for initial setup.
7. Create the account.

Azure Functions needs this account for host state and triggers.

Success check:

- Storage account exists in `closedloop-os-rg`.
- The name is copied into your notes.

## Step 8: Create the Function App

This repo is structured around Azure Functions using [function_app.py](D:/Intellihub/function_app.py:1).

In the Azure Portal:

1. Open **Function App**.
2. Select **Create**.
3. Choose resource group `closedloop-os-rg`.
4. Pick a globally unique app name.
5. Runtime stack: **Python**.
6. Python version: **3.11**.
7. Hosting plan: **Consumption** is fine for first setup.
8. Select the storage account you created.
9. Create the Function App.

Success check:

- Function App opens in the Azure Portal.
- Overview page shows a default domain like `https://<app-name>.azurewebsites.net`.
- Copy that URL as `FUNCTION_APP_URL`.

## Step 9: Configure Function App Settings

Open your Function App, then go to **Settings > Environment variables** or **Configuration > Application settings**.

Add these settings:

```text
FUNCTIONS_WORKER_RUNTIME=python
COSMOS_ENDPOINT=<COSMOS_ENDPOINT>
COSMOS_KEY=<COSMOS_KEY>
COSMOS_DATABASE_NAME=closedloop-os
COSMOS_CONTAINER_NAME=events
KEY_VAULT_URI=https://closedloop-secrets.vault.azure.net/
SERVICE_BUS_CONNECTION_STRING=<SERVICE_BUS_CONNECTION_STRING>
SERVICE_BUS_QUEUE_NAME=raw-events
AZURE_OPENAI_ENDPOINT=<AZURE_OPENAI_ENDPOINT>
AZURE_OPENAI_API_KEY=<AZURE_OPENAI_API_KEY>
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_OPENAI_EMBEDDING_DIMENSIONS=1536
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_SEARCH_ENDPOINT=<AZURE_SEARCH_ENDPOINT>
AZURE_SEARCH_API_KEY=<AZURE_SEARCH_API_KEY>
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

Use direct environment values for the first deployment if you want the simplest path. Move connector secrets into Key Vault once the app is running.

Success check:

- Every setting above exists in the Function App.
- The Function App was restarted after saving settings.
- There are no placeholder values like `<COSMOS_ENDPOINT>` left.

## Step 10: Grant Key Vault Access

The code uses `DefaultAzureCredential()` in [secrets.py](D:/Intellihub/src/closedloop_os/secrets.py:1).

For the Azure-hosted Function App:

1. Open the Function App.
2. Go to **Identity**.
3. Enable **System assigned managed identity**.
4. Save.
5. Open the Key Vault.
6. If the vault uses RBAC, assign the Function App identity the **Key Vault Secrets User** role.
7. If the vault uses access policies, add a policy for the Function App identity with secret **Get** and **List** permissions.

Success check:

- Function App identity is enabled.
- Key Vault has either an RBAC role assignment or access policy for that identity.

## Step 11: Deploy the Code

Deploy with whichever method is easiest in your environment:

- Azure Functions extension in VS Code
- ZIP deploy from the Azure Portal or deployment center
- GitHub Actions
- Azure Functions Core Tools, if you later choose to use local tooling

For manual setup, the important part is that the Function App has Python 3.11, the app settings above, and this repo's function app files.

Beginner-friendly deployment option:

1. Install the **Azure Functions** extension in VS Code.
2. Sign in to Azure inside VS Code.
3. Open this folder: `D:\Intellihub`.
4. In the Azure panel, find your Function App.
5. Use **Deploy to Function App**.
6. Select the Function App you created.
7. Wait for deployment to finish.

Success check:

- Deployment completes without errors.
- The Function App overview shows the app is running.
- `https://<app-name>.azurewebsites.net/healthz` returns `{"status":"ok"}`.

## Step 12: Configure Webhooks

After deployment, point integrations at your Function App base URL:

- GitHub: `POST /api/connectors/github`
- Slack: `POST /api/connectors/slack`
- Linear: `POST /api/connectors/linear`
- Jira: `POST /api/connectors/jira`
- Confluence: `POST /api/connectors/confluence`
- Zendesk: `POST /api/connectors/zendesk`
- Meetings: `POST /api/connectors/meetings/upload`

Also verify:

- `GET /healthz`
- `/mcp`

## Step 13: Post-Deployment Validation Checklist

- `healthz` returns `{"status":"ok"}`
- Service Bus queue `raw-events` exists
- Cosmos containers `events` and `relationships` exist
- Azure OpenAI deployments exist with the names configured in app settings
- Azure AI Search service exists and the app can create `closedloop-knowledge`
- Function App identity can read Key Vault secrets if Key Vault is used
- GitHub or another webhook reaches the app and stores an event
- `semantic_search()` returns results after events are indexed
- `ask_intelligence()` returns a cited answer after events exist
- `get_entity_graph()` returns relationship edges after relationship-producing events exist

## Optional Infra Reference

The Bicep files are still useful as a resource checklist or for future automated deployment:

- [infra/main.bicep](D:/Intellihub/infra/main.bicep:1)
- [infra/modules/closedloop-resources.bicep](D:/Intellihub/infra/modules/closedloop-resources.bicep:1)

You can ignore them for manual Azure Portal setup.

## Known Gaps

- Connector OAuth tokens must already exist. The app does not yet run a full OAuth consent flow for Jira, Confluence, Slack, Notion, or Zendesk.
- The repo provisions a Container Apps environment only in Bicep. The primary runtime path here is Azure Functions.
- Function App code deployment is still a separate step from resource creation.
