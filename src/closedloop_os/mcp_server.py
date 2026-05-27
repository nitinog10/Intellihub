from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from closedloop_os.models import EventQuery
from closedloop_os.persistence import build_repository

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
