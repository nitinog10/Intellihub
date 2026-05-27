import hashlib
import hmac
import io
import json

from fastapi.testclient import TestClient

from closedloop_os.api import app, get_publisher
from closedloop_os.classification import EventClassifier
from closedloop_os.models import ClassificationResult, RawConnectorEvent
from closedloop_os.persistence import InMemoryEventRepository
from closedloop_os.pipeline import ClassificationPipeline
from closedloop_os.search import DeterministicEmbeddingService, InMemoryKnowledgeStore


class CapturePublisher:
    def __init__(self) -> None:
        self.events = []

    def publish_raw_event(self, event) -> None:
        self.events.append(event)


class StaticClassifier(EventClassifier):
    def __init__(self, result: ClassificationResult) -> None:
        self.result = result

    def classify(self, raw_event: RawConnectorEvent) -> ClassificationResult:
        return self.result


def _signature(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_zendesk_sla_breach_is_published(monkeypatch):
    publisher = CapturePublisher()
    app.dependency_overrides.clear()
    app.dependency_overrides[get_publisher] = lambda: publisher
    monkeypatch.setattr("closedloop_os.api.resolve_zendesk_webhook_secret", lambda: "zendesk-secret")

    body = json.dumps(
        {
            "type": "sla.breached",
            "ticket": {
                "id": 99,
                "subject": "Enterprise outage",
                "description": "SLA is breached",
                "updated_at": "2026-05-27T10:00:00Z",
            },
        }
    ).encode("utf-8")
    client = TestClient(app)
    response = client.post(
        "/api/connectors/zendesk",
        content=body,
        headers={"X-Zendesk-Webhook-Signature": _signature("zendesk-secret", body)},
    )

    assert response.status_code == 202
    assert publisher.events[0].source_tool == "zendesk"
    assert publisher.events[0].event_name == "sla.breached"


def test_meeting_upload_parses_and_publishes():
    publisher = CapturePublisher()
    app.dependency_overrides.clear()
    app.dependency_overrides[get_publisher] = lambda: publisher
    client = TestClient(app)
    response = client.post(
        "/api/connectors/meetings/upload",
        files={"file": ("standup.txt", io.BytesIO(b"Ada: We decided ENG-101 is blocked by API-2.\nBob: Action: Ada will follow up."), "text/plain")},
    )

    assert response.status_code == 202
    assert response.json()["chunk_count"] >= 1
    assert publisher.events[0].source_tool == "meeting"


def test_meeting_pipeline_stores_action_items_and_graph():
    repository = InMemoryEventRepository()
    knowledge_store = InMemoryKnowledgeStore(DeterministicEmbeddingService(64))
    classifier = StaticClassifier(
        ClassificationResult(
            importance_score=0.9,
            has_decision=True,
            decisions=["ENG-101 stays blocked"],
            entities=["ENG-101", "API-2"],
            action_items=["Ada will follow up"],
        )
    )
    raw_event = RawConnectorEvent(
        source_tool="meeting",
        event_name="transcript_upload",
        delivery_id="meeting-1",
        payload={
            "meeting_id": "mtg-1",
            "title": "Weekly standup",
            "grouped_chunks": [
                {"speaker": "Ada", "timestamp": "00:00:01", "text": "We decided ENG-101 is blocked by API-2. Action: Ada will follow up."}
            ],
        },
    )

    pipeline = ClassificationPipeline(repository=repository, classifier=classifier, knowledge_store=knowledge_store)
    stored = pipeline.process(raw_event)

    assert stored is not None
    action_items = repository.get_action_items(limit=10)
    graph = repository.get_entity_graph("ENG-101", limit=10)
    assert action_items
    assert any(edge["relationship_type"] == "BLOCKED_BY" for edge in graph)


def test_zendesk_mapping_forces_sla_importance():
    repository = InMemoryEventRepository()
    knowledge_store = InMemoryKnowledgeStore(DeterministicEmbeddingService(64))
    classifier = StaticClassifier(ClassificationResult(importance_score=0.2))
    raw_event = RawConnectorEvent(
        source_tool="zendesk",
        event_name="sla.breached",
        delivery_id="zd-1",
        payload={
            "ticket": {
                "id": 5,
                "subject": "Critical account escalation",
                "description": "SLA breached",
                "updated_at": "2026-05-27T10:00:00Z",
            }
        },
    )

    pipeline = ClassificationPipeline(repository=repository, classifier=classifier, knowledge_store=knowledge_store)
    event = pipeline.process(raw_event)

    assert event is not None
    assert event.importance_score == 0.95
