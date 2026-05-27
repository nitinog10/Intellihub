from __future__ import annotations

import contextlib
import json

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status

from closedloop_os.config import get_settings
from closedloop_os.mcp_server import mcp
from closedloop_os.messaging import EventPublisher, build_publisher
from closedloop_os.persistence import EventRepository, build_repository
from closedloop_os.secrets import get_secret
from closedloop_os.security import verify_github_signature
from closedloop_os.services import GitHubIngestService

settings = get_settings()


def get_repository() -> EventRepository:
    return build_repository()


def get_publisher() -> EventPublisher:
    return build_publisher()


def resolve_github_secret() -> str:
    if settings.github_webhook_secret:
        return settings.github_webhook_secret
    return get_secret(settings.github_webhook_secret_name) or ""


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="ClosedLoop OS", version="0.1.0", lifespan=lifespan)
app.mount("/mcp", mcp.streamable_http_app())


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/connectors/github", status_code=status.HTTP_202_ACCEPTED)
async def github_connector(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
    repository: EventRepository = Depends(get_repository),
    publisher: EventPublisher = Depends(get_publisher),
) -> dict[str, object]:
    body = await request.body()
    secret = resolve_github_secret()
    if not verify_github_signature(secret, body, x_hub_signature_256):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid GitHub webhook signature.")

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload.") from exc

    service = GitHubIngestService(repository=repository, publisher=publisher)
    try:
        event = service.ingest(event_name=x_github_event, payload=payload, delivery_id=x_github_delivery)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {"status": "accepted", "event_id": event.id, "event_type": event.event_type}
