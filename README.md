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



