from __future__ import annotations

import hashlib
import hmac


def verify_github_signature(secret: str, payload: bytes, signature_header: str | None) -> bool:
    if not secret:
        raise ValueError("GitHub webhook secret is not configured.")
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"
    return hmac.compare_digest(expected, signature_header)
