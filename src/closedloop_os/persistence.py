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

    @abstractmethod
    def search_decisions(self, query_text: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_slack_context(
        self,
        channel: str,
        thread_ts: str | None = None,
        user: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_linear_sprint_status(
        self,
        project: str | None = None,
        cycle: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_jira_epic_status(self, epic_key: str | None = None, project: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_notion_decisions(self, query_text: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_latest_timestamp(self, source_tool: str, event_prefix: str | None = None) -> str | None:
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

    def search_decisions(self, query_text: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        sql = [
            "SELECT TOP @limit * FROM c",
            "WHERE IS_DEFINED(c.metadata.classification.has_decision)",
            "AND c.metadata.classification.has_decision = true",
        ]
        parameters = [{"name": "@limit", "value": limit}]
        if query_text:
            sql.append("AND (CONTAINS(LOWER(c.title), @query_text) OR CONTAINS(LOWER(c.description), @query_text))")
            parameters.append({"name": "@query_text", "value": query_text.lower()})
        sql.append("ORDER BY c.timestamp DESC")
        return list(
            self.container.query_items(
                query=" ".join(sql),
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )

    def get_slack_context(
        self,
        channel: str,
        thread_ts: str | None = None,
        user: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        sql = ["SELECT TOP @limit * FROM c WHERE c.source_tool = 'slack' AND c.metadata.channel = @channel"]
        parameters = [{"name": "@limit", "value": limit}, {"name": "@channel", "value": channel}]
        if thread_ts:
            sql.append("AND c.metadata.thread_ts = @thread_ts")
            parameters.append({"name": "@thread_ts", "value": thread_ts})
        if user:
            sql.append("AND c.metadata.user = @user")
            parameters.append({"name": "@user", "value": user})
        sql.append("ORDER BY c.timestamp DESC")
        return list(
            self.container.query_items(
                query=" ".join(sql),
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )

    def get_linear_sprint_status(
        self,
        project: str | None = None,
        cycle: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        sql = ["SELECT TOP @limit * FROM c WHERE c.source_tool = 'linear'"]
        parameters = [{"name": "@limit", "value": limit}]
        if project:
            sql.append("AND c.project = @project")
            parameters.append({"name": "@project", "value": project})
        if cycle:
            sql.append("AND c.metadata.cycle = @cycle")
            parameters.append({"name": "@cycle", "value": cycle})
        sql.append("ORDER BY c.timestamp DESC")
        return list(
            self.container.query_items(
                query=" ".join(sql),
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )

    def get_jira_epic_status(self, epic_key: str | None = None, project: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        sql = ["SELECT TOP @limit * FROM c WHERE c.source_tool = 'jira'"]
        parameters = [{"name": "@limit", "value": limit}]
        if epic_key:
            sql.append("AND c.metadata.epic_key = @epic_key")
            parameters.append({"name": "@epic_key", "value": epic_key})
        if project:
            sql.append("AND c.project = @project")
            parameters.append({"name": "@project", "value": project})
        sql.append("ORDER BY c.timestamp DESC")
        return list(
            self.container.query_items(
                query=" ".join(sql),
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )

    def get_notion_decisions(self, query_text: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        sql = [
            "SELECT TOP @limit * FROM c",
            "WHERE c.source_tool = 'notion'",
            "AND IS_DEFINED(c.metadata.classification.has_decision)",
            "AND c.metadata.classification.has_decision = true",
        ]
        parameters = [{"name": "@limit", "value": limit}]
        if query_text:
            sql.append("AND (CONTAINS(LOWER(c.title), @query_text) OR CONTAINS(LOWER(c.description), @query_text))")
            parameters.append({"name": "@query_text", "value": query_text.lower()})
        sql.append("ORDER BY c.timestamp DESC")
        return list(
            self.container.query_items(
                query=" ".join(sql),
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )

    def get_latest_timestamp(self, source_tool: str, event_prefix: str | None = None) -> str | None:
        sql = ["SELECT TOP 1 c.timestamp FROM c WHERE c.source_tool = @source_tool"]
        parameters = [{"name": "@source_tool", "value": source_tool}]
        if event_prefix:
            sql.append("AND STARTSWITH(c.event_type, @event_prefix)")
            parameters.append({"name": "@event_prefix", "value": event_prefix})
        sql.append("ORDER BY c.timestamp DESC")
        items = list(
            self.container.query_items(
                query=" ".join(sql),
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )
        return items[0]["timestamp"] if items else None


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

    def search_decisions(self, query_text: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        events = [
            event
            for event in self._events.values()
            if event.get("metadata", {}).get("classification", {}).get("has_decision") is True
        ]
        if query_text:
            needle = query_text.lower()
            events = [
                event
                for event in events
                if needle in event.get("title", "").lower() or needle in event.get("description", "").lower()
            ]
        events.sort(key=lambda item: item["timestamp"], reverse=True)
        return events[:limit]

    def get_slack_context(
        self,
        channel: str,
        thread_ts: str | None = None,
        user: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        events = [
            event
            for event in self._events.values()
            if event.get("source_tool") == "slack" and event.get("metadata", {}).get("channel") == channel
        ]
        if thread_ts:
            events = [event for event in events if event.get("metadata", {}).get("thread_ts") == thread_ts]
        if user:
            events = [event for event in events if event.get("metadata", {}).get("user") == user]
        events.sort(key=lambda item: item["timestamp"], reverse=True)
        return events[:limit]

    def get_linear_sprint_status(
        self,
        project: str | None = None,
        cycle: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        events = [event for event in self._events.values() if event.get("source_tool") == "linear"]
        if project:
            events = [event for event in events if event.get("project") == project]
        if cycle:
            events = [event for event in events if event.get("metadata", {}).get("cycle") == cycle]
        events.sort(key=lambda item: item["timestamp"], reverse=True)
        return events[:limit]

    def get_jira_epic_status(self, epic_key: str | None = None, project: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        events = [event for event in self._events.values() if event.get("source_tool") == "jira"]
        if epic_key:
            events = [event for event in events if event.get("metadata", {}).get("epic_key") == epic_key]
        if project:
            events = [event for event in events if event.get("project") == project]
        events.sort(key=lambda item: item["timestamp"], reverse=True)
        return events[:limit]

    def get_notion_decisions(self, query_text: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        events = [
            event
            for event in self._events.values()
            if event.get("source_tool") == "notion"
            and event.get("metadata", {}).get("classification", {}).get("has_decision") is True
        ]
        if query_text:
            needle = query_text.lower()
            events = [
                event
                for event in events
                if needle in event.get("title", "").lower() or needle in event.get("description", "").lower()
            ]
        events.sort(key=lambda item: item["timestamp"], reverse=True)
        return events[:limit]

    def get_latest_timestamp(self, source_tool: str, event_prefix: str | None = None) -> str | None:
        events = [event for event in self._events.values() if event.get("source_tool") == source_tool]
        if event_prefix:
            events = [event for event in events if event.get("event_type", "").startswith(event_prefix)]
        events.sort(key=lambda item: item["timestamp"], reverse=True)
        return events[0]["timestamp"] if events else None


def build_repository() -> EventRepository:
    settings = get_settings()
    if settings.has_cosmos:
        return CosmosEventRepository()
    return InMemoryEventRepository()
