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
        key_vault_uri=os.getenv("KEY_VAULT_URI", ""),
        service_bus_namespace=os.getenv("SERVICE_BUS_NAMESPACE", ""),
        service_bus_queue_name=os.getenv("SERVICE_BUS_QUEUE_NAME", "raw-events"),
        service_bus_connection_string=os.getenv("SERVICE_BUS_CONNECTION_STRING", ""),
    )


def env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(name, default)
