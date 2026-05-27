from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from closedloop_os.models import CanonicalEvent, ClassificationResult, RawConnectorEvent


def _parse_datetime(value: str | None) -> datetime:
    if value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def _extract_title(page: dict[str, Any]) -> str:
    props = page.get("properties", {})
    for prop in props.values():
        if isinstance(prop, dict) and prop.get("type") == "title":
            parts = prop.get("title", [])
            return "".join(part.get("plain_text", "") for part in parts) or "Untitled Notion Page"
    return page.get("title") or "Untitled Notion Page"


def map_notion_event(raw_event: RawConnectorEvent, classification: ClassificationResult) -> CanonicalEvent:
    page = raw_event.payload.get("page", raw_event.payload)
    title = _extract_title(page)
    actor = page.get("last_edited_by", {}).get("name") or page.get("created_by", {}).get("name") or "notion"
    metadata = {
        "delivery_id": raw_event.delivery_id,
        "page_id": page.get("id"),
        "url": page.get("url"),
        "classification": classification.model_dump(mode="json"),
    }
    return CanonicalEvent(
        source_tool="notion",
        event_type=f"notion.{raw_event.event_name}",
        title=title,
        description=page.get("url") or title,
        actor=actor,
        project=page.get("parent", {}).get("database_id") or "notion",
        importance_score=classification.importance_score,
        timestamp=_parse_datetime(page.get("last_edited_time") or page.get("created_time")),
        raw_payload=raw_event.payload,
        metadata=metadata,
    )
