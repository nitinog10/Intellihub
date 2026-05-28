from __future__ import annotations

from functools import lru_cache

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from closedloop_os.config import get_settings


@lru_cache(maxsize=1)
def _secret_client() -> SecretClient | None:
    settings = get_settings()
    if not settings.key_vault_uri or not settings.enable_key_vault_lookup:
        return None
    return SecretClient(vault_url=settings.key_vault_uri, credential=DefaultAzureCredential())


def get_secret(secret_name: str) -> str | None:
    client = _secret_client()
    if client is None:
        return None

    try:
        return client.get_secret(secret_name).value
    except Exception:
        return None
