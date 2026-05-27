from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from azure.cosmos import CosmosClient

from closedloop_os.config import get_settings
from closedloop_os.models import CanonicalEvent, EventQuery


class EventRepository(ABC):
    @abstractmethod
    def upsert_event(self, event: CanonicalEvent) -> CanonicalEvent:
        raise NotImplementedError

    @abstractmethod
    def query_events(self, query: EventQuery, source_tool: str = "github") -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_event_by_id(self, event_id: str) -> dict[str, Any] | None:
        raise NotImplementedError


class CosmosEventRepository(EventRepository):
    def __init__(self) -> None:
        settings = get_settings()
        client = CosmosClient(url=settings.cosmos_endpoint, credential=settings.cosmos_key)
        database = client.get_database_client(settings.cosmos_database_name)
        self.container = database.get_container_client(settings.cosmos_container_name)

    def upsert_event(self, event: CanonicalEvent) -> CanonicalEvent:
        self.container.upsert_item(event.model_dump(mode="json"))
        return event

    def query_events(self, query: EventQuery, source_tool: str = "github") -> list[dict[str, Any]]:
        sql = ["SELECT TOP @limit * FROM c WHERE c.source_tool = @source_tool"]
        parameters = [
            {"name": "@limit", "value": query.limit},
            {"name": "@source_tool", "value": source_tool},
        ]

        if query.project:
            sql.append("AND c.project = @project")
            parameters.append({"name": "@project", "value": query.project})
        if query.actor:
            sql.append("AND c.actor = @actor")
            parameters.append({"name": "@actor", "value": query.actor})
        if query.event_type:
            sql.append("AND STARTSWITH(c.event_type, @event_type)")
            parameters.append({"name": "@event_type", "value": query.event_type})

        sql.append("ORDER BY c.timestamp DESC")
        items = self.container.query_items(
            query=" ".join(sql),
            parameters=parameters,
            enable_cross_partition_query=True,
        )
        return list(items)

    def get_event_by_id(self, event_id: str) -> dict[str, Any] | None:
        query = self.container.query_items(
            query="SELECT TOP 1 * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": event_id}],
            enable_cross_partition_query=True,
        )
        return next(iter(query), None)


class InMemoryEventRepository(EventRepository):
    def __init__(self) -> None:
        self._events: dict[str, dict[str, Any]] = {}

    def upsert_event(self, event: CanonicalEvent) -> CanonicalEvent:
        self._events[event.id] = event.model_dump(mode="json")
        return event

    def query_events(self, query: EventQuery, source_tool: str = "github") -> list[dict[str, Any]]:
        events = [event for event in self._events.values() if event["source_tool"] == source_tool]
        if query.project:
            events = [event for event in events if event["project"] == query.project]
        if query.actor:
            events = [event for event in events if event["actor"] == query.actor]
        if query.event_type:
            events = [event for event in events if event["event_type"].startswith(query.event_type)]
        events.sort(key=lambda item: item["timestamp"], reverse=True)
        return events[: query.limit]

    def get_event_by_id(self, event_id: str) -> dict[str, Any] | None:
        return self._events.get(event_id)


def build_repository() -> EventRepository:
    settings = get_settings()
    if settings.has_cosmos:
        return CosmosEventRepository()
    return InMemoryEventRepository()
