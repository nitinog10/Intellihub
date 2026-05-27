from __future__ import annotations

import json
import re
from typing import Any

from openai import AzureOpenAI

from closedloop_os.config import get_settings
from closedloop_os.models import ClassificationResult, RawConnectorEvent


class EventClassifier:
    def classify(self, raw_event: RawConnectorEvent) -> ClassificationResult:
        raise NotImplementedError


class HeuristicEventClassifier(EventClassifier):
    decision_terms = ("decided", "decision", "approved", "blocked", "ship", "launch", "go/no-go")
    action_terms = ("action:", "todo", "follow up", "next step", "will own", "assign")

    def classify(self, raw_event: RawConnectorEvent) -> ClassificationResult:
        payload_text = json.dumps(raw_event.payload, ensure_ascii=False).lower()
        has_decision = any(term in payload_text for term in self.decision_terms)
        has_action = any(term in payload_text for term in self.action_terms)
        score = 0.55 if has_decision else 0.35
        if raw_event.source_tool == "slack" and not payload_text.strip("{}"):
            score = 0.0
        entities = sorted(set(re.findall(r"\b[A-Z]{2,}-\d+\b", json.dumps(raw_event.payload, ensure_ascii=False))))
        return ClassificationResult(
            importance_score=score,
            has_decision=has_decision,
            decisions=["Potential decision detected"] if has_decision else [],
            entities=entities,
            action_items=["Potential action item detected"] if has_action else [],
            relationships=[],
            rationale="Local heuristic fallback used because Azure OpenAI is not configured.",
        )


class AzureOpenAIEventClassifier(EventClassifier):
    def __init__(self) -> None:
        settings = get_settings()
        self._deployment = settings.azure_openai_deployment
        self._client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

    def classify(self, raw_event: RawConnectorEvent) -> ClassificationResult:
        response = self._client.chat.completions.create(
            model=self._deployment,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Classify knowledge-work events. Return JSON with keys: "
                        "importance_score float 0-1, has_decision boolean, "
                        "decisions array of strings, entities array of strings, "
                        "action_items array of strings, relationships array of objects, rationale string."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(raw_event.model_dump(mode="json"), ensure_ascii=False),
                },
            ],
            temperature=0.0,
        )
        content = response.choices[0].message.content or "{}"
        data: dict[str, Any] = json.loads(content)
        return ClassificationResult(**data)


def build_classifier() -> EventClassifier:
    settings = get_settings()
    if settings.azure_openai_endpoint and settings.azure_openai_api_key:
        return AzureOpenAIEventClassifier()
    return HeuristicEventClassifier()
