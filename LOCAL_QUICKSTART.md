# ClosedLoop OS Beginner Quickstart

Use this file first. The goal is:

1. prove the app works on your laptop
2. run the test suite
3. only then create Azure resources
4. deploy after Azure settings are ready

You do not need Azure to finish the local test steps.

## Part 1: Local Test Before Azure

### Step 1: Open PowerShell in the project folder

```powershell
cd D:\Intellihub
```

Check that you are in the right folder:

```powershell
Get-ChildItem
```

You should see files like:

- `main.py`
- `function_app.py`
- `pyproject.toml`
- `local.settings.sample.json`

### Step 2: Run the local setup script

```powershell
.\scripts\setup_local.ps1
```

This creates `.venv`, installs Python packages, and creates `local.settings.json` if it does not already exist.

If PowerShell blocks the script, run this once in the same PowerShell window:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then run setup again:

```powershell
.\scripts\setup_local.ps1
```

### Step 3: Run all local tests

```powershell
.\scripts\test_all.ps1
```

This should run:

- `pytest`
- Python compile check

If this passes, the code is healthy locally.

### Step 4: Start the local API

```powershell
.\scripts\run_local.ps1
```

Leave this PowerShell window open. The app should run at:

```text
http://127.0.0.1:8000
```

### Step 5: Open a second PowerShell window

In the second window:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/healthz
```

Expected response:

```json
{"status":"ok"}
```

If you see that, local API startup works.

### Step 6: Stop the local app

Go back to the first PowerShell window and press:

```text
Ctrl+C
```

## Part 2: What Works Locally Without Azure

These should work before Azure exists:

- app startup
- health check
- unit tests
- in-memory event storage
- deterministic local embeddings
- local semantic search fallback
- intelligence logic against local test data

These need Azure later:

- persistent Cosmos DB storage
- Service Bus queue processing
- Azure OpenAI classification
- Azure AI Search indexing
- Key Vault secret lookup

## Part 3: Azure Setup Order

After local tests pass, use the Azure Portal guide:

- [AZURE_SETUP.md](D:/Intellihub/AZURE_SETUP.md:1)

Create Azure resources in this order:

1. Resource Group
2. Cosmos DB account, database, and containers
3. Key Vault
4. Service Bus namespace and queue
5. Azure OpenAI account and deployments
6. Azure AI Search
7. Storage Account
8. Function App
9. Function App environment variables
10. Function App managed identity and Key Vault access
11. Code deployment
12. Webhook setup
13. Post-deployment validation

You can print a short checklist with:

```powershell
.\scripts\azure_prep_checklist.ps1
```

## Part 4: The Values You Must Collect From Azure

Keep these in a temporary note while you create resources:

```text
COSMOS_ENDPOINT=
COSMOS_KEY=
KEY_VAULT_URI=
SERVICE_BUS_CONNECTION_STRING=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_SEARCH_ENDPOINT=
AZURE_SEARCH_API_KEY=
FUNCTION_APP_NAME=
FUNCTION_APP_URL=
```

These become Function App settings during deployment.

## Part 5: Full Local Testing Guide

For deeper connector and end-to-end testing notes:

- [SETUP_RUN_AND_TEST.md](D:/Intellihub/SETUP_RUN_AND_TEST.md:1)
