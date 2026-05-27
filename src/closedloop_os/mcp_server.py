from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from closedloop_os.models import EventQuery
from closedloop_os.persistence import build_repository
from closedloop_os.search import build_knowledge_store

mcp = FastMCP("ClosedLoop OS MCP", stateless_http=True, json_response=True)


@mcp.tool()
def query_github_events(
    project: str | None = None,
    actor: str | None = None,
    event_type: str | None = None,
    limit: int = 25,
) -> list[dict]:
    """Query normalized GitHub events from ClosedLoop OS."""
    repository = build_repository()
    query = EventQuery(project=project, actor=actor, event_type=event_type, limit=limit)
    return repository.query_events(query=query, source_tool="github")


@mcp.tool()
def get_event_by_id(event_id: str) -> dict | None:
    """Fetch a single event by its canonical id."""
    repository = build_repository()
    return repository.get_event_by_id(event_id)


@mcp.tool()
def search_decisions(query_text: str | None = None, limit: int = 25) -> list[dict]:
    """Search classified Slack and Linear events that contain decisions."""
    repository = build_repository()
    return repository.search_decisions(query_text=query_text, limit=limit)


@mcp.tool()
def get_slack_context(
    channel: str,
    thread_ts: str | None = None,
    user: str | None = None,
    limit: int = 25,
) -> list[dict]:
    """Fetch classified Slack context by channel, optionally scoped to thread or user."""
    repository = build_repository()
    return repository.get_slack_context(channel=channel, thread_ts=thread_ts, user=user, limit=limit)


@mcp.tool()
def get_linear_sprint_status(
    project: str | None = None,
    cycle: str | None = None,
    limit: int = 25,
) -> list[dict]:
    """Fetch recent Linear issue, comment, cycle, and project events for sprint status."""
    repository = build_repository()
    return repository.get_linear_sprint_status(project=project, cycle=cycle, limit=limit)


@mcp.tool()
def semantic_search(query_text: str, limit: int = 10, source_tool: str | None = None) -> list[dict]:
    """Run semantic search across indexed ClosedLoop knowledge."""
    knowledge_store = build_knowledge_store()
    return knowledge_store.semantic_search(query_text=query_text, limit=limit, source_tool=source_tool)


@mcp.tool()
def get_jira_epic_status(epic_key: str | None = None, project: str | None = None, limit: int = 25) -> list[dict]:
    """Fetch recent Jira events for an epic or project."""
    repository = build_repository()
    return repository.get_jira_epic_status(epic_key=epic_key, project=project, limit=limit)


@mcp.tool()
def get_notion_decisions(query_text: str | None = None, limit: int = 25) -> list[dict]:
    """Fetch recent Notion pages classified as decisions."""
    repository = build_repository()
    return repository.get_notion_decisions(query_text=query_text, limit=limit)


@mcp.tool()
def analyze_meeting(meeting_id: str, limit: int = 100) -> list[dict]:
    """Fetch transcript-derived meeting events for a meeting id."""
    repository = build_repository()
    return repository.analyze_meeting(meeting_id=meeting_id, limit=limit)


@mcp.tool()
def get_customer_signals(limit: int = 25) -> list[dict]:
    """Fetch recent Zendesk-driven customer signals ordered by importance."""
    repository = build_repository()
    return repository.get_customer_signals(limit=limit)


@mcp.tool()
def get_entity_graph(entity: str, limit: int = 50) -> list[dict]:
    """Fetch graph relationships touching a named entity."""
    repository = build_repository()
    return repository.get_entity_graph(entity=entity, limit=limit)


@mcp.tool()
def get_action_items(query_text: str | None = None, limit: int = 25) -> list[dict]:
    """Fetch events that contain extracted action items."""
    repository = build_repository()
    return repository.get_action_items(query_text=query_text, limit=limit)
