from __future__ import annotations

from abc import ABC, abstractmethod

from closedloop_os.models import CanonicalEvent, RawConnectorEvent

PublishableEvent = CanonicalEvent | RawConnectorEvent


class EventPublisher(ABC):
    @abstractmethod
    def publish_raw_event(self, event: PublishableEvent) -> None:
        raise NotImplementedError


class NullPublisher(EventPublisher):
    """No-op publisher for testing — discards all events."""

    def publish_raw_event(self, event: PublishableEvent) -> None:
        return None


class LocalProcessingPublisher(EventPublisher):
    """Synchronous in-process publisher — processes events immediately without a message queue.

    This replaces the Azure Service Bus publisher. All events are classified and
    stored in the same process that receives the webhook.
    """

    def publish_raw_event(self, event: PublishableEvent) -> None:
        from closedloop_os.classification import build_classifier
        from closedloop_os.models import RawConnectorEvent
        from closedloop_os.persistence import build_repository
        from closedloop_os.pipeline import ClassificationPipeline
        from closedloop_os.search import build_knowledge_store

        if isinstance(event, RawConnectorEvent):
            pipeline = ClassificationPipeline(
                repository=build_repository(),
                classifier=build_classifier(),
                knowledge_store=build_knowledge_store(),
            )
            pipeline.process(event)
            return

        repository = build_repository()
        knowledge_store = build_knowledge_store()
        repository.upsert_event(event)
        knowledge_store.upsert_event(event)


def build_publisher() -> EventPublisher:
    """Always returns LocalProcessingPublisher — no Service Bus needed."""
    return LocalProcessingPublisher()
