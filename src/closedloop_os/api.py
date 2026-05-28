from __future__ import annotations

import contextlib
import json
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, Response, UploadFile, status

from closedloop_os.config import get_settings
from closedloop_os.mcp_server import mcp
from closedloop_os.messaging import EventPublisher, build_publisher
from closedloop_os.persistence import EventRepository, build_repository
from closedloop_os.secrets import get_secret
from closedloop_os.security import (
    verify_github_signature,
    verify_linear_signature,
    verify_sha256_signature,
    verify_slack_signature,
)
from closedloop_os.services import GitHubIngestService, RawIngestService
from closedloop_os.transcripts import chunk_transcript, parse_transcript

settings = get_settings()


def get_repository() -> EventRepository:
    return build_repository()


def get_publisher() -> EventPublisher:
    return build_publisher()


def resolve_github_secret() -> str:
    if settings.github_webhook_secret:
        return settings.github_webhook_secret
    return get_secret(settings.github_webhook_secret_name) or ""


def resolve_slack_signing_secret() -> str:
    if settings.slack_signing_secret:
        return settings.slack_signing_secret
    return get_secret(settings.slack_signing_secret_name) or ""


def resolve_slack_bot_token() -> str:
    if settings.slack_bot_token:
        return settings.slack_bot_token
    return get_secret(settings.slack_bot_token_name) or ""


def resolve_linear_secret() -> str:
    if settings.linear_webhook_secret:
        return settings.linear_webhook_secret
    return get_secret(settings.linear_webhook_secret_name) or ""


def resolve_jira_access_token() -> str:
    if settings.jira_access_token:
        return settings.jira_access_token
    return get_secret(settings.jira_access_token_name) or ""


def resolve_jira_webhook_secret() -> str:
    if settings.jira_webhook_secret:
        return settings.jira_webhook_secret
    return get_secret(settings.jira_webhook_secret_name) or ""


def resolve_confluence_access_token() -> str:
    if settings.confluence_access_token:
        return settings.confluence_access_token
    return get_secret(settings.confluence_access_token_name) or ""


def resolve_confluence_webhook_secret() -> str:
    if settings.confluence_webhook_secret:
        return settings.confluence_webhook_secret
    return get_secret(settings.confluence_webhook_secret_name) or ""


def resolve_notion_access_token() -> str:
    if settings.notion_access_token:
        return settings.notion_access_token
    return get_secret(settings.notion_access_token_name) or ""


def resolve_zendesk_webhook_secret() -> str:
    if settings.zendesk_webhook_secret:
        return settings.zendesk_webhook_secret
    return get_secret(settings.zendesk_webhook_secret_name) or ""


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="ClosedLoop OS", version="0.1.0", lifespan=lifespan)
app.mount("/mcp", mcp.streamable_http_app())


@app.get("/")
async def root() -> dict[str, object]:
    return {
        "name": "ClosedLoop OS",
        "status": "running",
        "health": "/healthz",
        "docs": "/docs",
        "connectors": [
            "/api/connectors/github",
            "/api/connectors/slack",
            "/api/connectors/linear",
            "/api/connectors/jira",
            "/api/connectors/confluence",
            "/api/connectors/zendesk",
            "/api/connectors/meetings/upload",
        ],
        "mcp": "/mcp",
    }


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


