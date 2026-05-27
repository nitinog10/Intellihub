from __future__ import annotations

from typing import Any

import httpx

from closedloop_os.config import get_settings
from closedloop_os.messaging import EventPublisher
from closedloop_os.persistence import EventRepository
from closedloop_os.secrets import get_secret
from closedloop_os.services.raw_ingest import RawIngestService


class NotionSyncService:
    def __init__(self, repository: EventRepository, publisher: EventPublisher) -> None:
        self.repository = repository
        self.publisher = publisher
        self.settings = get_settings()

    def sync_updated_pages(self) -> list[str]:
        token = self.settings.notion_access_token or get_secret(self.settings.notion_access_token_name)
        if not token:
            return []

        last_timestamp = self.repository.get_latest_timestamp("notion", "notion.page")
        payload = {
            "filter": {
                "property": "object",
                "value": "page",
            },
            "sort": {
                "direction": "ascending",
                "timestamp": "last_edited_time",
            },
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": self.settings.notion_api_version,
            "Content-Type": "application/json",
        }

        response = httpx.post(
            "https://api.notion.com/v1/search",
            headers=headers,
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        results = response.json().get("results", [])

        delivery_ids: list[str] = []
        raw_ingest = RawIngestService(self.publisher)
        for page in results:
            edited = page.get("last_edited_time")
            if last_timestamp and edited and edited <= last_timestamp:
                continue
            delivery_id = f"notion-{page.get('id')}-{edited}"
            raw_ingest.ingest(
                source_tool="notion",
                event_name="page_updated",
                payload={"page": page},
                delivery_id=delivery_id,
            )
            delivery_ids.append(delivery_id)
        return delivery_ids
