from __future__ import annotations

import json

from closedloop_os.classification import EventClassifier, build_classifier
from closedloop_os.mappers.linear import map_linear_event
from closedloop_os.mappers.slack import map_slack_event
from closedloop_os.models import CanonicalEvent, RawConnectorEvent
from closedloop_os.persistence import EventRepository, build_repository

MIN_IMPORTANCE_SCORE = 0.3


class ClassificationPipeline:
    def __init__(self, repository: EventRepository, classifier: EventClassifier) -> None:
        self.repository = repository
        self.classifier = classifier

    def process(self, raw_event: RawConnectorEvent) -> CanonicalEvent | None:
        classification = self.classifier.classify(raw_event)
        if classification.importance_score <= MIN_IMPORTANCE_SCORE:
            return None

        if raw_event.source_tool == "slack":
            event = map_slack_event(raw_event, classification)
        elif raw_event.source_tool == "linear":
            event = map_linear_event(raw_event, classification)
        else:
            raise ValueError(f"Unsupported pipeline source: {raw_event.source_tool}")

        self.repository.upsert_event(event)
        return event


def process_raw_event_message(body: str | bytes) -> CanonicalEvent | None:
    raw = body.decode("utf-8") if isinstance(body, bytes) else body
    raw_event = RawConnectorEvent(**json.loads(raw))
    pipeline = ClassificationPipeline(repository=build_repository(), classifier=build_classifier())
    return pipeline.process(raw_event)
