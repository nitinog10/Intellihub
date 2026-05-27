from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

from closedloop_os.models import Citation, IntelligenceResponse
from closedloop_os.persistence import EventRepository, build_repository
from closedloop_os.search import KnowledgeStore, build_knowledge_store


@dataclass
class EvidenceItem:
    id: str
    source_tool: str
    event_type: str
    title: str
    description: str
    actor: str
    project: str
    timestamp: str
    importance_score: float

    @property
    def snippet(self) -> str:
        return self.description[:280]


class IntelligenceService:
    def __init__(self, repository: EventRepository | None = None, knowledge_store: KnowledgeStore | None = None) -> None:
        self.repository = repository or build_repository()
        self.knowledge_store = knowledge_store or build_knowledge_store()

    def ask_intelligence(self, question: str) -> IntelligenceResponse:
        started = time.perf_counter()
        parts = self._decompose(question)
        evidence = self._retrieve(parts)
        citations = [self._to_citation(item) for item in evidence]
        answer, uncited_claims = self._build_answer(question, evidence)
        confidence, trust_score = self._score_confidence(evidence, uncited_claims)
        suggested_actions = self._suggest_actions(evidence)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return IntelligenceResponse(
            answer=answer,
            confidence=confidence,
            trust_score=trust_score,
            citations=citations,
            uncited_claims=uncited_claims,
            suggested_actions=suggested_actions,
            processing_time_ms=elapsed_ms,
        )

    def get_timeline(self, entity: str, limit: int = 50) -> list[dict[str, Any]]:
        return self.repository.get_timeline(entity=entity, limit=limit)

    def _decompose(self, question: str) -> list[str]:
        normalized = question.strip()
        clauses = [part.strip() for part in re.split(r"[?.]| and | then | also ", normalized, flags=re.IGNORECASE) if part.strip()]
        if not clauses:
            return [normalized]
        return clauses[:4]

    def _retrieve(self, parts: list[str]) -> list[EvidenceItem]:
        merged: dict[str, EvidenceItem] = {}
        for part in parts:
            semantic_hits = self.knowledge_store.semantic_search(part, limit=6)
            text_hits = self.repository.search_text(part, limit=6)
            decision_hits = self.repository.search_decisions(part, limit=4)
            action_hits = self.repository.get_action_items(part, limit=4)
            for raw in [*semantic_hits, *text_hits, *decision_hits, *action_hits]:
                if "id" not in raw:
                    continue
                item = self._to_evidence(raw)
                if item.id not in merged:
                    merged[item.id] = item
        ranked = sorted(
            merged.values(),
            key=lambda item: (item.importance_score, item.timestamp),
            reverse=True,
        )
        return ranked[:8]

    def _to_evidence(self, raw: dict[str, Any]) -> EvidenceItem:
        return EvidenceItem(
            id=str(raw.get("id")),
            source_tool=str(raw.get("source_tool", "")),
            event_type=str(raw.get("event_type", "")),
            title=str(raw.get("title", "")),
            description=str(raw.get("description", "")),
            actor=str(raw.get("actor", "")),
            project=str(raw.get("project", "")),
            timestamp=str(raw.get("timestamp", "")),
            importance_score=float(raw.get("importance_score", 0.0)),
        )

    def _to_citation(self, item: EvidenceItem) -> Citation:
        return Citation(
            id=item.id,
            source_tool=item.source_tool,
            event_type=item.event_type,
            title=item.title,
            timestamp=item.timestamp,
            snippet=item.snippet,
        )

    def _build_answer(self, question: str, evidence: list[EvidenceItem]) -> tuple[str, list[str]]:
        if not evidence:
            return "I could not find supporting evidence for that question.", []

        sentences: list[str] = []
        for index, item in enumerate(evidence, start=1):
            factual = self._fact_sentence(item)
            sentences.append(f"{factual[:-1]} [{index}].")

        summary = " ".join(sentences)
        uncited = self._verify_citations(summary, len(evidence))
        return summary, uncited

    def _fact_sentence(self, item: EvidenceItem) -> str:
        bits = [item.title]
        if item.description and item.description != item.title:
            bits.append(item.description)
        bits.append(f"Source {item.source_tool}")
        if item.timestamp:
            bits.append(f"Timestamp {item.timestamp}")
        return "; ".join(bit.strip().rstrip(".") for bit in bits if bit).strip() + "."

    def _verify_citations(self, answer: str, citation_count: int) -> list[str]:
        uncited: list[str] = []
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", answer) if part.strip()]
        for sentence in sentences:
            if not re.search(r"\[\d+\]", sentence):
                uncited.append(sentence)
        cited_numbers = {int(match) for match in re.findall(r"\[(\d+)\]", answer)}
        if any(number < 1 or number > citation_count for number in cited_numbers):
            uncited.append("Answer contains invalid citation references.")
        return uncited

    def _score_confidence(self, evidence: list[EvidenceItem], uncited_claims: list[str]) -> tuple[str, float]:
        if not evidence:
            return "LOW", 0.15
        base = min(1.0, 0.2 + 0.1 * len(evidence) + 0.4 * max(item.importance_score for item in evidence))
        penalty = 0.25 * len(uncited_claims)
        trust_score = max(0.0, round(base - penalty, 2))
        if trust_score >= 0.8:
            return "HIGH", trust_score
        if trust_score >= 0.5:
            return "MEDIUM", trust_score
        return "LOW", trust_score

    def _suggest_actions(self, evidence: list[EvidenceItem]) -> list[str]:
        actions: list[str] = []
        for item in evidence:
            if item.source_tool == "zendesk":
                actions.append(f"Review customer issue: {item.title}")
            if item.event_type.endswith("decision_page") or "decision" in item.title.lower():
                actions.append(f"Validate the recorded decision in {item.source_tool}: {item.title}")
            if item.source_tool == "meeting":
                actions.append(f"Inspect meeting follow-ups for {item.project}")
        deduped: list[str] = []
        for action in actions:
            if action not in deduped:
                deduped.append(action)
        return deduped[:5]
