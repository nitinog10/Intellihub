import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from closedloop_os.api import app
from closedloop_os.messaging import NullPublisher
from closedloop_os.persistence import InMemoryEventRepository


def _signature(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_github_webhook_accepts_supported_event(monkeypatch):
    repository = InMemoryEventRepository()

    app.dependency_overrides.clear()
    app.dependency_overrides[__import__("closedloop_os.api", fromlist=["get_repository"]).get_repository] = lambda: repository
    app.dependency_overrides[__import__("closedloop_os.api", fromlist=["get_publisher"]).get_publisher] = lambda: NullPublisher()
    monkeypatch.setattr("closedloop_os.api.resolve_github_secret", lambda: "super-secret")

    client = TestClient(app)
    payload = {
        "repository": {"full_name": "closedloop/example"},
        "sender": {"login": "octocat"},
        "ref": "refs/heads/main",
        "commits": [{"id": "abc"}],
        "head_commit": {"timestamp": "2026-05-27T08:00:00Z"},
    }
    body = json.dumps(payload).encode("utf-8")

    response = client.post(
        "/api/connectors/github",
        content=body,
        headers={
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": "delivery-1",
            "X-Hub-Signature-256": _signature("super-secret", body),
        },
    )

    assert response.status_code == 202
    data = response.json()
    assert data["event_type"] == "github.push"
    assert repository.get_event_by_id(data["event_id"]) is not None


def test_github_webhook_rejects_invalid_signature(monkeypatch):
    app.dependency_overrides.clear()
    monkeypatch.setattr("closedloop_os.api.resolve_github_secret", lambda: "super-secret")
    client = TestClient(app)
    body = json.dumps({"repository": {"full_name": "closedloop/example"}}).encode("utf-8")

    response = client.post(
        "/api/connectors/github",
        content=body,
        headers={
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": "delivery-1",
            "X-Hub-Signature-256": "sha256=bad",
        },
    )

    assert response.status_code == 401
