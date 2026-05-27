from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from closedloop_os.models import CanonicalEvent, ClassificationResult, RawConnectorEvent


def _slack_ts_to_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromtimestamp(float(value), tz=timezone.utc)


def extract_slack_event(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("event", payload)


def map_slack_event(raw_event: RawConnectorEvent, classification: ClassificationResult) -> CanonicalEvent:
    event = extract_slack_event(raw_event.payload)
    channel = event.get("channel") or event.get("channel_id") or "unknown"
    user = event.get("user") or event.get("user_id") or event.get("bot_id") or "unknown"
    text = event.get("text") or event.get("title") or ""
    event_ts = event.get("event_ts") or event.get("ts")

    if raw_event.event_name == "file_shared" or event.get("type") == "file_shared":
        event_type = "slack.file_shared"
        title = f"File shared in {channel}"
        description = text or f"{user} shared a file in Slack channel {channel}."
    else:
        event_type = "slack.message"
        title = f"Slack message in {channel}"
        description = text

    metadata = {
        "delivery_id": raw_event.delivery_id,
        "channel": channel,
        "user": user,
        "timestamp": event_ts,
        "thread_ts": event.get("thread_ts"),
        "classification": classification.model_dump(mode="json"),
    }

    return CanonicalEvent(
        source_tool="slack",
        event_type=event_type,
        title=title,
        description=description,
        actor=user,
        project=channel,
        importance_score=classification.importance_score,
        timestamp=_slack_ts_to_datetime(event_ts),
        raw_payload=raw_event.payload,
        metadata=metadata,
    )
