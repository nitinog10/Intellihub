from __future__ import annotations

import json

from closedloop_os.classification import EventClassifier, build_classifier
from closedloop_os.mappers.confluence import map_confluence_event
from closedloop_os.mappers.jira import map_jira_event
from closedloop_os.mappers.linear import map_linear_event
from closedloop_os.mappers.notion import map_notion_event
from closedloop_os.mappers.slack import map_slack_event
from closedloop_os.mappers.zendesk import map_zendesk_event
from closedloop_os.models import CanonicalEvent, RawConnectorEvent
from closedloop_os.persistence import EventRepository, build_repository
from closedloop_os.search import KnowledgeStore, build_knowledge_store
from closedloop_os.transcripts import TranscriptChunk, build_meeting_events, extract_relationships

MIN_IMPORTANCE_SCORE = 0.3


class ClassificationPipeline:
    def __init__(
        self,
        repository: EventRepository,
        classifier: EventClassifier,
        knowledge_store: KnowledgeStore | None = None,
    ) -> None:
        self.repository = repository
        self.classifier = classifier
        self.knowledge_store = knowledge_store or build_knowledge_store()

    def process(self, raw_event: RawConnectorEvent) -> CanonicalEvent | None:
        if raw_event.source_tool == "meeting":
            return self._process_meeting(raw_event)

        classification = self.classifier.classify(raw_event)
        event = self._map_event(raw_event, classification)
        if event.importance_score <= MIN_IMPORTANCE_SCORE:
            return None

        duplicate = self._find_duplicate(event)
        if duplicate:
            event.metadata["duplicate_candidate"] = {
                "id": duplicate.get("id"),
                "source_tool": duplicate.get("source_tool"),
                "similarity_score": duplicate.get("similarity_score"),
            }

        self.repository.upsert_event(event)
        self.repository.upsert_relationships(extract_relationships(event, classification))
        self.knowledge_store.upsert_event(event)
        return event

    def _process_meeting(self, raw_event: RawConnectorEvent) -> CanonicalEvent | None:
        grouped_chunks = [
            chunk if isinstance(chunk, TranscriptChunk) else TranscriptChunk(**chunk)
            for chunk in raw_event.payload.get("grouped_chunks", [])
        ]
        if not grouped_chunks:
            return None
        events, relationships = build_meeting_events(
            raw_event=raw_event,
            grouped_chunks=grouped_chunks,
            classification_factory=self.classifier.classify,
        )
        stored_events: list[CanonicalEvent] = []
        for event in events:
            if event.importance_score <= MIN_IMPORTANCE_SCORE:
                continue
            self.repository.upsert_event(event)
            self.knowledge_store.upsert_event(event)
            stored_events.append(event)
        if relationships:
            self.repository.upsert_relationships(relationships)
        return stored_events[0] if stored_events else None

    def _map_event(self, raw_event: RawConnectorEvent, classification) -> CanonicalEvent:
        if raw_event.source_tool == "slack":
            return map_slack_event(raw_event, classification)
        if raw_event.source_tool == "linear":
            return map_linear_event(raw_event, classification)
        if raw_event.source_tool == "jira":
            return map_jira_event(raw_event, classification)
        if raw_event.source_tool == "confluence":
            return map_confluence_event(raw_event, classification)
        if raw_event.source_tool == "notion":
            return map_notion_event(raw_event, classification)
        if raw_event.source_tool == "zendesk":
            return map_zendesk_event(raw_event, classification)
        raise ValueError(f"Unsupported pipeline source: {raw_event.source_tool}")

    def _find_duplicate(self, event: CanonicalEvent) -> dict | None:
        if event.source_tool == "jira":
            return self.knowledge_store.find_overlap(event, compare_source="linear", threshold=0.75)
        if event.source_tool == "linear":
            return self.knowledge_store.find_overlap(event, compare_source="jira", threshold=0.75)
        return None


def process_raw_event_message(body: str | bytes) -> CanonicalEvent | None:
    raw = body.decode("utf-8") if isinstance(body, bytes) else body
    raw_event = RawConnectorEvent(**json.loads(raw))
    pipeline = ClassificationPipeline(
        repository=build_repository(),
        classifier=build_classifier(),
        knowledge_store=build_knowledge_store(),
    )
    return pipeline.process(raw_event)
