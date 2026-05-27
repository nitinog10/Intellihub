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
