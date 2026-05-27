# IntelliHub — Phase 1  
### AI-Native Organizational Intelligence Infrastructure

IntelliHub Phase 1 bootstraps the foundation of an enterprise-grade organizational intelligence system built on Microsoft Azure and the Model Context Protocol (MCP).

This phase focuses on:
- GitHub event ingestion
- Canonical event normalization
- Cosmos DB persistence
- MCP-based querying
- Azure-native infrastructure deployment

The system converts GitHub activity into structured intelligence that can be queried by AI systems like Claude, GPT, Cursor, or any MCP-compatible client.

---

# 🚀 Features

## GitHub Webhook Intake
Receive and normalize GitHub events through Azure-backed webhook endpoints.

Supported GitHub events:
- `push`
- `pull_request`
- `pull_request_review`
- `issues`
- `workflow_run`
- `release`

---

## Canonical Event System
All incoming events are transformed into a unified schema for future AI reasoning, semantic search, and analytics.

Example:

```json
{
  "id": "uuid",
  "source_tool": "github",
  "event_type": "github.pull_request.opened",
  "title": "PR opened: Add webhook flow",
  "description": "Normalized event description",
  "actor": "octocat",
  "project": "org/repo",
  "importance_score": 0.82,
  "timestamp": "2026-05-27T12:00:00Z",
  "raw_payload": {},
  "metadata": {}
}
```

## Azure Cosmos DB Persistence

Normalized events are stored inside Azure Cosmos DB for:

event history
querying
future vector indexing
AI retrieval pipelines
MCP Server Integration

Expose intelligence tools through MCP.

Available tools:

query_github_events()
get_event_by_id()

MCP endpoint:

/mcp

Optional Service Bus Fan-Out

Raw events can optionally be published to Azure Service Bus for:

async AI processing
classification pipelines
downstream enrichment

Enabled only when:

SERVICE_BUS_CONNECTION_STRING

is configured.

🏗️ Architecture
GitHub Webhooks
        │
        ▼
Azure Functions / FastAPI
        │
        ▼
Canonical Event Normalizer
        │
 ┌──────┴────────┐
 ▼               ▼
Cosmos DB    Service Bus (optional)
        │
        ▼
MCP Server
        │
        ▼
Claude / GPT / Cursor
📂 Project Structure
.
├── api/
│   ├── connectors/
│   │   └── github/
│   ├── models/
│   ├── services/
│   └── utils/
│
├── infra/
│   └── main.bicep
│
├── mcp/
│   └── server.py
│
├── tests/
│
├── .github/
│   └── workflows/
│       └── deploy.yml
│
├── main.py
├── requirements.txt
├── local.settings.sample.json
└── README.md


⚡ API Endpoints
GitHub Connector
POST /api/connectors/github



Features:
GitHub signature verification
Event normalization
Cosmos DB persistence
Optional Service Bus publishing
Health Check
GET /healthz



Returns service health status.
Example:
{
  "status": "ok"
}

MCP Endpoint
/mcp
Streamable HTTP endpoint exposing MCP tools.


🧠 MCP Tools
query_github_events(days, event_type=None)

Retrieve recent GitHub events filtered by:

time window
event type


Example:
query_github_events(days=7)
get_event_by_id(event_id)




🛠️ Local Development Setup

1. Create Virtual Environment
python -m venv .venv

2. Activate Environment
Windows
. .venv/Scripts/activate

Linux/macOS
source .venv/bin/activate

3. Install Dependencies
pip install -e ".[dev]"

4. Configure Environment
copy local.settings.sample.json local.settings.json


5. Run Application
python main.py

6. Run Tests
pytest
☁️ Azure Infrastructure

Infrastructure is provisioned using Bicep.

Resources created:

Azure Resource Group
Azure Cosmos DB
Azure Functions
Azure Key Vault
Azure Service Bus
Azure Container Apps

🚀 Azure Deployment
Validate Infrastructure
az deployment sub validate \
  --location eastus \
  --template-file infra/main.bicep
Deploy Infrastructure
az deployment sub create \
  --location eastus \
  --template-file infra/main.bicep


🔐 Environment Variables
Required
COSMOS_ENDPOINT=
COSMOS_KEY=
COSMOS_DATABASE_NAME=closedloop-os
COSMOS_CONTAINER_NAME=events

GITHUB_WEBHOOK_SECRET=
Optional
SERVICE_BUS_CONNECTION_STRING=
KEY_VAULT_URL=

🔒 Security
Implemented:

GitHub webhook signature verification
Azure Key Vault integration
Secure environment variable loading
Async request handling
📡 GitHub Actions CI/CD



Workflow path:
.github/workflows/deploy.yml
📌 Assumptions
Cosmos SQL database name defaults to:
closedloop-os
GitHub secret can come from:
GITHUB_WEBHOOK_SECRET
Azure Key Vault secret:
github-webhook-secret

