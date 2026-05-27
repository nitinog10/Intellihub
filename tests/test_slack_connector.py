import hashlib
import hmac
import json
import time

from fastapi.testclient import TestClient

from closedloop_os.api import app, get_publisher


class CapturePublisher:
    def __init__(self) -> None:
        self.events = []

    def publish_raw_event(self, event) -> None:
        self.events.append(event)


def _signature(secret: str, body: bytes, timestamp: str) -> str:
    base = b"v0:" + timestamp.encode("utf-8") + b":" + body
    return "v0=" + hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()


def test_slack_url_verification(monkeypatch):
    publisher = CapturePublisher()
    app.dependency_overrides.clear()
    app.dependency_overrides[get_publisher] = lambda: publisher
    monkeypatch.setattr("closedloop_os.api.resolve_slack_signing_secret", lambda: "slack-secret")
    monkeypatch.setattr("closedloop_os.api.resolve_slack_bot_token", lambda: "xoxb-token")

    client = TestClient(app)
    body = json.dumps({"type": "url_verification", "challenge": "hello"}).encode("utf-8")
    timestamp = str(int(time.time()))

    response = client.post(
        "/api/connectors/slack",
        content=body,
        headers={
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": _signature("slack-secret", body, timestamp),
        },
    )

    assert response.status_code == 200
    assert response.json() == {"challenge": "hello"}
    assert publisher.events == []


def test_slack_message_event_is_published(monkeypatch):
    publisher = CapturePublisher()
    app.dependency_overrides.clear()
    app.dependency_overrides[get_publisher] = lambda: publisher
    monkeypatch.setattr("closedloop_os.api.resolve_slack_signing_secret", lambda: "slack-secret")
    monkeypatch.setattr("closedloop_os.api.resolve_slack_bot_token", lambda: "xoxb-token")

    client = TestClient(app)
    body = json.dumps(
        {
            "type": "event_callback",
            "event_id": "Ev123",
            "event": {
                "type": "message",
                "channel": "C123",
                "user": "U123",
                "text": "Decision: ship the first connector.",
                "ts": "1770000000.000100",
                "thread_ts": "1770000000.000100",
            },
        }
    ).encode("utf-8")
    timestamp = str(int(time.time()))

    response = client.post(
        "/api/connectors/slack",
        content=body,
        headers={
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": _signature("slack-secret", body, timestamp),
        },
    )

    assert response.status_code == 202
    assert len(publisher.events) == 1
    assert publisher.events[0].source_tool == "slack"
    assert publisher.events[0].event_name == "message"
