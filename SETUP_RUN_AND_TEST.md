# Setup, Run, and Test Guide for ClosedLoop OS

This guide explains how to set up the project locally, run the app, exercise every connector, and test the major behavior end to end.

If you are new to this project, start with [LOCAL_QUICKSTART.md](LOCAL_QUICKSTART.md). It gives the shortest safe path: setup, test locally, run the API, then configure Azure.

## Local First Rule

Do not create Azure resources until these local checks pass:

```powershell
cd D:\Intellihub
.\scripts\setup_local.ps1
.\scripts\test_all.ps1
```

Then run the app:

```powershell
.\scripts\run_local.ps1
```

In a second PowerShell window:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/healthz
```

Expected response:

```json
{"status":"ok"}
```

## What This Guide Covers

- local Python setup
- local configuration
- running the API
- running tests
- testing each connector
- testing classification pipeline
- testing semantic search
- testing intelligence queries
- testing meeting uploads and graph queries

## Project Entry Points

Important files:

- [main.py](main.py) — standalone Uvicorn runner
- [api.py](src/closedloop_os/api.py) — FastAPI routes + APScheduler lifespan
- [pipeline.py](src/closedloop_os/pipeline.py) — classification and processing pipeline
- [mcp_server.py](src/closedloop_os/mcp_server.py) — MCP tool surface
- [intelligence.py](src/closedloop_os/intelligence.py) — cited answer generation

## Step 1: Create a Virtual Environment

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## Step 2: Create Local Settings

Start from the sample:

```powershell
Copy-Item local.settings.sample.json local.settings.json
```

Or use a `.env` file (see [.env.example](.env.example) for the template).

For basic local dev without Azure, the app can still run with minimal config because some pieces fall back to in-memory behavior.

### Minimal local config

Useful if you only want to run tests and the API:

```json
{
  "IsEncrypted": false,
  "Values": {
    "COSMOS_ENDPOINT": "",
    "COSMOS_KEY": "",
    "COSMOS_DATABASE_NAME": "closedloop-os",
    "COSMOS_CONTAINER_NAME": "events",
    "AZURE_OPENAI_ENDPOINT": "",
    "AZURE_OPENAI_API_KEY": ""
  }
}
```

### What works without Azure

- unit tests
- API startup
- in-memory repository storage
- deterministic embeddings
- local semantic search fallback
- intelligence query layer on in-memory data

### What needs real Azure config

- Cosmos DB persistence
- Azure OpenAI classification and embeddings

## Step 3: Run the API Locally

```powershell
python main.py
```

Default local URL:

- `http://127.0.0.1:8000`

Useful endpoints:

- `GET /healthz`
- `POST /api/connectors/github`
- `POST /api/connectors/slack`
- `POST /api/connectors/linear`
- `POST /api/connectors/jira`
- `POST /api/connectors/confluence`
- `POST /api/connectors/zendesk`
- `POST /api/connectors/meetings/upload`
- `/mcp`

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/healthz
```

Expected response:

```json
{"status":"ok"}
```

## Step 4: Run the Automated Test Suite

```powershell
pytest
```

Current test coverage includes:

- GitHub mapping and webhook verification
- Slack connector behavior
- Linear connector behavior
- Jira and Confluence connectors
- classification threshold behavior
- semantic overlap and semantic search
- Zendesk connector and meeting upload
- intelligence query layer and timeline

Optional sanity check:

```powershell
python -m compileall src main.py
```

## Step 5: Local Connector Testing

### GitHub

The code expects:

- `X-GitHub-Event`
- `X-GitHub-Delivery`
- `X-Hub-Signature-256`

Example payload flow:

```powershell
$body = '{"ref":"refs/heads/main","repository":{"full_name":"org/repo"},"sender":{"login":"octocat"},"commits":[{"id":"abc"}],"head_commit":{"timestamp":"2026-05-27T08:00:00Z"}}'
```

In practice, the easiest path is the test suite:

- [tests/test_github_webhook.py](tests/test_github_webhook.py)

### Slack

Supported:

- `url_verification`
- `message`
- `file_shared`

Reference tests:

- [tests/test_slack_connector.py](tests/test_slack_connector.py)

### Linear

Supported:

- `Issue`
- `Comment`
- `Cycle`
- `Project`

Reference tests:

- [tests/test_linear_connector.py](tests/test_linear_connector.py)

### Jira

Supported:

- `issue_created`
- `issue_updated`
- `comment_created`
- `sprint_started`
- `sprint_closed`

Reference tests:

- [tests/test_jira_confluence_connectors.py](tests/test_jira_confluence_connectors.py)

### Confluence

The connector detects ADR/RFC style pages and marks them as decisions.

Reference tests:

- [tests/test_jira_confluence_connectors.py](tests/test_jira_confluence_connectors.py)

### Zendesk

Supported:

- `ticket.created`
- `ticket.updated`
- `sla.breached`
- `satisfaction_rated`

Special rule:

- `sla.breached` is forced to `importance_score = 0.95`

Reference tests:

- [tests/test_zendesk_and_meetings.py](tests/test_zendesk_and_meetings.py)

## Step 6: Testing Meeting Transcript Upload

Supported file types:

- `.txt`
- `.vtt`
- `.srt`
- `.json`

Example with PowerShell:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/connectors/meetings/upload `
  -F "file=@sample_meeting.txt"
