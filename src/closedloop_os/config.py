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
    local_runtime_mode: bool = Field(default=False)
    cosmos_endpoint: str = Field(default="")
    cosmos_key: str = Field(default="")
    cosmos_database_name: str = Field(default="closedloop-os")
    cosmos_container_name: str = Field(default="events")
    github_webhook_secret: str = Field(default="")
    github_webhook_secret_name: str = Field(default="github-webhook-secret")
    slack_signing_secret: str = Field(default="")
    slack_signing_secret_name: str = Field(default="slack-signing-secret")
    slack_bot_token: str = Field(default="")
    slack_bot_token_name: str = Field(default="slack-bot-token")
    linear_webhook_secret: str = Field(default="")
    linear_webhook_secret_name: str = Field(default="linear-webhook-secret")
    jira_client_id: str = Field(default="")
    jira_client_secret: str = Field(default="")
    jira_access_token: str = Field(default="")
    jira_access_token_name: str = Field(default="jira-access-token")
    jira_webhook_secret: str = Field(default="")
    jira_webhook_secret_name: str = Field(default="jira-webhook-secret")
    confluence_access_token: str = Field(default="")
    confluence_access_token_name: str = Field(default="confluence-access-token")
    confluence_webhook_secret: str = Field(default="")
    confluence_webhook_secret_name: str = Field(default="confluence-webhook-secret")
    notion_access_token: str = Field(default="")
    notion_access_token_name: str = Field(default="notion-access-token")
    notion_api_version: str = Field(default="2022-06-28")
    notion_database_id: str = Field(default="")
    zendesk_webhook_secret: str = Field(default="")
    zendesk_webhook_secret_name: str = Field(default="zendesk-webhook-secret")
    azure_search_endpoint: str = Field(default="")
    azure_search_api_key: str = Field(default="")
    azure_search_index_name: str = Field(default="closedloop-knowledge")
    azure_openai_endpoint: str = Field(default="")
    azure_openai_api_key: str = Field(default="")
    azure_openai_deployment: str = Field(default="gpt-4o-mini")
    azure_openai_embedding_deployment: str = Field(default="text-embedding-3-small")
    azure_openai_embedding_dimensions: int = Field(default=1536)
    azure_openai_api_version: str = Field(default="2024-10-21")
    key_vault_uri: str = Field(default="")
    enable_key_vault_lookup: bool = Field(default=False)
    service_bus_namespace: str = Field(default="")
    service_bus_queue_name: str = Field(default="raw-events")
    service_bus_connection_string: str = Field(default="")

    @property
    def has_cosmos(self) -> bool:
        return bool(self.cosmos_endpoint and self.cosmos_key)

    @property
    def has_service_bus(self) -> bool:
        return bool(self.service_bus_connection_string or self.service_bus_namespace)

    @property
    def has_search(self) -> bool:
        return bool(self.azure_search_endpoint and self.azure_search_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        local_runtime_mode=os.getenv("LOCAL_RUNTIME_MODE", "").lower() in {"1", "true", "yes"},
        cosmos_endpoint=os.getenv("COSMOS_ENDPOINT", ""),
        cosmos_key=os.getenv("COSMOS_KEY", ""),
        cosmos_database_name=os.getenv("COSMOS_DATABASE_NAME", "closedloop-os"),
        cosmos_container_name=os.getenv("COSMOS_CONTAINER_NAME", "events"),
        github_webhook_secret=os.getenv("GITHUB_WEBHOOK_SECRET", ""),
        github_webhook_secret_name=os.getenv("GITHUB_WEBHOOK_SECRET_NAME", "github-webhook-secret"),
        slack_signing_secret=os.getenv("SLACK_SIGNING_SECRET", ""),
        slack_signing_secret_name=os.getenv("SLACK_SIGNING_SECRET_NAME", "slack-signing-secret"),
        slack_bot_token=os.getenv("SLACK_BOT_TOKEN", ""),
        slack_bot_token_name=os.getenv("SLACK_BOT_TOKEN_NAME", "slack-bot-token"),
        linear_webhook_secret=os.getenv("LINEAR_WEBHOOK_SECRET", ""),
        linear_webhook_secret_name=os.getenv("LINEAR_WEBHOOK_SECRET_NAME", "linear-webhook-secret"),
        jira_client_id=os.getenv("JIRA_CLIENT_ID", ""),
        jira_client_secret=os.getenv("JIRA_CLIENT_SECRET", ""),
        jira_access_token=os.getenv("JIRA_ACCESS_TOKEN", ""),
        jira_access_token_name=os.getenv("JIRA_ACCESS_TOKEN_NAME", "jira-access-token"),
        jira_webhook_secret=os.getenv("JIRA_WEBHOOK_SECRET", ""),
        jira_webhook_secret_name=os.getenv("JIRA_WEBHOOK_SECRET_NAME", "jira-webhook-secret"),
        confluence_access_token=os.getenv("CONFLUENCE_ACCESS_TOKEN", ""),
        confluence_access_token_name=os.getenv("CONFLUENCE_ACCESS_TOKEN_NAME", "confluence-access-token"),
        confluence_webhook_secret=os.getenv("CONFLUENCE_WEBHOOK_SECRET", ""),
        confluence_webhook_secret_name=os.getenv("CONFLUENCE_WEBHOOK_SECRET_NAME", "confluence-webhook-secret"),
        notion_access_token=os.getenv("NOTION_ACCESS_TOKEN", ""),
        notion_access_token_name=os.getenv("NOTION_ACCESS_TOKEN_NAME", "notion-access-token"),
        notion_api_version=os.getenv("NOTION_API_VERSION", "2022-06-28"),
        notion_database_id=os.getenv("NOTION_DATABASE_ID", ""),
        zendesk_webhook_secret=os.getenv("ZENDESK_WEBHOOK_SECRET", ""),
        zendesk_webhook_secret_name=os.getenv("ZENDESK_WEBHOOK_SECRET_NAME", "zendesk-webhook-secret"),
        azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT", ""),
        azure_search_api_key=os.getenv("AZURE_SEARCH_API_KEY", ""),
        azure_search_index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "closedloop-knowledge"),
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
        azure_openai_embedding_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"),
        azure_openai_embedding_dimensions=int(os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSIONS", "1536")),
        azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        key_vault_uri=os.getenv("KEY_VAULT_URI", ""),
        enable_key_vault_lookup=os.getenv("ENABLE_KEY_VAULT_LOOKUP", "").lower() in {"1", "true", "yes"},
        service_bus_namespace=os.getenv("SERVICE_BUS_NAMESPACE", ""),
        service_bus_queue_name=os.getenv("SERVICE_BUS_QUEUE_NAME", "raw-events"),
        service_bus_connection_string=os.getenv("SERVICE_BUS_CONNECTION_STRING", ""),
    )


def env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(name, default)