@app.post("/api/connectors/slack", status_code=status.HTTP_202_ACCEPTED)
async def slack_connector(
    request: Request,
    response: Response,
    x_slack_signature: str | None = Header(default=None, alias="X-Slack-Signature"),
    x_slack_request_timestamp: str | None = Header(default=None, alias="X-Slack-Request-Timestamp"),
    publisher: EventPublisher = Depends(get_publisher),
) -> dict[str, object]:
    body = await request.body()
    if not verify_slack_signature(resolve_slack_signing_secret(), body, x_slack_signature, x_slack_request_timestamp):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Slack signature.")

    # OAuth2 bot token is resolved here so deployment fails early if the connector is configured incompletely.
    resolve_slack_bot_token()

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload.") from exc

    if payload.get("type") == "url_verification":
        response.status_code = status.HTTP_200_OK
        return {"challenge": payload.get("challenge", "")}

    event = payload.get("event", {})
    event_type = event.get("type")
    if event_type not in {"message", "file_shared"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported Slack event '{event_type}'.")

    delivery_id = payload.get("event_id") or f"slack-{event.get('event_ts') or event.get('ts')}"
    raw_event = RawIngestService(publisher=publisher).ingest(
        source_tool="slack",
        event_name=event_type,
        payload=payload,
        delivery_id=delivery_id,
    )
    return {"status": "accepted", "raw_event_id": raw_event.id, "event_type": event_type}


@app.post("/api/connectors/linear", status_code=status.HTTP_202_ACCEPTED)
async def linear_connector(
    request: Request,
    linear_signature: str | None = Header(default=None, alias="Linear-Signature"),
    publisher: EventPublisher = Depends(get_publisher),
) -> dict[str, object]:
    body = await request.body()
    if not verify_linear_signature(resolve_linear_secret(), body, linear_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Linear signature.")

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload.") from exc

    linear_type = (payload.get("type") or payload.get("data", {}).get("__typename") or "").lower()
    if linear_type not in {"issue", "comment", "cycle", "project"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported Linear event '{linear_type}'.")

    delivery_id = payload.get("webhookId") or payload.get("id") or f"linear-{linear_type}-{payload.get('action', 'event')}"
    raw_event = RawIngestService(publisher=publisher).ingest(
        source_tool="linear",
        event_name=linear_type,
        payload=payload,
        delivery_id=delivery_id,
    )
    return {"status": "accepted", "raw_event_id": raw_event.id, "event_type": linear_type}


@app.post("/api/connectors/jira", status_code=status.HTTP_202_ACCEPTED)
async def jira_connector(
    request: Request,
    x_atlassian_webhook_identifier: str | None = Header(default=None, alias="X-Atlassian-Webhook-Identifier"),
    x_atlassian_webhook_event: str | None = Header(default=None, alias="X-Atlassian-Webhook-Event"),
    x_closedloop_signature: str | None = Header(default=None, alias="X-ClosedLoop-Signature"),
    publisher: EventPublisher = Depends(get_publisher),
) -> dict[str, object]:
    body = await request.body()
    secret = resolve_jira_webhook_secret()
    if secret and not verify_sha256_signature(secret, body, x_closedloop_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Jira signature.")
    resolve_jira_access_token()

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload.") from exc

    event_name = (x_atlassian_webhook_event or payload.get("webhookEvent") or "").lower().replace("jira:", "").replace("comment_", "comment_")
    supported = {"issue_created", "issue_updated", "comment_created", "sprint_started", "sprint_closed"}
    if event_name not in supported:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported Jira event '{event_name}'.")

    delivery_id = str(x_atlassian_webhook_identifier or payload.get("timestamp") or f"jira-{event_name}")
    raw_event = RawIngestService(publisher=publisher).ingest("jira", event_name, payload, delivery_id)
    return {"status": "accepted", "raw_event_id": raw_event.id, "event_type": event_name}


@app.post("/api/connectors/confluence", status_code=status.HTTP_202_ACCEPTED)
async def confluence_connector(
    request: Request,
    x_atlassian_webhook_identifier: str | None = Header(default=None, alias="X-Atlassian-Webhook-Identifier"),
    x_closedloop_signature: str | None = Header(default=None, alias="X-ClosedLoop-Signature"),
    publisher: EventPublisher = Depends(get_publisher),
) -> dict[str, object]:
    body = await request.body()
    secret = resolve_confluence_webhook_secret()
    if secret and not verify_sha256_signature(secret, body, x_closedloop_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Confluence signature.")
    resolve_confluence_access_token()

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload.") from exc

    delivery_id = str(x_atlassian_webhook_identifier or payload.get("timestamp") or "confluence-event")
    raw_event = RawIngestService(publisher=publisher).ingest(
        source_tool="confluence",
        event_name=payload.get("eventType", "page_updated"),
        payload=payload,
        delivery_id=delivery_id,
    )
    return {"status": "accepted", "raw_event_id": raw_event.id, "event_type": raw_event.event_name}


@app.post("/api/connectors/zendesk", status_code=status.HTTP_202_ACCEPTED)
async def zendesk_connector(
    request: Request,
    x_zendesk_webhook_signature: str | None = Header(default=None, alias="X-Zendesk-Webhook-Signature"),
    publisher: EventPublisher = Depends(get_publisher),
) -> dict[str, object]:
    body = await request.body()
    secret = resolve_zendesk_webhook_secret()
    if secret and not verify_sha256_signature(secret, body, x_zendesk_webhook_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Zendesk signature.")

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload.") from exc

    event_name = (payload.get("type") or payload.get("event_type") or "").lower()
    supported = {"ticket.created", "ticket.updated", "sla.breached", "satisfaction_rated"}
    if event_name not in supported:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported Zendesk event '{event_name}'.")

    delivery_id = str(payload.get("id") or payload.get("ticket", {}).get("id") or f"zendesk-{event_name}")
    raw_event = RawIngestService(publisher=publisher).ingest("zendesk", event_name, payload, delivery_id)
    return {"status": "accepted", "raw_event_id": raw_event.id, "event_type": event_name}


@app.post("/api/connectors/meetings/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_meeting_transcript(
    file: UploadFile = File(...),
    publisher: EventPublisher = Depends(get_publisher),
) -> dict[str, object]:
    supported = {".txt", ".vtt", ".srt", ".json"}
    filename = file.filename or "meeting.txt"
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in supported:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported transcript file '{suffix}'.")

    content = await file.read()
    parsed_chunks = parse_transcript(filename, content)
    grouped = chunk_transcript(parsed_chunks)
    delivery_id = f"meeting-{uuid4()}"
    meeting_id = f"meeting-{uuid4()}"
    payload = {
        "meeting_id": meeting_id,
        "title": filename,
        "filename": filename,
        "grouped_chunks": [
            {"speaker": chunk.speaker, "timestamp": chunk.timestamp, "text": chunk.text}
            for chunk in grouped
        ],
    }
    raw_event = RawIngestService(publisher=publisher).ingest("meeting", "transcript_upload", payload, delivery_id)
    return {
        "status": "accepted",
        "raw_event_id": raw_event.id,
        "meeting_id": meeting_id,
        "chunk_count": len(grouped),
    }
