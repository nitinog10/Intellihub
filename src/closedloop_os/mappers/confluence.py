from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from closedloop_os.models import CanonicalEvent, ClassificationResult, RawConnectorEvent


def _parse_datetime(value: str | None) -> datetime:
    if value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def _is_decision_page(title: str, labels: list[str]) -> bool:
    upper = title.upper()
    return upper.startswith("ADR") or upper.startswith("RFC") or any(label.lower() in {"adr", "rfc", "decision"} for label in labels)


def map_confluence_event(raw_event: RawConnectorEvent, classification: ClassificationResult) -> CanonicalEvent:
    payload = raw_event.payload
    page = payload.get("page") or payload.get("content") or payload
    title = page.get("title") or "Untitled Confluence Page"
    labels = [label.get("name", "") if isinstance(label, dict) else str(label) for label in page.get("labels", [])]
    is_decision = _is_decision_page(title, labels)
    event_type = "confluence.decision_page" if is_decision else f"confluence.{raw_event.event_name}"
    description = (
        page.get("body", {}).get("storage", {}).get("value")
        if isinstance(page.get("body"), dict)
        else page.get("excerpt")
    ) or title
    actor = payload.get("user", {}).get("displayName") or payload.get("author", {}).get("displayName") or "confluence"
    classification_data = classification.model_copy(
        update={
            "has_decision": classification.has_decision or is_decision,
            "importance_score": max(classification.importance_score, 0.85 if is_decision else classification.importance_score),
            "decisions": classification.decisions or ([title] if is_decision else []),
        }
    )
    metadata = {
        "delivery_id": raw_event.delivery_id,
        "space": page.get("space", {}).get("key") if isinstance(page.get("space"), dict) else page.get("space"),
        "page_id": page.get("id"),
        "labels": labels,
        "classification": classification_data.model_dump(mode="json"),
    }

    return CanonicalEvent(
        source_tool="confluence",
        event_type=event_type,
        title=title,
        description=str(description),
        actor=actor,
        project=metadata["space"] or "confluence",
        importance_score=classification_data.importance_score,
        timestamp=_parse_datetime(page.get("version", {}).get("when") if isinstance(page.get("version"), dict) else None),
        raw_payload=payload,
        metadata=metadata,
    )
