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


def _signature(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_jira_issue_event_is_published(monkeypatch):
    publisher = CapturePublisher()
    app.dependency_overrides.clear()
    app.dependency_overrides[get_publisher] = lambda: publisher
    monkeypatch.setattr("closedloop_os.api.resolve_jira_webhook_secret", lambda: "jira-secret")
    monkeypatch.setattr("closedloop_os.api.resolve_jira_access_token", lambda: "jira-token")

    body = json.dumps(
        {
            "webhookEvent": "jira:issue_created",
            "timestamp": 1770000000,
            "issue": {
                "key": "ENG-101",
                "fields": {
                    "summary": "Ship semantic search",
                    "project": {"key": "ENG"},
                    "updated": "2026-05-27T10:00:00Z",
                },
            },
            "user": {"displayName": "Ada"},
        }
    ).encode("utf-8")
    client = TestClient(app)
    response = client.post(
        "/api/connectors/jira",
        content=body,
        headers={
            "X-Atlassian-Webhook-Event": "issue_created",
            "X-ClosedLoop-Signature": _signature("jira-secret", body),
        },
    )

    assert response.status_code == 202
    assert publisher.events[0].source_tool == "jira"
    assert publisher.events[0].event_name == "issue_created"


def test_confluence_event_is_published(monkeypatch):
    publisher = CapturePublisher()
    app.dependency_overrides.clear()
    app.dependency_overrides[get_publisher] = lambda: publisher
    monkeypatch.setattr("closedloop_os.api.resolve_confluence_webhook_secret", lambda: "confluence-secret")
    monkeypatch.setattr("closedloop_os.api.resolve_confluence_access_token", lambda: "confluence-token")

    body = json.dumps(
        {
            "eventType": "page_updated",
            "page": {
                "id": "123",
                "title": "ADR-42 Search Index Direction",
                "space": {"key": "ARCH"},
                "version": {"when": "2026-05-27T10:00:00Z"},
                "labels": [{"name": "adr"}],
            },
        }
    ).encode("utf-8")
    client = TestClient(app)
    response = client.post(
        "/api/connectors/confluence",
        content=body,
        headers={"X-ClosedLoop-Signature": _signature("confluence-secret", body)},
    )

    assert response.status_code == 202
    assert publisher.events[0].source_tool == "confluence"
