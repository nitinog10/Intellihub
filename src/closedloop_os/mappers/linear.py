from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from closedloop_os.models import CanonicalEvent, ClassificationResult, RawConnectorEvent


def _parse_datetime(value: str | None) -> datetime:
    if value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def _entity(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("data") or payload.get("issue") or payload.get("comment") or payload


def _actor(payload: dict[str, Any]) -> str:
    return (
        payload.get("actor", {}).get("name")
        or payload.get("actor", {}).get("email")
        or payload.get("organization", {}).get("name")
        or "linear"
    )


def map_linear_event(raw_event: RawConnectorEvent, classification: ClassificationResult) -> CanonicalEvent:
    payload = raw_event.payload
    data = _entity(payload)
    action = payload.get("action") or payload.get("type") or raw_event.event_name
    model = (payload.get("type") or data.get("__typename") or raw_event.event_name).lower()
    title_value = data.get("title") or data.get("name") or data.get("body") or model
    project = (
        data.get("project", {}).get("name")
        or data.get("team", {}).get("key")
        or payload.get("organization", {}).get("name")
        or "linear"
    )

    metadata = {
        "delivery_id": raw_event.delivery_id,
        "linear_id": data.get("id"),
        "url": data.get("url"),
        "cycle": data.get("cycle", {}).get("name") if isinstance(data.get("cycle"), dict) else data.get("cycle"),
        "state": data.get("state", {}).get("name") if isinstance(data.get("state"), dict) else data.get("state"),
        "classification": classification.model_dump(mode="json"),
    }

    return CanonicalEvent(
        source_tool="linear",
        event_type=f"linear.{model}.{action}".replace(" ", "_").lower(),
        title=f"Linear {model} {action}: {title_value}",
        description=data.get("description") or data.get("body") or title_value,
        actor=_actor(payload),
        project=project,
        importance_score=classification.importance_score,
        timestamp=_parse_datetime(data.get("updatedAt") or data.get("createdAt")),
        raw_payload=payload,
        metadata=metadata,
    )
