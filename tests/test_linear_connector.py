import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from closedloop_os.api import app, get_publisher


class CapturePublisher:
    def __init__(self) -> None:
        self.events = []

    def publish_raw_event(self, event) -> None:
        self.events.append(event)


def test_linear_issue_event_is_published(monkeypatch):
    publisher = CapturePublisher()
    app.dependency_overrides.clear()
    app.dependency_overrides[get_publisher] = lambda: publisher
    monkeypatch.setattr("closedloop_os.api.resolve_linear_secret", lambda: "linear-secret")

    client = TestClient(app)
    body = json.dumps(
        {
            "type": "Issue",
            "action": "create",
            "webhookId": "wh_123",
            "actor": {"name": "Ada"},
            "data": {
                "id": "LIN-1",
                "title": "Build classifier",
                "team": {"key": "ENG"},
                "createdAt": "2026-05-27T10:00:00Z",
            },
        }
    ).encode("utf-8")
    signature = hmac.new("linear-secret".encode("utf-8"), body, hashlib.sha256).hexdigest()

    response = client.post(
        "/api/connectors/linear",
        content=body,
        headers={"Linear-Signature": signature},
    )

    assert response.status_code == 202
    assert len(publisher.events) == 1
    assert publisher.events[0].source_tool == "linear"
    assert publisher.events[0].event_name == "issue"
