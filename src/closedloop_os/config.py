from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


def load_local_settings() -> None:
    """Load values from local.settings.json into environment variables (backward compat)."""
    settings_path = Path("local.settings.json")
    if not settings_path.exists():
        return

    try:
        values = json.loads(settings_path.read_text(encoding="utf-8")).get("Values", {})
    except (OSError, json.JSONDecodeError):
        return

    for key, value in values.items():
        if value is None:
            continue
        os.environ.setdefault(key, str(value))


if not any("pytest" in arg.lower() for arg in sys.argv):
    load_local_settings()


class Settings(BaseModel):
    # ── Cosmos DB (the only Azure service retained) ──
    cosmos_endpoint: str = Field(default="")
    cosmos_key: str = Field(default="")
    cosmos_database_name: str = Field(default="closedloop-os")
    cosmos_container_name: str = Field(default="events")

    # ── Azure OpenAI (kept as AI provider) ──
    azure_openai_endpoint: str = Field(default="")
    azure_openai_api_key: str = Field(default="")
    azure_openai_deployment: str = Field(default="gpt-4o-mini")
    azure_openai_embedding_deployment: str = Field(default="text-embedding-3-small")
    azure_openai_embedding_dimensions: int = Field(default=1536)
    azure_openai_api_version: str = Field(default="2024-10-21")

    # ── APScheduler (replaces Azure Timer Trigger) ──
    notion_sync_interval_minutes: int = Field(default=5)

    # ── Connector secrets (all from env vars, no Key Vault) ──
    github_webhook_secret: str = Field(default="")
    slack_signing_secret: str = Field(default="")
    slack_bot_token: str = Field(default="")
    linear_webhook_secret: str = Field(default="")
    jira_client_id: str = Field(default="")
    jira_client_secret: str = Field(default="")
    jira_access_token: str = Field(default="")
    jira_webhook_secret: str = Field(default="")
    confluence_access_token: str = Field(default="")
    confluence_webhook_secret: str = Field(default="")
    notion_access_token: str = Field(default="")
    notion_api_version: str = Field(default="2022-06-28")
    notion_database_id: str = Field(default="")
    zendesk_webhook_secret: str = Field(default="")

    @property
    def has_cosmos(self) -> bool:
        return bool(self.cosmos_endpoint and self.cosmos_key)

    @property
    def has_openai(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        cosmos_endpoint=os.getenv("COSMOS_ENDPOINT", ""),
        cosmos_key=os.getenv("COSMOS_KEY", ""),
        cosmos_database_name=os.getenv("COSMOS_DATABASE_NAME", "closedloop-os"),
        cosmos_container_name=os.getenv("COSMOS_CONTAINER_NAME", "events"),
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
        azure_openai_embedding_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"),
        azure_openai_embedding_dimensions=int(os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSIONS", "1536")),
        azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        notion_sync_interval_minutes=int(os.getenv("NOTION_SYNC_INTERVAL_MINUTES", "5")),
        github_webhook_secret=os.getenv("GITHUB_WEBHOOK_SECRET", ""),
        slack_signing_secret=os.getenv("SLACK_SIGNING_SECRET", ""),
        slack_bot_token=os.getenv("SLACK_BOT_TOKEN", ""),
        linear_webhook_secret=os.getenv("LINEAR_WEBHOOK_SECRET", ""),
        jira_client_id=os.getenv("JIRA_CLIENT_ID", ""),
        jira_client_secret=os.getenv("JIRA_CLIENT_SECRET", ""),
        jira_access_token=os.getenv("JIRA_ACCESS_TOKEN", ""),
        jira_webhook_secret=os.getenv("JIRA_WEBHOOK_SECRET", ""),
        confluence_access_token=os.getenv("CONFLUENCE_ACCESS_TOKEN", ""),
        confluence_webhook_secret=os.getenv("CONFLUENCE_WEBHOOK_SECRET", ""),
        notion_access_token=os.getenv("NOTION_ACCESS_TOKEN", ""),
        notion_api_version=os.getenv("NOTION_API_VERSION", "2022-06-28"),
        notion_database_id=os.getenv("NOTION_DATABASE_ID", ""),
        zendesk_webhook_secret=os.getenv("ZENDESK_WEBHOOK_SECRET", ""),
    )


def env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(name, default)
