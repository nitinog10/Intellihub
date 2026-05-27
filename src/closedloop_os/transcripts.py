from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from closedloop_os.models import CanonicalEvent, ClassificationResult, GraphRelationship, RawConnectorEvent

FILLER_TERMS = {"um", "uh", "like", "you know", "sort of", "kind of", "actually"}
RELATIONSHIP_TYPES = {
    "implements": "IMPLEMENTS",
    "blocked by": "BLOCKED_BY",
    "assigned to": "ASSIGNED_TO",
    "mentioned in": "MENTIONED_IN",
    "caused by": "CAUSED_BY",
    "resolved by": "RESOLVED_BY",
    "discussed in": "DISCUSSED_IN",
}


@dataclass
class TranscriptChunk:
    speaker: str
    timestamp: str | None
    text: str


def parse_transcript(filename: str, content: bytes) -> list[TranscriptChunk]:
    suffix = Path(filename).suffix.lower()
    text = content.decode("utf-8")
    if suffix == ".txt":
        return [TranscriptChunk(speaker="unknown", timestamp=None, text=line.strip()) for line in text.splitlines() if line.strip()]
    if suffix == ".json":
        payload = json.loads(text)
        if isinstance(payload, list):
            return [
                TranscriptChunk(
                    speaker=item.get("speaker", "unknown"),
                    timestamp=item.get("timestamp"),
                    text=item.get("text", "").strip(),
                )
                for item in payload
                if item.get("text")
            ]
        return [
            TranscriptChunk(
                speaker=item.get("speaker", "unknown"),
                timestamp=item.get("timestamp"),
                text=item.get("text", "").strip(),
            )
            for item in payload.get("segments", [])
            if item.get("text")
        ]
    if suffix in {".vtt", ".srt"}:
        return _parse_caption_text(text)
    raise ValueError(f"Unsupported transcript file type: {suffix}")


def _parse_caption_text(text: str) -> list[TranscriptChunk]:
    chunks: list[TranscriptChunk] = []
    blocks = re.split(r"\n\s*\n", text.strip())
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if lines[0].isdigit():
            lines = lines[1:]
        timestamp = lines[0] if "-->" in lines[0] else None
        content_lines = lines[1:] if timestamp else lines
        merged = " ".join(content_lines).strip()
        if merged:
            speaker, body = _extract_speaker(merged)
            chunks.append(TranscriptChunk(speaker=speaker, timestamp=timestamp, text=body))
    return chunks


def _extract_speaker(text: str) -> tuple[str, str]:
    if ":" in text:
        speaker, body = text.split(":", 1)
        if len(speaker.split()) <= 4:
            return speaker.strip(), body.strip()
    return "unknown", text.strip()


def remove_filler(text: str) -> str:
    cleaned = text
    for term in sorted(FILLER_TERMS, key=len, reverse=True):
        cleaned = re.sub(rf"\b{re.escape(term)}\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" ,.")


def chunk_transcript(chunks: list[TranscriptChunk], chunk_size: int = 3) -> list[TranscriptChunk]:
    grouped: list[TranscriptChunk] = []
    for start in range(0, len(chunks), chunk_size):
        batch = chunks[start : start + chunk_size]
        grouped.append(
            TranscriptChunk(
                speaker=batch[0].speaker if batch else "unknown",
                timestamp=batch[0].timestamp if batch else None,
                text=" ".join(chunk.text for chunk in batch),
            )
        )
    return grouped


def build_meeting_events(
    raw_event: RawConnectorEvent,
    grouped_chunks: list[TranscriptChunk],
    classification_factory,
) -> tuple[list[CanonicalEvent], list[GraphRelationship]]:
    payload = raw_event.payload
    meeting_id = payload.get("meeting_id", raw_event.id)
    title = payload.get("title", "Meeting Transcript")
    base_timestamp = datetime.now(timezone.utc)
    events: list[CanonicalEvent] = []
    relationships: list[GraphRelationship] = []

    for index, chunk in enumerate(grouped_chunks):
        cleaned_text = remove_filler(chunk.text)
        if not cleaned_text:
            continue
        segment_payload = {
            "meeting_id": meeting_id,
            "title": title,
            "speaker": chunk.speaker,
            "timestamp": chunk.timestamp,
            "text": cleaned_text,
        }
        classification = classification_factory(
            RawConnectorEvent(
                source_tool="meeting",
                event_name="transcript_chunk",
                delivery_id=f"{raw_event.delivery_id}-{index}",
                payload=segment_payload,
            )
        )
        event = CanonicalEvent(
            source_tool="meeting",
            event_type="meeting.transcript_chunk",
            title=f"{title} - segment {index + 1}",
            description=cleaned_text,
            actor=chunk.speaker,
            project=meeting_id,
            importance_score=classification.importance_score,
            timestamp=base_timestamp,
            raw_payload=segment_payload,
            metadata={
                "meeting_id": meeting_id,
                "classification": classification.model_dump(mode="json"),
                "speaker": chunk.speaker,
                "segment_index": index,
            },
        )
        events.append(event)
        relationships.extend(extract_relationships(event, classification))
    return events, relationships


def extract_relationships(event: CanonicalEvent, classification: ClassificationResult) -> list[GraphRelationship]:
    relationships: list[GraphRelationship] = []
    entities = classification.entities or []
    for entity in entities:
        relationships.append(
            GraphRelationship(
                source_event_id=event.id,
                source_node=entity,
                relationship_type="MENTIONED_IN",
                target_node=event.id,
                metadata={"event_type": event.event_type},
            )
        )

    text = event.description.lower()
    for phrase, relationship_type in RELATIONSHIP_TYPES.items():
        if phrase in text and len(entities) >= 2:
            relationships.append(
                GraphRelationship(
                    source_event_id=event.id,
                    source_node=entities[0],
                    relationship_type=relationship_type,
                    target_node=entities[1],
                    metadata={"event_type": event.event_type},
                )
            )
    if event.source_tool == "meeting":
        relationships.append(
            GraphRelationship(
                source_event_id=event.id,
                source_node=event.project,
                relationship_type="DISCUSSED_IN",
                target_node=event.id,
                metadata={"speaker": event.actor},
            )
        )
    return relationships
