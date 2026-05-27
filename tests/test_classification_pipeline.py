from closedloop_os.classification import EventClassifier
from closedloop_os.models import ClassificationResult, RawConnectorEvent
from closedloop_os.persistence import InMemoryEventRepository
from closedloop_os.pipeline import ClassificationPipeline


class StaticClassifier(EventClassifier):
    def __init__(self, result: ClassificationResult) -> None:
        self.result = result

    def classify(self, raw_event: RawConnectorEvent) -> ClassificationResult:
        return self.result


def test_pipeline_stores_only_events_above_threshold():
    repository = InMemoryEventRepository()
    raw_event = RawConnectorEvent(
        source_tool="slack",
        event_name="message",
        delivery_id="Ev123",
        payload={
            "event": {
                "type": "message",
                "channel": "C123",
                "user": "U123",
                "text": "Decision: ship Phase 2.",
                "ts": "1770000000.000100",
            }
        },
    )

    low = ClassificationPipeline(
        repository=repository,
        classifier=StaticClassifier(ClassificationResult(importance_score=0.3)),
    ).process(raw_event)

    high = ClassificationPipeline(
        repository=repository,
        classifier=StaticClassifier(
            ClassificationResult(
                importance_score=0.8,
                has_decision=True,
                decisions=["Ship Phase 2"],
                entities=["Phase 2"],
            )
        ),
    ).process(raw_event)

    assert low is None
    assert high is not None
    assert repository.search_decisions("ship", limit=10)[0]["id"] == high.id
