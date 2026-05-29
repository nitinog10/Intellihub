from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from functools import lru_cache
from hashlib import sha256
from typing import Any

from azure.cosmos import CosmosClient
from openai import AzureOpenAI

from closedloop_os.config import get_settings
from closedloop_os.models import CanonicalEvent, SearchDocument


def _event_text(event: CanonicalEvent) -> str:
    return f"{event.title}\n{event.description}\n{event.actor}\n{event.project}"


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


class EmbeddingService(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class DeterministicEmbeddingService(EmbeddingService):
    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        if not tokens:
            return vector
        for token in tokens:
            digest = sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]


class AzureOpenAIEmbeddingService(EmbeddingService):
    def __init__(self) -> None:
        settings = get_settings()
        self._deployment = settings.azure_openai_embedding_deployment
        self._client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

    def embed(self, text: str) -> list[float]:
        result = self._client.embeddings.create(model=self._deployment, input=text)
        return list(result.data[0].embedding)


class KnowledgeStore(ABC):
    @abstractmethod
    def ensure_index(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def upsert_event(self, event: CanonicalEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    def semantic_search(self, query_text: str, limit: int = 10, source_tool: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def find_overlap(self, event: CanonicalEvent, compare_source: str, threshold: float = 0.92) -> dict[str, Any] | None:
        raise NotImplementedError


class InMemoryKnowledgeStore(KnowledgeStore):
    def __init__(self, embedding_service: EmbeddingService) -> None:
        self.embedding_service = embedding_service
        self._documents: dict[str, SearchDocument] = {}

    def ensure_index(self) -> None:
        return None

    def _build_document(self, event: CanonicalEvent) -> SearchDocument:
        return SearchDocument(
            id=event.id,
            source_tool=event.source_tool,
            event_type=event.event_type,
            title=event.title,
            description=event.description,
            actor=event.actor,
            importance_score=event.importance_score,
            timestamp=event.timestamp.isoformat(),
            content_vector=self.embedding_service.embed(_event_text(event)),
            project=event.project,
            metadata=event.metadata,
        )

    def upsert_event(self, event: CanonicalEvent) -> None:
        self._documents[event.id] = self._build_document(event)

    def semantic_search(self, query_text: str, limit: int = 10, source_tool: str | None = None) -> list[dict[str, Any]]:
        query_vector = self.embedding_service.embed(query_text)
        docs = list(self._documents.values())
        if source_tool:
            docs = [doc for doc in docs if doc.source_tool == source_tool]
        ranked = sorted(
            docs,
            key=lambda doc: _cosine_similarity(query_vector, doc.content_vector),
            reverse=True,
        )
        return [doc.model_dump(mode="json") for doc in ranked[:limit]]

    def find_overlap(self, event: CanonicalEvent, compare_source: str, threshold: float = 0.92) -> dict[str, Any] | None:
        if not self._documents:
            return None
        probe = self._build_document(event)
        candidates = [doc for doc in self._documents.values() if doc.source_tool == compare_source]
        ranked = sorted(
            candidates,
            key=lambda doc: _cosine_similarity(probe.content_vector, doc.content_vector),
            reverse=True,
        )
        if not ranked:
            return None
        score = _cosine_similarity(probe.content_vector, ranked[0].content_vector)
        if score < threshold:
            return None
        result = ranked[0].model_dump(mode="json")
        result["similarity_score"] = score
        return result


class CosmosAwareKnowledgeStore(KnowledgeStore):
    """Stores search documents (including vectors) in Cosmos DB and loads them
    into memory for fast cosine-similarity search.

    This replaces Azure AI Search with a simpler approach:
    - Vectors are persisted in a Cosmos DB ``knowledge`` container
    - On ``ensure_index()`` all existing documents are loaded into memory
    - Search is performed in-memory (no network latency)
    """

    def __init__(self, embedding_service: EmbeddingService) -> None:
        settings = get_settings()
        self.embedding_service = embedding_service
        client = CosmosClient(url=settings.cosmos_endpoint, credential=settings.cosmos_key)
        database = client.get_database_client(settings.cosmos_database_name)
        self._container = database.get_container_client("knowledge")
        self._documents: dict[str, SearchDocument] = {}
        self._loaded = False

    def ensure_index(self) -> None:
        if self._loaded:
            return
        self._load_from_cosmos()
        self._loaded = True

    def _load_from_cosmos(self) -> None:
        """Load all existing knowledge documents from Cosmos DB into memory."""
        items = list(
            self._container.query_items(
                query="SELECT * FROM c",
                enable_cross_partition_query=True,
            )
        )
        for item in items:
            try:
                doc = SearchDocument(**item)
                self._documents[doc.id] = doc
            except Exception:
                continue

    def _build_document(self, event: CanonicalEvent) -> SearchDocument:
        return SearchDocument(
            id=event.id,
            source_tool=event.source_tool,
            event_type=event.event_type,
            title=event.title,
            description=event.description,
            actor=event.actor,
            importance_score=event.importance_score,
            timestamp=event.timestamp.isoformat(),
            content_vector=self.embedding_service.embed(_event_text(event)),
            project=event.project,
            metadata=event.metadata,
        )

    def upsert_event(self, event: CanonicalEvent) -> None:
        self.ensure_index()
        doc = self._build_document(event)
        self._documents[event.id] = doc
        self._container.upsert_item(doc.model_dump(mode="json"))

    def semantic_search(self, query_text: str, limit: int = 10, source_tool: str | None = None) -> list[dict[str, Any]]:
        self.ensure_index()
        query_vector = self.embedding_service.embed(query_text)
        docs = list(self._documents.values())
        if source_tool:
            docs = [doc for doc in docs if doc.source_tool == source_tool]
        ranked = sorted(
            docs,
            key=lambda doc: _cosine_similarity(query_vector, doc.content_vector),
            reverse=True,
        )
        return [doc.model_dump(mode="json") for doc in ranked[:limit]]

    def find_overlap(self, event: CanonicalEvent, compare_source: str, threshold: float = 0.92) -> dict[str, Any] | None:
        self.ensure_index()
        if not self._documents:
            return None
        probe = self._build_document(event)
        candidates = [doc for doc in self._documents.values() if doc.source_tool == compare_source]
        ranked = sorted(
            candidates,
            key=lambda doc: _cosine_similarity(probe.content_vector, doc.content_vector),
            reverse=True,
        )
        if not ranked:
            return None
        score = _cosine_similarity(probe.content_vector, ranked[0].content_vector)
        if score < threshold:
            return None
        result = ranked[0].model_dump(mode="json")
        result["similarity_score"] = score
        return result


def build_embedding_service() -> EmbeddingService:
    settings = get_settings()
    if settings.has_openai:
        return AzureOpenAIEmbeddingService()
    return DeterministicEmbeddingService(settings.azure_openai_embedding_dimensions)


@lru_cache(maxsize=1)
def get_local_knowledge_store() -> InMemoryKnowledgeStore:
    settings = get_settings()
    return InMemoryKnowledgeStore(DeterministicEmbeddingService(settings.azure_openai_embedding_dimensions))


def build_knowledge_store() -> KnowledgeStore:
    settings = get_settings()
    embedding_service = build_embedding_service()
    if settings.has_cosmos:
        return CosmosAwareKnowledgeStore(embedding_service)
    return InMemoryKnowledgeStore(embedding_service)
