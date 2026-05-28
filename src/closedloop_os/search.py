from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from functools import lru_cache
from hashlib import sha256
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchableField,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery
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


class AzureAISearchKnowledgeStore(KnowledgeStore):
    def __init__(self, embedding_service: EmbeddingService) -> None:
        settings = get_settings()
        credential = AzureKeyCredential(settings.azure_search_api_key)
        self.index_name = settings.azure_search_index_name
        self.embedding_service = embedding_service
        self.index_client = SearchIndexClient(endpoint=settings.azure_search_endpoint, credential=credential)
        self.search_client = SearchClient(endpoint=settings.azure_search_endpoint, index_name=self.index_name, credential=credential)
        self.dimensions = settings.azure_openai_embedding_dimensions

    def ensure_index(self) -> None:
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(name="source_tool", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="event_type", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SearchableField(name="description", type=SearchFieldDataType.String),
            SearchableField(name="actor", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="importance_score", type=SearchFieldDataType.Double, filterable=True, sortable=True),
            SimpleField(name="timestamp", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self.dimensions,
                vector_search_profile_name="closedloop-vector-profile",
            ),
        ]
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=VectorSearch(
                algorithms=[HnswAlgorithmConfiguration(name="closedloop-hnsw")],
                profiles=[VectorSearchProfile(name="closedloop-vector-profile", algorithm_configuration_name="closedloop-hnsw")],
            ),
        )
        self.index_client.create_or_update_index(index)

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
        self.search_client.merge_or_upload_documents([self._build_document(event).model_dump(mode="json")])

    def semantic_search(self, query_text: str, limit: int = 10, source_tool: str | None = None) -> list[dict[str, Any]]:
        self.ensure_index()
        vector = self.embedding_service.embed(query_text)
        filter_text = f"source_tool eq '{source_tool}'" if source_tool else None
        results = self.search_client.search(
            search_text=query_text,
            vector_queries=[VectorizedQuery(vector=vector, k_nearest_neighbors=limit, fields="content_vector")],
            top=limit,
            filter=filter_text,
        )
        return [dict(item) for item in results]

    def find_overlap(self, event: CanonicalEvent, compare_source: str, threshold: float = 0.92) -> dict[str, Any] | None:
        self.ensure_index()
        vector = self.embedding_service.embed(_event_text(event))
        results = list(
            self.search_client.search(
                search_text=event.title,
                vector_queries=[VectorizedQuery(vector=vector, k_nearest_neighbors=1, fields="content_vector")],
                top=1,
                filter=f"source_tool eq '{compare_source}'",
            )
        )
        if not results:
            return None
        result = dict(results[0])
        score = float(result.get("@search.score", 0.0))
        if score < threshold:
            return None
        result["similarity_score"] = score
        return result


def build_embedding_service() -> EmbeddingService:
    settings = get_settings()
    if settings.local_runtime_mode:
        return DeterministicEmbeddingService(settings.azure_openai_embedding_dimensions)
    if settings.azure_openai_endpoint and settings.azure_openai_api_key:
        return AzureOpenAIEmbeddingService()
    return DeterministicEmbeddingService(settings.azure_openai_embedding_dimensions)


@lru_cache(maxsize=1)
def get_local_knowledge_store() -> InMemoryKnowledgeStore:
    settings = get_settings()
    return InMemoryKnowledgeStore(DeterministicEmbeddingService(settings.azure_openai_embedding_dimensions))


def build_knowledge_store() -> KnowledgeStore:
    settings = get_settings()
    if settings.local_runtime_mode:
        return get_local_knowledge_store()
    embedding_service = build_embedding_service()
    if settings.has_search:
        return AzureAISearchKnowledgeStore(embedding_service)
    return InMemoryKnowledgeStore(embedding_service)
