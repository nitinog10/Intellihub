# Setup, Run, and Test Guide for ClosedLoop OS

This guide explains how to set up the project locally, run the app, exercise every connector, and test the major behavior end to end.

## What This Guide Covers

- local Python setup
- local configuration
- running the API
- running tests
- testing each connector
- testing Service Bus driven classification
- testing semantic search
- testing intelligence queries
- testing meeting uploads and graph queries

## Project Entry Points

Important files:

- [main.py](D:/Intellihub/main.py:1)
- [function_app.py](D:/Intellihub/function_app.py:1)
- [api.py](D:/Intellihub/src/closedloop_os/api.py:1)
- [pipeline.py](D:/Intellihub/src/closedloop_os/pipeline.py:1)
- [mcp_server.py](D:/Intellihub/src/closedloop_os/mcp_server.py:1)
- [intelligence.py](D:/Intellihub/src/closedloop_os/intelligence.py:1)

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

For basic local dev without Azure, the app can still run with minimal config because some pieces fall back to in-memory behavior.

### Minimal local config

Useful if you only want to run tests and the API:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "COSMOS_ENDPOINT": "",
    "COSMOS_KEY": "",
    "COSMOS_DATABASE_NAME": "closedloop-os",
    "COSMOS_CONTAINER_NAME": "events",
    "SERVICE_BUS_CONNECTION_STRING": "",
    "SERVICE_BUS_QUEUE_NAME": "raw-events",
    "AZURE_OPENAI_ENDPOINT": "",
    "AZURE_OPENAI_API_KEY": "",
    "AZURE_SEARCH_ENDPOINT": "",
    "AZURE_SEARCH_API_KEY": ""
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

- Cosmos persistence
- Service Bus raw event publishing
- Azure OpenAI classification
- Azure AI Search vector index
- Key Vault secret resolution

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
python -m compileall src function_app.py main.py
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

- [tests/test_github_webhook.py](D:/Intellihub/tests/test_github_webhook.py:1)

### Slack

Supported:

- `url_verification`
- `message`
- `file_shared`

Reference tests:

- [tests/test_slack_connector.py](D:/Intellihub/tests/test_slack_connector.py:1)

### Linear

Supported:

- `Issue`
- `Comment`
- `Cycle`
- `Project`

Reference tests:

- [tests/test_linear_connector.py](D:/Intellihub/tests/test_linear_connector.py:1)

### Jira

Supported:

- `issue_created`
- `issue_updated`
- `comment_created`
- `sprint_started`
- `sprint_closed`

Reference tests:

- [tests/test_jira_confluence_connectors.py](D:/Intellihub/tests/test_jira_confluence_connectors.py:1)

### Confluence

The connector detects ADR/RFC style pages and marks them as decisions.

Reference tests:

- [tests/test_jira_confluence_connectors.py](D:/Intellihub/tests/test_jira_confluence_connectors.py:1)

### Zendesk

Supported:

- `ticket.created`
- `ticket.updated`
- `sla.breached`
- `satisfaction_rated`

Special rule:

- `sla.breached` is forced to `importance_score = 0.95`

Reference tests:

- [tests/test_zendesk_and_meetings.py](D:/Intellihub/tests/test_zendesk_and_meetings.py:1)

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

- [transcripts.py](D:/Intellihub/src/closedloop_os/transcripts.py:1)
- [pipeline.py](D:/Intellihub/src/closedloop_os/pipeline.py:1)

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

- Azure AI Search when configured
- in-memory fallback otherwise

Reference semantic tests:

- [tests/test_semantic_pipeline.py](D:/Intellihub/tests/test_semantic_pipeline.py:1)

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

- [tests/test_zendesk_and_meetings.py](D:/Intellihub/tests/test_zendesk_and_meetings.py:1)

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

- [tests/test_intelligence.py](D:/Intellihub/tests/test_intelligence.py:1)

Useful sample questions:

```text
What customer signals mention ENG-101?
What decisions were made about semantic search?
What action items came from the last standup?
What is the timeline for ENG-101?
```

## Step 11: Testing MCP Tools

Current tool surface includes:

- `query_github_events`
- `get_event_by_id`
- `search_decisions`
- `get_slack_context`
- `get_linear_sprint_status`
- `semantic_search`
- `get_jira_epic_status`
- `get_notion_decisions`
- `analyze_meeting`
- `get_customer_signals`
- `get_entity_graph`
- `get_action_items`
- `ask_intelligence`
- `get_timeline`

Implementation:

- [mcp_server.py](D:/Intellihub/src/closedloop_os/mcp_server.py:1)

To test the MCP endpoint in an integrated environment:

1. run the app
2. point your MCP client at `/mcp`
3. call the tools listed above

## Step 12: End-to-End Local Validation Checklist

Use this sequence when you want to validate the whole stack locally:

1. `pip install -e ".[dev]"`
2. `python main.py`
3. verify `GET /healthz`
4. run `pytest`
5. upload a meeting transcript
6. trigger at least one webhook style connector
7. call semantic search
8. call `get_entity_graph`
9. call `ask_intelligence`
10. call `get_timeline`

## Troubleshooting

### API starts but no events persist

Likely causes:

- no Cosmos settings
- intentional fallback to in-memory repository
- the process restarted and in-memory state was lost

### Semantic search returns weak results

Likely causes:

- Azure AI Search is not configured
- the app is using deterministic local embeddings
- no events were indexed yet

### `ask_intelligence()` gives a thin answer

Likely causes:

- not enough source events available
- the question does not match stored event text well
- retrieval is evidence-first and intentionally conservative

### Key Vault secrets do not resolve

Likely causes:

- `KEY_VAULT_URI` missing
- wrong secret names
- no Azure identity for the runtime

### Service Bus trigger does not fire locally

Likely causes:

- no Service Bus connection string
- the raw event was never published
- local function host is not being used for queue-trigger execution

## Recommended Daily Commands

Setup:

```powershell
.venv\Scripts\activate
pip install -e ".[dev]"
```

Run app:

```powershell
python main.py
```

Run tests:

```powershell
pytest
```

Run compile sanity check:

```powershell
python -m compileall src function_app.py main.py
```
