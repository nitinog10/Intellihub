from __future__ import annotations

import json
from abc import ABC, abstractmethod

from azure.servicebus import ServiceBusClient, ServiceBusMessage

from closedloop_os.config import get_settings
from closedloop_os.models import CanonicalEvent


class EventPublisher(ABC):
    @abstractmethod
    def publish_raw_event(self, event: CanonicalEvent) -> None:
        raise NotImplementedError


class NullPublisher(EventPublisher):
    def publish_raw_event(self, event: CanonicalEvent) -> None:
        return None


class ServiceBusPublisher(EventPublisher):
    def __init__(self) -> None:
        settings = get_settings()
        self._queue_name = settings.service_bus_queue_name
        self._client = ServiceBusClient.from_connection_string(settings.service_bus_connection_string)

    def publish_raw_event(self, event: CanonicalEvent) -> None:
        body = json.dumps(event.model_dump(mode="json"))
        with self._client:
            sender = self._client.get_queue_sender(queue_name=self._queue_name)
            with sender:
                sender.send_messages(ServiceBusMessage(body))


def build_publisher() -> EventPublisher:
    settings = get_settings()
    if settings.service_bus_connection_string:
        return ServiceBusPublisher()
    return NullPublisher()
