from __future__ import annotations

from closedloop_os.messaging import EventPublisher
from closedloop_os.models import RawConnectorEvent


class RawIngestService:
    def __init__(self, publisher: EventPublisher) -> None:
        self.publisher = publisher

    def ingest(self, source_tool: str, event_name: str, payload: dict, delivery_id: str) -> RawConnectorEvent:
        event = RawConnectorEvent(
            source_tool=source_tool,
            event_name=event_name,
            delivery_id=delivery_id,
            payload=payload,
        )
        self.publisher.publish_raw_event(event)
        return event
