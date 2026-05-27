from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class CanonicalEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    source_tool: str
    event_type: str
    title: str
    description: str
    actor: str
    project: str
    importance_score: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_payload: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)


class GitHubWebhookEnvelope(BaseModel):
    event_name: str
    delivery_id: str
    payload: dict[str, Any]


class EventQuery(BaseModel):
    project: str | None = None
    actor: str | None = None
    event_type: str | None = None
    limit: int = 25
