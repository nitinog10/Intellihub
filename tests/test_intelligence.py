from datetime import datetime, timezone

from closedloop_os.intelligence import IntelligenceService
from closedloop_os.models import CanonicalEvent
from closedloop_os.persistence import InMemoryEventRepository
from closedloop_os.search import DeterministicEmbeddingService, InMemoryKnowledgeStore


def _event(
    event_id: str,
    source_tool: str,
    title: str,
    description: str,
    timestamp: str,
    importance_score: float = 0.8,
    actor: str = "Ada",
    project: str = "ENG",
    metadata: dict | None = None,
) -> CanonicalEvent:
    return CanonicalEvent(
        id=event_id,
        source_tool=source_tool,
        event_type=f"{source_tool}.event",
        title=title,
        description=description,
        actor=actor,
        project=project,
        importance_score=importance_score,
        timestamp=datetime.fromisoformat(timestamp.replace("Z", "+00:00")),
        raw_payload={},
        metadata=metadata or {},
    )


def test_ask_intelligence_returns_cited_answer():
    repository = InMemoryEventRepository()
    knowledge_store = InMemoryKnowledgeStore(DeterministicEmbeddingService(64))
    event = _event(
        "evt-1",
        "zendesk",
        "Enterprise outage ticket",
        "SLA breached for customer ACME on ENG-101.",
        "2026-05-27T10:00:00Z",
        importance_score=0.95,
    )
    repository.upsert_event(event)
    knowledge_store.upsert_event(event)

    service = IntelligenceService(repository=repository, knowledge_store=knowledge_store)
    response = service.ask_intelligence("What customer signals mention ENG-101?")

    assert response.citations
    assert response.answer
    assert "[" in response.answer and "]" in response.answer
    assert response.uncited_claims == []
    assert response.confidence in {"HIGH", "MEDIUM", "LOW"}
    assert response.trust_score > 0


def test_get_timeline_returns_chronological_events():
    repository = InMemoryEventRepository()
    knowledge_store = InMemoryKnowledgeStore(DeterministicEmbeddingService(64))
    first = _event("evt-1", "jira", "ENG-101 opened", "Initial issue created", "2026-05-27T09:00:00Z")
    second = _event("evt-2", "meeting", "Standup", "Discussed ENG-101 blockers", "2026-05-27T10:00:00Z")
    repository.upsert_event(second)
    repository.upsert_event(first)
    knowledge_store.upsert_event(first)
    knowledge_store.upsert_event(second)

    service = IntelligenceService(repository=repository, knowledge_store=knowledge_store)
    timeline = service.get_timeline("ENG-101", limit=10)

    assert [item["id"] for item in timeline] == ["evt-1", "evt-2"]
