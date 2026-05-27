from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from closedloop_os.models import CanonicalEvent, ClassificationResult, RawConnectorEvent


def _parse_datetime(value: str | None) -> datetime:
    if value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def map_zendesk_event(raw_event: RawConnectorEvent, classification: ClassificationResult) -> CanonicalEvent:
    payload = raw_event.payload
    ticket = payload.get("ticket", payload)
    requester = ticket.get("requester", {}) if isinstance(ticket.get("requester"), dict) else {}
    title = ticket.get("subject") or f"Zendesk {raw_event.event_name}"
    description = ticket.get("description") or ticket.get("comment", {}).get("body") or title
    importance_score = 0.95 if raw_event.event_name == "sla.breached" else classification.importance_score
    metadata = {
        "delivery_id": raw_event.delivery_id,
        "ticket_id": ticket.get("id"),
        "status": ticket.get("status"),
        "priority": ticket.get("priority"),
        "satisfaction_score": payload.get("satisfaction_rating", {}).get("score"),
        "classification": classification.model_dump(mode="json"),
    }
    return CanonicalEvent(
        source_tool="zendesk",
        event_type=f"zendesk.{raw_event.event_name}",
        title=title,
        description=description,
        actor=requester.get("name") or requester.get("email") or "zendesk",
        project=ticket.get("group_id") or "zendesk",
        importance_score=importance_score,
        timestamp=_parse_datetime(ticket.get("updated_at") or ticket.get("created_at")),
        raw_payload=payload,
        metadata=metadata,
    )
