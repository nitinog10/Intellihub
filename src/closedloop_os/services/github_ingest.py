from __future__ import annotations

from closedloop_os.mappers.github import map_github_event
from closedloop_os.messaging import EventPublisher
from closedloop_os.models import CanonicalEvent
from closedloop_os.persistence import EventRepository


SUPPORTED_GITHUB_EVENTS = {
    "push",
    "pull_request",
    "issues",
    "pull_request_review",
    "release",
    "workflow_run",
}


class GitHubIngestService:
    def __init__(self, repository: EventRepository, publisher: EventPublisher) -> None:
        self.repository = repository
        self.publisher = publisher

    def ingest(self, event_name: str, payload: dict, delivery_id: str) -> CanonicalEvent:
        if event_name not in SUPPORTED_GITHUB_EVENTS:
            raise ValueError(f"Unsupported GitHub event '{event_name}'.")

        event = map_github_event(event_name=event_name, payload=payload, delivery_id=delivery_id)
        self.repository.upsert_event(event)
        self.publisher.publish_raw_event(event)
        return event
