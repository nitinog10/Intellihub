from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class Settings(BaseModel):
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
    azure_openai_endpoint: str = Field(default="")
    azure_openai_api_key: str = Field(default="")
    azure_openai_deployment: str = Field(default="gpt-4o-mini")
    azure_openai_api_version: str = Field(default="2024-10-21")
    key_vault_uri: str = Field(default="")
    service_bus_namespace: str = Field(default="")
    service_bus_queue_name: str = Field(default="raw-events")
    service_bus_connection_string: str = Field(default="")

    @property
    def has_cosmos(self) -> bool:
        return bool(self.cosmos_endpoint and self.cosmos_key)

    @property
    def has_service_bus(self) -> bool:
        return bool(self.service_bus_connection_string or self.service_bus_namespace)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
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
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
        azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        key_vault_uri=os.getenv("KEY_VAULT_URI", ""),
        service_bus_namespace=os.getenv("SERVICE_BUS_NAMESPACE", ""),
        service_bus_queue_name=os.getenv("SERVICE_BUS_QUEUE_NAME", "raw-events"),
        service_bus_connection_string=os.getenv("SERVICE_BUS_CONNECTION_STRING", ""),
    )


def env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(name, default)
