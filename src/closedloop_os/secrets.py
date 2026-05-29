from __future__ import annotations

import os


def get_secret(name: str) -> str | None:
    """Resolve a secret from environment variables only.

    Key Vault has been removed — all secrets come from .env or local.settings.json.
    """
    return os.getenv(name)