```

Expected behavior:

1. the file is parsed
2. transcript lines are chunked
3. a raw meeting event is published
4. the classifier pipeline turns chunks into canonical meeting events
5. filler words are removed
6. entities and action items are stored in metadata
7. graph relationships are extracted
8. embeddings are generated for search

Key code:

- [transcripts.py](src/closedloop_os/transcripts.py)
- [pipeline.py](src/closedloop_os/pipeline.py)

## Step 7: Testing the Classification Pipeline

There are two modes:

### Heuristic fallback mode

Used when Azure OpenAI is not configured.

Good for local dev and tests.

### Azure OpenAI mode

Used when these are configured:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`

Classification model:

- `AZURE_OPENAI_DEPLOYMENT`, default `gpt-4o-mini`

Embedding model:

- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`, default `text-embedding-3-small`

## Step 8: Testing Semantic Search

Tool:

- `semantic_search(query_text, limit=10, source_tool=None)`

Backends:

- CosmosAwareKnowledgeStore when Cosmos DB is configured (vectors stored in `knowledge` container, searched in-memory)
- InMemoryKnowledgeStore otherwise (deterministic embeddings, in-memory cosine similarity)

Reference semantic tests:

- [tests/test_semantic_pipeline.py](tests/test_semantic_pipeline.py)

What to verify:

- relevant results rank near the top
- indexed meeting events are retrievable
- Jira and Linear overlap detection works

## Step 9: Testing Graph Relationships

Tool:

- `get_entity_graph(entity, limit=50)`

Relationship types currently supported:

- `IMPLEMENTS`
- `BLOCKED_BY`
- `ASSIGNED_TO`
- `MENTIONED_IN`
- `CAUSED_BY`
- `RESOLVED_BY`
- `DISCUSSED_IN`

Where they come from:

- transcript extraction
- classifier entity output
- event text heuristics

Reference test:

- [tests/test_zendesk_and_meetings.py](tests/test_zendesk_and_meetings.py)

## Step 10: Testing the Intelligence Query Layer

Main tool:

- `ask_intelligence(question)`

It returns:

- `answer`
- `confidence`
- `trust_score`
- `citations`
- `uncited_claims`
- `suggested_actions`
- `processing_time_ms`

Rules enforced by implementation:

- facts come only from retrieved sources
- factual sentences carry citations
- confidence is computed from evidence coverage and citation quality

Reference tests:

- [tests/test_intelligence.py](tests/test_intelligence.py)

Useful sample questions:

```text
What customer signals mention ENG-101?
What decisions were made about semantic search?
What action items came from the last standup?
What is the timeline for ENG-101?
```

## Step 11: Testing MCP Tools

The MCP server runs at:

- `http://127.0.0.1:8000/mcp`

It uses the Streamable HTTP transport.

You can test with any MCP client, or check the info endpoint:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/mcp-info
```

## Step 12: Testing Notion Sync

Notion sync runs as a background APScheduler job.

Configuration:

- `NOTION_ACCESS_TOKEN` — required for sync to run
- `NOTION_DATABASE_ID` — the Notion database to sync
- `NOTION_API_VERSION` — default `2022-06-28`
- `NOTION_SYNC_INTERVAL_MINUTES` — default `5`

When `NOTION_ACCESS_TOKEN` is set, the scheduler automatically polls Notion for updated pages every interval.

## Troubleshooting

### Cosmos DB connection fails

Check:

- `COSMOS_ENDPOINT` and `COSMOS_KEY` are set correctly
- the Cosmos DB account exists and is accessible
- the database and containers (`events`, `relationships`, `knowledge`) exist

### Azure OpenAI classification returns errors

Check:

- `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` are set
- the model deployments exist with the names configured in `AZURE_OPENAI_DEPLOYMENT` and `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`

### Semantic search returns no results

If Azure OpenAI is not configured, the app uses deterministic embeddings which are less accurate but still functional. Check that events have been ingested before searching.
