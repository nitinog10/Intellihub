from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from closedloop_os.models import CanonicalEvent, ClassificationResult, RawConnectorEvent


def _parse_datetime(value: str | None) -> datetime:
    if value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def map_jira_event(raw_event: RawConnectorEvent, classification: ClassificationResult) -> CanonicalEvent:
    payload = raw_event.payload
    issue = payload.get("issue", {})
    comment = payload.get("comment", {})
    sprint = payload.get("sprint", {})
    actor = (
        payload.get("user", {}).get("displayName")
        or payload.get("actor", {}).get("displayName")
        or payload.get("user", {}).get("name")
        or "jira"
    )
    project = issue.get("fields", {}).get("project", {}).get("key") or sprint.get("originBoardName") or "jira"
    title_source = issue.get("fields", {}).get("summary") or comment.get("body") or sprint.get("name") or raw_event.event_name
    description = issue.get("fields", {}).get("description")
    if isinstance(description, dict):
        description = str(description)
    description = description or comment.get("body") or title_source
    fields = issue.get("fields", {})
    metadata = {
        "delivery_id": raw_event.delivery_id,
        "issue_key": issue.get("key"),
        "epic_key": fields.get("parent", {}).get("key") or fields.get("customfield_10014"),
        "status": fields.get("status", {}).get("name"),
        "sprint": sprint.get("name") or fields.get("customfield_10020"),
        "comment_id": comment.get("id"),
        "classification": classification.model_dump(mode="json"),
    }

    event_type = f"jira.{raw_event.event_name}"
    return CanonicalEvent(
        source_tool="jira",
        event_type=event_type,
        title=f"Jira {raw_event.event_name}: {title_source}",
        description=description,
        actor=actor,
        project=project,
        importance_score=classification.importance_score,
        timestamp=_parse_datetime(
            issue.get("fields", {}).get("updated")
            or comment.get("updated")
            or sprint.get("completeDate")
            or sprint.get("startDate")
        ),
        raw_payload=payload,
        metadata=metadata,
    )
