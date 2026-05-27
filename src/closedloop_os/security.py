from __future__ import annotations

import hashlib
import hmac
import time


def verify_github_signature(secret: str, payload: bytes, signature_header: str | None) -> bool:
    if not secret:
        raise ValueError("GitHub webhook secret is not configured.")
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"
    return hmac.compare_digest(expected, signature_header)


def verify_slack_signature(
    secret: str,
    payload: bytes,
    signature_header: str | None,
    timestamp_header: str | None,
    tolerance_seconds: int = 300,
) -> bool:
    if not secret:
        raise ValueError("Slack signing secret is not configured.")
    if not signature_header or not timestamp_header:
        return False

    try:
        request_timestamp = int(timestamp_header)
    except ValueError:
        return False

    if abs(time.time() - request_timestamp) > tolerance_seconds:
        return False

    basestring = b"v0:" + timestamp_header.encode("utf-8") + b":" + payload
    digest = hmac.new(secret.encode("utf-8"), basestring, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"v0={digest}", signature_header)


def verify_linear_signature(secret: str, payload: bytes, signature_header: str | None) -> bool:
    if not secret:
        raise ValueError("Linear webhook secret is not configured.")
    if not signature_header:
        return False

    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"
    return hmac.compare_digest(expected, signature_header) or hmac.compare_digest(digest, signature_header)


def verify_sha256_signature(secret: str, payload: bytes, signature_header: str | None) -> bool:
    if not secret:
        raise ValueError("Webhook secret is not configured.")
    if not signature_header:
        return False
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"
    return hmac.compare_digest(expected, signature_header) or hmac.compare_digest(digest, signature_header)
