from __future__ import annotations

import json
from abc import ABC, abstractmethod

from azure.servicebus import ServiceBusClient, ServiceBusMessage

from closedloop_os.config import get_settings
from closedloop_os.models import CanonicalEvent, RawConnectorEvent

PublishableEvent = CanonicalEvent | RawConnectorEvent


class EventPublisher(ABC):
    @abstractmethod
    def publish_raw_event(self, event: PublishableEvent) -> None:
        raise NotImplementedError


class NullPublisher(EventPublisher):
    def publish_raw_event(self, event: PublishableEvent) -> None:
        return None


class LocalProcessingPublisher(EventPublisher):
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


class ServiceBusPublisher(EventPublisher):
    def __init__(self) -> None:
        settings = get_settings()
        self._queue_name = settings.service_bus_queue_name
        self._client = ServiceBusClient.from_connection_string(settings.service_bus_connection_string)

    def publish_raw_event(self, event: PublishableEvent) -> None:
        body = json.dumps(event.model_dump(mode="json"))
        with self._client:
            sender = self._client.get_queue_sender(queue_name=self._queue_name)
            with sender:
                sender.send_messages(ServiceBusMessage(body))


def build_publisher() -> EventPublisher:
    settings = get_settings()
    if settings.local_runtime_mode:
        return LocalProcessingPublisher()
    if settings.service_bus_connection_string:
        return ServiceBusPublisher()
    return NullPublisher()
