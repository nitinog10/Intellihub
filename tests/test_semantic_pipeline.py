from closedloop_os.classification import EventClassifier
from closedloop_os.models import ClassificationResult, RawConnectorEvent
from closedloop_os.persistence import InMemoryEventRepository
from closedloop_os.pipeline import ClassificationPipeline
from closedloop_os.search import DeterministicEmbeddingService, InMemoryKnowledgeStore


class StaticClassifier(EventClassifier):
    def __init__(self, result: ClassificationResult) -> None:
        self.result = result

    def classify(self, raw_event: RawConnectorEvent) -> ClassificationResult:
        return self.result


def test_jira_linear_overlap_sets_duplicate_metadata():
    repository = InMemoryEventRepository()
    knowledge_store = InMemoryKnowledgeStore(DeterministicEmbeddingService(64))
    classifier = StaticClassifier(
        ClassificationResult(
            importance_score=0.8,
            has_decision=False,
            decisions=[],
            entities=["ENG-101"],
        )
    )

    linear_raw = RawConnectorEvent(
        source_tool="linear",
        event_name="issue",
        delivery_id="linear-1",
        payload={
            "type": "Issue",
            "action": "create",
            "actor": {"name": "Ada"},
            "data": {
                "id": "LIN-1",
                "title": "Ship semantic search",
                "team": {"key": "ENG"},
                "createdAt": "2026-05-27T10:00:00Z",
            },
        },
    )
    jira_raw = RawConnectorEvent(
        source_tool="jira",
        event_name="issue_created",
        delivery_id="jira-1",
        payload={
            "issue": {
                "key": "ENG-101",
                "fields": {
                    "summary": "Ship semantic search",
                    "project": {"key": "ENG"},
                    "updated": "2026-05-27T10:00:00Z",
                },
            },
            "user": {"displayName": "Ada"},
        },
    )

    pipeline = ClassificationPipeline(repository=repository, classifier=classifier, knowledge_store=knowledge_store)
    pipeline.process(linear_raw)
    jira_event = pipeline.process(jira_raw)

    assert jira_event is not None
    assert jira_event.metadata["duplicate_candidate"]["source_tool"] == "linear"


def test_semantic_search_returns_ranked_results():
    knowledge_store = InMemoryKnowledgeStore(DeterministicEmbeddingService(64))
    repository = InMemoryEventRepository()
    classifier = StaticClassifier(ClassificationResult(importance_score=0.9, has_decision=True, decisions=["Use AI Search"]))
    pipeline = ClassificationPipeline(repository=repository, classifier=classifier, knowledge_store=knowledge_store)

    notion_raw = RawConnectorEvent(
        source_tool="notion",
        event_name="page_updated",
        delivery_id="notion-1",
        payload={
            "page": {
                "id": "page-1",
                "url": "https://notion.so/page-1",
                "last_edited_time": "2026-05-27T10:00:00Z",
                "parent": {"database_id": "db-1"},
                "properties": {
                    "Name": {
                        "type": "title",
                        "title": [{"plain_text": "Decision log: use Azure AI Search"}],
                    }
                },
            }
        },
    )
    pipeline.process(notion_raw)
    results = knowledge_store.semantic_search("Azure AI Search decision", limit=5)

    assert results
    assert results[0]["source_tool"] == "notion"
