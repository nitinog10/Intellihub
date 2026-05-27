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


class GraphRelationship(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    source_event_id: str
    source_node: str
    relationship_type: str
    target_node: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchDocument(BaseModel):
    id: str
    source_tool: str
    event_type: str
    title: str
    description: str
    actor: str
    importance_score: float
    timestamp: str
    content_vector: list[float]
    project: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class GitHubWebhookEnvelope(BaseModel):
    event_name: str
    delivery_id: str
    payload: dict[str, Any]


class RawConnectorEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    source_tool: str
    event_name: str
    delivery_id: str
    payload: dict[str, Any]
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClassificationResult(BaseModel):
    importance_score: float = 0.0
    has_decision: bool = False
    decisions: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    rationale: str = ""


class EventQuery(BaseModel):
    project: str | None = None
    actor: str | None = None
    event_type: str | None = None
    limit: int = 25


class Citation(BaseModel):
    id: str
    source_tool: str
    event_type: str
    title: str
    timestamp: str
    snippet: str


class IntelligenceResponse(BaseModel):
    answer: str
    confidence: str
    trust_score: float
    citations: list[Citation] = Field(default_factory=list)
    uncited_claims: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    processing_time_ms: int
